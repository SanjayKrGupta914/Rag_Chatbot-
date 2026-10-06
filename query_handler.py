"""
Query Handler Module - Orchestrates PDF Q&A workflow
Coordinates text extraction, chunking, LLM querying (Ollama with Gemini fallback), and response validation
"""

import logging
import re
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from llm_service import HybridLLMService, PromptBuilder, LLMResponse, OllamaService, GeminiService
from config import config

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of document question answering"""
    success: bool
    answer: str = ""
    error: str = ""
    model_used: str = ""
    context_used_length: int = 0
    processing_time: float = 0.0
    confidence: float = 1.0  # Based on response indicators
    has_answer: bool = True  # Whether answer was found in document


class DocumentChunker:
    """
    Handles breaking large documents into manageable chunks.
    Preserves semantic meaning while respecting context windows.
    """
    
    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = 4000,
        overlap: int = 500
    ) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
        
        logger.info(f"Document split into {len(chunks)} chunks")
        return chunks
    
    @staticmethod
    def find_relevant_chunks(
        chunks: List[str],
        question: str,
        max_total_chars: int = 120000,
        keywords: Optional[List[str]] = None
    ) -> str:
        """Find and assemble the most relevant chunks up to max_total_chars."""
        if not chunks:
            return ""
        
        if len(chunks) == 1 or sum(len(c) for c in chunks) <= max_total_chars:
            return "\n\n".join(chunks)
        
        if keywords is None:
            keywords = re.findall(r'\b\w{3,}\b', question.lower())
        
        scored_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_lower = chunk.lower()
            score = sum(1 for keyword in keywords if keyword in chunk_lower)
            scored_chunks.append((score, i, chunk))
        
        scored_chunks.sort(key=lambda x: (x[0], -x[1]), reverse=True)
        
        selected = []
        total_len = 0
        for score, idx, chunk in scored_chunks:
            if total_len + len(chunk) <= max_total_chars or not selected:
                selected.append((idx, chunk))
                total_len += len(chunk)
            if total_len >= max_total_chars:
                break
        
        selected.sort(key=lambda x: x[0])
        return "\n\n---\n\n".join(c for idx, c in selected)

    @staticmethod
    def find_relevant_chunk(
        chunks: List[str],
        question: str,
        keywords: Optional[List[str]] = None
    ) -> str:
        """Find the most relevant single chunk for a question (backwards compatibility)."""
        return DocumentChunker.find_relevant_chunks(chunks, question, max_total_chars=16000, keywords=keywords)


class ResponseValidator:
    """Validates LLM responses for hallucination indicators"""
    
    NO_ANSWER_PHRASES = [
        "not available in the provided document",
        "not found in the document",
        "not in the document",
        "cannot find in the document",
        "not mentioned in the document",
        "no information provided in the document",
        "document does not contain",
    ]
    
    HALLUCINATION_PHRASES = [
        "based on my general knowledge",
        "from my training",
        "in general",
        "typically",
        "usually the case",
        "commonly",
        "as far as i know",
        "i believe",
        "i think",
    ]
    
    @classmethod
    def validate_response(
        cls,
        response_text: str,
        question: str
    ) -> tuple[bool, float]:
        """Validate response for quality indicators."""
        response_lower = response_text.lower()
        
        has_answer = not any(
            phrase in response_lower 
            for phrase in cls.NO_ANSWER_PHRASES
        )
        
        confidence = 1.0
        for phrase in cls.HALLUCINATION_PHRASES:
            if phrase in response_lower:
                confidence -= 0.1
        
        confidence = max(0.0, min(1.0, confidence))
        logger.info(f"Response validation: has_answer={has_answer}, confidence={confidence:.2f}")
        return has_answer, confidence


class QueryHandler:
    """
    Main handler for document question answering.
    Orchestrates PDF text + LLM interaction using Ollama with automatic Gemini fallback.
    """
    
    def __init__(
        self,
        ollama_url: Optional[str] = None,
        model: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        gemini_model: Optional[str] = None,
        max_context: int = 120000,
        chunk_size: int = 16000,
    ):
        """
        Initialize query handler with hybrid LLM service.
        """
        ollama_url = ollama_url or getattr(config, "OLLAMA_BASE_URL", "http://localhost:11434")
        model = model or getattr(config, "OLLAMA_MODEL", "llama2")
        gemini_api_key = gemini_api_key or getattr(config, "GEMINI_API_KEY", None)
        gemini_model = gemini_model or getattr(config, "GEMINI_MODEL", "gemini-3.8-flash")
        enable_fallback = getattr(config, "USE_GEMINI_FALLBACK", True)

        self.llm_service = HybridLLMService(
            ollama_url=ollama_url,
            ollama_model=model,
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
            enable_gemini_fallback=enable_fallback,
        )
        self.max_context = max_context
        self.chunk_size = chunk_size
        self.chunker = DocumentChunker()
        self.validator = ResponseValidator()
        
        logger.info(f"QueryHandler initialized with Ollama model '{model}' and Gemini fallback '{gemini_model}' (max_context={max_context})")
    
    def health_check(self) -> bool:
        """Check if any LLM service (Ollama or Gemini fallback) is available."""
        return self.llm_service.health_check()
    
    def detailed_health_check(self) -> dict:
        """Get detailed health check report."""
        return self.llm_service.detailed_health_check()
    
    def answer_question(
        self,
        pdf_text: str,
        question: str,
        temperature: float = 0.3,
        chat_history: Optional[List[Any]] = None,
        preferred_provider: Optional[str] = None
    ) -> QueryResult:
        """
        Answer a question based on PDF text using LLM service (Gemini or Ollama).
        """
        start_time = time.time()
        
        try:
            if not pdf_text or not pdf_text.strip():
                return QueryResult(
                    success=False,
                    error="No PDF text provided",
                )
            
            if not question or not question.strip():
                return QueryResult(
                    success=False,
                    error="Question cannot be empty",
                )
            
            logger.info(f"Processing question: {question[:100]}...")
            
            context = pdf_text
            if len(pdf_text) > self.max_context:
                logger.info(f"PDF context exceeds {self.max_context} chars (total {len(pdf_text)} chars), extracting top chunks")
                chunks = self.chunker.chunk_text(pdf_text, self.chunk_size)
                context = self.chunker.find_relevant_chunks(chunks, question, max_total_chars=self.max_context)
            
            system_instr, prompt, used_context = PromptBuilder.build_prompt_with_system(
                context,
                question,
                self.max_context,
                chat_history=chat_history
            )
            
            # Get response from LLM
            llm_response = self.llm_service.generate_response(
                prompt=prompt,
                system_instruction=system_instr,
                temperature=temperature,
                preferred_provider=preferred_provider
            )
            
            if not llm_response.success:
                logger.error(f"LLM error: {llm_response.error}")
                return QueryResult(
                    success=False,
                    error=llm_response.error,
                    model_used=llm_response.model,
                    processing_time=time.time() - start_time,
                )
            
            has_answer, confidence = self.validator.validate_response(
                llm_response.response,
                question
            )

            # Fallback over chunks if answer not found in initial pass
            if not has_answer and len(pdf_text) > self.max_context:
                try:
                    logger.info("Initial pass did not find answer — running secondary chunk scan")
                    chunks = self.chunker.chunk_text(pdf_text, self.chunk_size)
                    keywords = re.findall(r'\b\w{3,}\b', question.lower())
                    scored = []
                    for c in chunks:
                        score = sum(1 for k in keywords if k in c.lower())
                        scored.append((score, c))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    top_chunks = [c for s, c in scored[:3] if s >= 0]

                    for idx, chunk in enumerate(top_chunks):
                        sys_instr, p, used_ctx = PromptBuilder.build_prompt_with_system(
                            chunk, question, self.max_context, chat_history=chat_history
                        )
                        resp = self.llm_service.generate_response(
                            prompt=p,
                            system_instruction=sys_instr,
                            temperature=temperature,
                            preferred_provider=preferred_provider
                        )
                        if not resp.success:
                            continue
                        h, conf = self.validator.validate_response(resp.response, question)
                        if h:
                            logger.info(f"Fallback chunk {idx+1} found answer with confidence {conf:.2f}")
                            return QueryResult(
                                success=True,
                                answer=resp.response,
                                model_used=resp.model,
                                context_used_length=len(used_ctx),
                                processing_time=time.time() - start_time,
                                confidence=conf,
                                has_answer=True,
                            )
                except Exception as e:
                    logger.warning(f"Fallback chunking pass failed: {e}")
            
            processing_time = time.time() - start_time
            logger.info(
                f"Answer generated in {processing_time:.2f}s "
                f"(model: {llm_response.model}, confidence: {confidence:.2f})"
            )
            
            return QueryResult(
                success=True,
                answer=llm_response.response,
                model_used=llm_response.model,
                context_used_length=len(used_context),
                processing_time=processing_time,
                confidence=confidence,
                has_answer=has_answer,
            )
            
        except Exception as e:
            logger.error(f"Query handler error: {str(e)}", exc_info=True)
            return QueryResult(
                success=False,
                error=f"Error processing question: {str(e)}",
                processing_time=time.time() - start_time,
            )
    
    def close(self):
        """Clean up resources."""
        self.llm_service.close()
        logger.info("QueryHandler closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
