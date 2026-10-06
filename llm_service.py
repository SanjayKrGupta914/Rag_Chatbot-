"""
LLM Service Module - Handles Ollama and Gemini Fallback Integration
Provides context-aware question answering using local Ollama LLM with automatic Gemini API fallback
"""

import os
import requests
import logging
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

# Attempt importing google-genai SDK
try:
    from google import genai
    from google.genai import types
    GENAI_SDK_AVAILABLE = True
except ImportError:
    GENAI_SDK_AVAILABLE = False


@dataclass
class LLMResponse:
    """Structured response from LLM (Ollama or Gemini)"""
    success: bool
    response: str = ""
    error: str = ""
    model: str = ""
    provider: str = ""  # "ollama" or "gemini"
    processing_time: float = 0.0
    tokens_generated: int = 0


# Backwards compatibility alias
OllamaResponse = LLMResponse


class OllamaService:
    """
    Service for interacting with Ollama LLM.
    Handles connection, prompt generation, and response processing.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        timeout: int = 300,
        max_tokens: int = 2048,
    ):
        """
        Initialize Ollama service.
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self._session = requests.Session()
        
        # Validate model availability and pick a fallback if necessary
        try:
            available = self.get_available_models()
            if available:
                names = [m['name'] for m in available]
                if self.model not in names:
                    available_sorted = sorted(available, key=lambda x: x.get('size', float('inf')))
                    fallback = available_sorted[0]['name']
                    old = self.model
                    self.model = fallback
                    logger.warning(f"Requested model '{old}' not found. Falling back to '{self.model}' (smallest available)")
        except Exception:
            pass

        logger.info(f"Ollama Service initialized: {self.base_url}, Model: {self.model}")
    
    def health_check(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = self._session.get(
                f"{self.base_url}/api/tags",
                timeout=3
            )
            is_healthy = response.status_code == 200
            
            if is_healthy:
                logger.info("Ollama health check: ✅ OK")
            else:
                logger.warning(f"Ollama health check failed: HTTP {response.status_code}")
            
            return is_healthy
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
    
    def get_available_models(self) -> list:
        """Get list of available models in Ollama."""
        try:
            response = self._session.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = []
                for m in data.get('models', []):
                    models.append({
                        'name': m.get('name', ''),
                        'size': m.get('size', 0)
                    })
                logger.info(f"Available Ollama models: {[m['name'] for m in models]}")
                return models
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch available Ollama models: {e}")
            return []
    
    def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3
    ) -> LLMResponse:
        """Generate response from Ollama model."""
        try:
            start_time = time.time()
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
            }
            
            if system_instruction:
                payload["system"] = system_instruction
            
            logger.info(f"Sending prompt to Ollama (model: {self.model})")
            
            response = self._session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '')
                
                logger.info(f"Ollama response received in {processing_time:.2f}s")
                
                return LLMResponse(
                    success=True,
                    response=response_text.strip(),
                    model=self.model,
                    provider="ollama",
                    processing_time=processing_time,
                    tokens_generated=data.get('eval_count', 0)
                )
            else:
                error_msg = f"Ollama returned HTTP {response.status_code}"
                logger.error(error_msg)
                return LLMResponse(
                    success=False,
                    error=error_msg,
                    model=self.model,
                    provider="ollama",
                    processing_time=processing_time
                )
                
        except requests.exceptions.Timeout:
            error_msg = f"Ollama request timeout (>{self.timeout}s)"
            logger.error(error_msg)
            return LLMResponse(
                success=False,
                error=error_msg,
                model=self.model,
                provider="ollama"
            )
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to Ollama. Ensure it's running at " + self.base_url
            logger.warning(error_msg)
            return LLMResponse(
                success=False,
                error=error_msg,
                model=self.model,
                provider="ollama"
            )
        except Exception as e:
            error_msg = f"Unexpected error with Ollama: {str(e)}"
            logger.error(error_msg)
            return LLMResponse(
                success=False,
                error=error_msg,
                model=self.model,
                provider="ollama"
            )
    
    def close(self):
        """Close the session."""
        if self._session:
            self._session.close()


class GeminiService:
    """
    Service for interacting with Google Gemini API.
    Used as fallback when Ollama is unavailable or fails.
    Supports official google-genai SDK with direct REST API fallback.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        timeout: int = 60,
    ):
        self.api_key = api_key if api_key is not None else (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        self.model = model
        self.timeout = timeout
        self._session = requests.Session()
        
        self.client = None
        if GENAI_SDK_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini Service initialized with SDK (model: {self.model})")
            except Exception as e:
                logger.warning(f"Failed to initialize google-genai SDK client: {e}. Will fallback to REST API.")
        else:
            logger.info(f"Gemini Service initialized with REST API (model: {self.model})")

    def health_check(self) -> bool:
        """Check if Gemini API key is configured."""
        if not self.api_key:
            return False
        return True

    def _call_single_model(
        self,
        target_model: str,
        prompt: str,
        system_instruction: Optional[str],
        temperature: float
    ) -> LLMResponse:
        start_time = time.time()
        
        # Method 1: Try official SDK if client is ready
        if self.client:
            try:
                config_kwargs = {"temperature": temperature}
                if system_instruction:
                    config_kwargs["system_instruction"] = system_instruction
                
                logger.info(f"Sending prompt to Gemini via SDK (model: {target_model})")
                response = self.client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_kwargs)
                )
                processing_time = time.time() - start_time
                text = response.text if hasattr(response, "text") and response.text else ""
                
                if text.strip():
                    logger.info(f"Gemini SDK response received in {processing_time:.2f}s")
                    return LLMResponse(
                        success=True,
                        response=text.strip(),
                        model=target_model,
                        provider="gemini",
                        processing_time=processing_time
                    )
            except Exception as e:
                logger.warning(f"Gemini SDK generation failed for '{target_model}': {e}. Falling back to REST API...")

        # Method 2: Fallback to Google Generative Language REST API
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={self.api_key}"
            
            payload: Dict[str, Any] = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": 8192
                }
            }
            if system_instruction:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_instruction}]
                }
                
            logger.info(f"Sending prompt to Gemini REST API (model: {target_model})")
            res = self._session.post(url, json=payload, timeout=self.timeout)
            processing_time = time.time() - start_time
            
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts)
                    usage = data.get("usageMetadata", {})
                    tokens = usage.get("candidatesTokenCount", 0)
                    logger.info(f"Gemini REST response received in {processing_time:.2f}s")
                    return LLMResponse(
                        success=True,
                        response=text.strip(),
                        model=target_model,
                        provider="gemini",
                        processing_time=processing_time,
                        tokens_generated=tokens
                    )
                else:
                    return LLMResponse(
                        success=False,
                        error="Gemini returned an empty candidate response",
                        model=target_model,
                        provider="gemini",
                        processing_time=processing_time
                    )
            else:
                err_text = res.text[:200]
                error_msg = f"Gemini API HTTP {res.status_code}: {err_text}"
                logger.warning(error_msg)
                return LLMResponse(
                    success=False,
                    error=error_msg,
                    model=target_model,
                    provider="gemini",
                    processing_time=processing_time
                )
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Gemini REST call error: {str(e)}"
            logger.error(error_msg)
            return LLMResponse(
                success=False,
                error=error_msg,
                model=target_model,
                provider="gemini",
                processing_time=processing_time
            )

    def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3
    ) -> LLMResponse:
        """Generate response using Google Gemini API with model cascade fallback."""
        if not self.api_key:
            return LLMResponse(
                success=False,
                error="Gemini API key is not configured (GEMINI_API_KEY environment variable missing)",
                model=self.model,
                provider="gemini"
            )

        candidate_models = []
        req_model = self.model.strip()
        if req_model:
            candidate_models.append(req_model)
        
        # Add fallbacks in order of preference
        for m in ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-pro"]:
            if m not in candidate_models:
                candidate_models.append(m)

        last_resp = None
        for target_model in candidate_models:
            resp = self._call_single_model(target_model, prompt, system_instruction, temperature)
            if resp.success:
                return resp
            last_resp = resp
            logger.warning(f"Model '{target_model}' failed. Attempting next candidate model...")

        return last_resp or LLMResponse(
            success=False,
            error="All Gemini model candidates failed",
            model=self.model,
            provider="gemini"
        )

    def close(self):
        """Close HTTP session."""
        if self._session:
            self._session.close()


class HybridLLMService:
    """
    Hybrid LLM service with Ollama as primary provider and Gemini as automatic fallback.
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama2",
        gemini_api_key: Optional[str] = None,
        gemini_model: str = "gemini-3.8-flash",
        timeout: int = 300,
        enable_gemini_fallback: bool = True,
    ):
        self.ollama_service = OllamaService(
            base_url=ollama_url,
            model=ollama_model,
            timeout=timeout,
        )
        self.gemini_service = GeminiService(
            api_key=gemini_api_key,
            model=gemini_model,
            timeout=60,
        )
        self.enable_gemini_fallback = enable_gemini_fallback

    def health_check(self) -> bool:
        """
        Check if any LLM service (Ollama or Gemini fallback) is available.
        """
        ollama_ok = self.ollama_service.health_check()
        if ollama_ok:
            return True
            
        if self.enable_gemini_fallback:
            gemini_ok = self.gemini_service.health_check()
            if gemini_ok:
                logger.info("Ollama is offline; Gemini fallback is active and ready.")
                return True
                
        return False

    def detailed_health_check(self) -> Dict[str, Any]:
        """
        Get detailed status for both Ollama and Gemini fallback.
        """
        ollama_ok = self.ollama_service.health_check()
        gemini_ok = self.gemini_service.health_check()
        
        active_provider = "none"
        if ollama_ok:
            active_provider = "ollama"
        elif self.enable_gemini_fallback and gemini_ok:
            active_provider = "gemini"

        return {
            "healthy": ollama_ok or (self.enable_gemini_fallback and gemini_ok),
            "ollama": {
                "available": ollama_ok,
                "url": self.ollama_service.base_url,
                "model": self.ollama_service.model
            },
            "gemini_fallback": {
                "available": gemini_ok,
                "model": self.gemini_service.model,
                "has_api_key": bool(self.gemini_service.api_key)
            },
            "active_provider": active_provider
        }

    def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
        preferred_provider: Optional[str] = None
    ) -> LLMResponse:
        """
        Generate response using preferred provider or fallback cascade.
        """
        # Determine execution order based on explicit preference
        use_gemini_first = (preferred_provider == "gemini")

        if use_gemini_first and self.gemini_service.health_check():
            logger.info(f"Gemini provider selected/preferred. Sending query to model '{self.gemini_service.model}'.")
            gemini_res = self.gemini_service.generate_response(prompt, system_instruction, temperature)
            if gemini_res.success:
                return gemini_res
            logger.warning(f"Gemini generation attempt failed: '{gemini_res.error}'. Attempting Ollama fallback...")

        # Step: Try Ollama if healthy
        if self.ollama_service.health_check():
            logger.info(f"Ollama service active. Sending query to model '{self.ollama_service.model}'.")
            ollama_res = self.ollama_service.generate_response(prompt, system_instruction, temperature)
            if ollama_res.success:
                ollama_res.provider = "ollama"
                return ollama_res
            logger.warning(f"Ollama generation attempt failed: '{ollama_res.error}'. Attempting Gemini fallback...")

        # Step: Fallback to Gemini if not tried yet
        if not use_gemini_first and self.enable_gemini_fallback and self.gemini_service.health_check():
            logger.info(f"Ollama unavailable or failed. Executing fallback to Gemini model '{self.gemini_service.model}'.")
            gemini_res = self.gemini_service.generate_response(prompt, system_instruction, temperature)
            if gemini_res.success:
                gemini_res.model = f"{gemini_res.model} (Gemini Fallback)"
                return gemini_res
            else:
                logger.error(f"Gemini fallback generation failed: {gemini_res.error}")
                return LLMResponse(
                    success=False,
                    error=f"Ollama unavailable and Gemini fallback failed: {gemini_res.error}",
                    model=self.ollama_service.model,
                    provider="hybrid"
                )

        # Step 3: Neither available or both failed
        error_msg = f"Cannot connect to Ollama at {self.ollama_service.base_url}."
        if not self.gemini_service.api_key:
            error_msg += " Gemini fallback is enabled, but GEMINI_API_KEY environment variable is missing."
        elif use_gemini_first and 'gemini_res' in locals() and not gemini_res.success:
            error_msg = f"Gemini failed: {gemini_res.error}. And Ollama fallback is unavailable ({self.ollama_service.base_url})."
        elif not use_gemini_first and self.enable_gemini_fallback and 'gemini_res' in locals() and not gemini_res.success:
            error_msg += f" Gemini fallback also failed: {gemini_res.error}."
            
        logger.error(error_msg)
        return LLMResponse(
            success=False,
            error=error_msg,
            model=self.ollama_service.model,
            provider="none"
        )

    def close(self):
        """Clean up services."""
        self.ollama_service.close()
        self.gemini_service.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class PromptBuilder:
    """Builds structured prompts for document Q&A"""
    
    SYSTEM_INSTRUCTION = """You are a highly precise document question-answering assistant powered by Gemini.

CRITICAL ANTI-HALLUCINATION RULES — FOLLOW EXACTLY:
1. Answer ONLY and EXCLUSIVELY using information that appears word-for-word or clearly stated in the DOCUMENT CONTEXT below.
2. If a number, name, date, clause, amount, section, table value, or term is present in the document, reproduce it exactly as written — never paraphrase key details.
3. If the user asks about something NOT found anywhere in the document, respond EXACTLY: "The answer is not available in the provided document."
4. NEVER use your training data, general knowledge, or assumptions to answer. Zero tolerance for fabrication.
5. NEVER say "typically", "generally", "usually", "I think", "I believe", "in most cases" — these indicate hallucination.
6. If the document mentions multiple relevant items, list ALL of them — do not cherry-pick.
7. For tables, lists, and structured data: reproduce the exact values from the document.
8. Use conversation history ONLY to understand follow-up questions — never to introduce new facts.
9. Cite the relevant section, page, or clause when you can identify it from the document.
10. Respond in clear, structured markdown when the answer is multi-part."""
    
    @staticmethod
    def build_prompt(
        pdf_text: str,
        question: str,
        max_context_length: int = 120000,
        chat_history: Optional[List[Any]] = None
    ) -> tuple[str, str]:
        """
        Build a structured prompt for document Q&A.
        
        Args:
            pdf_text: Extracted PDF content
            question: User question
            max_context_length: Maximum context length to use
            chat_history: List of previous chat messages
        
        Returns:
            Tuple of (full_prompt, truncated_context)
        """
        context = pdf_text[:max_context_length]
        if len(pdf_text) > max_context_length:
            context += "\n[... document truncated due to length ...]"
        
        chat_str = ""
        if chat_history:
            chat_str = "CONVERSATION HISTORY:\n"
            for msg in chat_history[-6:]:
                role = "User" if (getattr(msg, 'role', '') == 'user' or (isinstance(msg, dict) and msg.get('role') == 'user')) else "Assistant"
                content = getattr(msg, 'content', '') if hasattr(msg, 'content') else (msg.get('content', '') if isinstance(msg, dict) else str(msg))
                if content:
                    chat_str += f"{role}: {content}\n"
            chat_str += "\n"

        prompt = f"""DOCUMENT CONTEXT:
{context}

{chat_str}CURRENT QUESTION:
{question}

ANSWER:"""
        
        return prompt, context
    
    @staticmethod
    def build_prompt_with_system(
        pdf_text: str,
        question: str,
        max_context_length: int = 120000,
        chat_history: Optional[List[Any]] = None
    ) -> tuple[str, str, str]:
        """
        Build prompt with system instruction.
        
        Returns:
            Tuple of (system_instruction, prompt, context)
        """
        prompt, context = PromptBuilder.build_prompt(
            pdf_text, 
            question, 
            max_context_length,
            chat_history=chat_history
        )
        return PromptBuilder.SYSTEM_INSTRUCTION, prompt, context
