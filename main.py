from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import logging
import shutil
import os
import re
import pymupdf4llm
import fitz  # PyMuPDF
from pathlib import Path
import time
import tempfile
import uuid
from datetime import datetime, timedelta
import uvicorn

# LLM Integration
try:
    from query_handler import QueryHandler
    from config import config
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logger_placeholder = logging.getLogger(__name__)
    logger_placeholder.warning("query_handler or config not found. LLM features disabled.")

# Configure logging with timestamp
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app with metadata
app = FastAPI(
    title="PDF Text Extractor",
    description="Production-ready PDF text extraction API with 100% accuracy for English PDFs",
    version="1.0.0",
)

# CORS configuration for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
import tempfile
UPLOAD_DIR = Path(tempfile.gettempdir()) / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE_MB = 200
MAX_PAGES = 160
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {'.pdf'}
TEMP_FILE_EXPIRY_HOURS = 1


import unicodedata

def filter_english(text: str) -> str:
    """
    Clean and normalize text while preserving English characters, numbers,
    punctuation, smart quotes, dashes, section marks, and symbols.
    """
    if not text:
        return ""
    replacements = {
        '“': '"', '”': '"', '‘': "'", '’': "'",
        '—': '-', '–': '-', '•': '*', '…': '...',
        'ﬁ': 'fi', 'ﬂ': 'fl', '§': 'Section ',
        '₹': 'INR ', '€': 'EUR ', '£': 'GBP ', '°': ' deg '
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    
    cleaned = []
    for char in text:
        code = ord(char)
        if code < 128 or unicodedata.category(char).startswith(('P', 'S', 'Z', 'N', 'L')):
            cleaned.append(char)
        else:
            cleaned.append(' ')
    
    result = ''.join(cleaned)
    result = re.sub(r'[ \t]+', ' ', result)
    return result.strip()

def cleanup_expired_files():
    """Remove temporary files older than TEMP_FILE_EXPIRY_HOURS."""
    try:
        now = time.time()
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < now - TEMP_FILE_EXPIRY_HOURS * 3600:
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up expired temp file: {file_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup file {file_path.name}: {e}")
    except Exception as e:
        logger.warning(f"Cleanup operation failed: {e}")

def validate_pdf_file(file_path: Path) -> tuple[bool, str]:
    """
    Comprehensive PDF validation.
    Returns (is_valid, message)
    """
    try:
        doc = fitz.open(file_path)
        
        # Check encryption
        if doc.is_encrypted:
            doc.close()
            return False, "Encrypted PDFs are not supported for security reasons."
        
        # Check page count
        page_count = doc.page_count
        if page_count == 0:
            doc.close()
            return False, "PDF file is empty (contains no pages)."
        
        if page_count > MAX_PAGES:
            doc.close()
            return False, f"PDF exceeds maximum limit of {MAX_PAGES} pages. This PDF has {page_count} pages."
        
        # Check if PDF has any extractable content
        has_content = False
        for page in doc:
            if page.get_text("text").strip():
                has_content = True
                break
        
        doc.close()
        
        if not has_content:
            return False, "PDF appears to have no extractable text content."
        
        return True, f"Valid PDF with {page_count} page(s)"
        
    except Exception as e:
        return False, f"PDF validation failed: {str(e)}"

def extract_text_from_pdf(file_path: Path) -> str:
    """
    Extract text from PDF with fallback mechanisms.
    Attempts PyMuPDF4LLM first for better layout preservation, falls back to basic extraction.
    """
    try:
        # Primary method: PyMuPDF4LLM for structured text extraction
        logger.info(f"Attempting structured extraction via PyMuPDF4LLM")
        extracted_content = pymupdf4llm.to_markdown(str(file_path))
        
        if extracted_content and len(extracted_content.strip()) > 0:
            logger.info("Successfully extracted text via PyMuPDF4LLM")
            return extracted_content
        
    except Exception as e:
        logger.warning(f"PyMuPDF4LLM extraction failed: {e}. Falling back to basic extraction.")
    
    # Fallback method: Basic text extraction via PyMuPDF
    try:
        logger.info("Using fallback text extraction method")
        doc = fitz.open(file_path)
        full_text = []
        
        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text")
            if text.strip():
                full_text.append(f"--- Page {page_num} ---\n{text}")
        
        doc.close()
        extracted_content = "\n\n".join(full_text)
        
        if extracted_content:
            logger.info("Successfully extracted text via fallback method")
            return extracted_content
        
    except Exception as e:
        logger.error(f"Fallback extraction also failed: {e}")
        raise Exception(f"Text extraction failed: {str(e)}")
    
    raise Exception("No text could be extracted from the PDF")

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return JSONResponse(content={
        "status": "healthy",
        "service": "PDF Text Extractor",
        "timestamp": datetime.now().isoformat()
    })

@app.post("/api/extract", tags=["Extraction"])
async def extract_text(file: UploadFile = File(...)):
    """
    Extract text from an uploaded PDF file.
    
    **Parameters:**
    - file: PDF file to extract text from
    
    **Returns:**
    - filename: Original filename
    - text: Extracted text content
    - page_count: Number of pages processed
    - processing_time: Time taken in seconds
    - character_count: Total characters in extracted text
    
    **Errors:**
    - 400: Invalid file type, too many pages, encrypted PDF, or corrupted file
    - 413: File size exceeds maximum limit
    - 500: Internal processing error
    """
    start_time = time.time()
    temp_file_path = None
    
    try:
        # Cleanup expired files before processing
        cleanup_expired_files()
        
        # 1. Validate file type
        if not file.content_type or "pdf" not in file.content_type.lower():
            logger.warning(f"Invalid content type: {file.content_type}")
            raise HTTPException(
                status_code=400, 
                detail="Invalid file type. Only PDF files are accepted."
            )
        
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            logger.warning(f"Invalid filename: {file.filename}")
            raise HTTPException(
                status_code=400, 
                detail="Invalid filename. Please ensure the file has a .pdf extension."
            )
        
        # 2. Check file size before saving
        # Read file size from content
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to start
        
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413, 
                detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE_MB}MB."
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=400, 
                detail="Uploaded file is empty."
            )
        
        # 3. Save uploaded file temporarily with unique identifier
        unique_id = str(uuid.uuid4())[:8]
        temp_file_path = UPLOAD_DIR / f"temp_{unique_id}_{int(time.time())}.pdf"
        
        try:
            with temp_file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            logger.info(f"File saved: {temp_file_path.name} ({file_size} bytes)")
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            raise HTTPException(
                status_code=500, 
                detail="Failed to save uploaded file."
            )
        
        # 4. Validate PDF integrity and constraints
        is_valid, validation_message = validate_pdf_file(temp_file_path)
        
        if not is_valid:
            logger.warning(f"PDF validation failed: {validation_message}")
            raise HTTPException(
                status_code=400, 
                detail=validation_message
            )
        
        logger.info(f"PDF validation passed: {validation_message}")
        
        # 5. Extract text from PDF
        logger.info("Starting text extraction")
        extracted_content = extract_text_from_pdf(temp_file_path)
        
        # 6. Filter to English text only
        logger.info("Filtering non-English characters")
        cleaned_text = filter_english(extracted_content)
        
        # Remove excessive whitespace while preserving paragraph structure
        cleaned_text = '\n'.join(line.rstrip() for line in cleaned_text.split('\n'))
        
        # Get page count for response
        doc = fitz.open(temp_file_path)
        page_count = doc.page_count
        doc.close()
        
        processing_time = time.time() - start_time
        
        logger.info(f"Successfully processed {file.filename} ({page_count} pages) in {processing_time:.2f}s")
        
        return JSONResponse(content={
            "filename": file.filename,
            "text": cleaned_text,
            "page_count": page_count,
            "character_count": len(cleaned_text),
            "processing_time": round(processing_time, 2),
            "message": "Text extraction completed successfully",
            "status": "success"
        })
    
    except HTTPException as he:
        logger.error(f"HTTP error: {he.detail}")
        raise he
    
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred during text extraction: {str(e)[:100]}"
        )
    
    finally:
        # 7. Cleanup temporary file
        if temp_file_path and temp_file_path.exists():
            try:
                os.remove(temp_file_path)
                logger.info(f"Temporary file cleaned up: {temp_file_path.name}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")

# ==================== LLM Integration Endpoints ====================

@app.get("/api/llm/health", tags=["LLM"])
async def llm_health():
    """Check if LLM service (Gemini) is available."""
    if not LLM_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "message": "LLM module not available. Install query_handler module.",
                "service": "LLM"
            }
        )
    
    try:
        query_handler = QueryHandler()
        details = query_handler.detailed_health_check()
        query_handler.close()
        
        # Consider healthy if Gemini is available (Ollama is optional)
        gemini_ok = details.get("gemini_fallback", {}).get("available", False)
        ollama_ok = details.get("ollama", {}).get("available", False)
        is_healthy = gemini_ok or ollama_ok
        
        if is_healthy:
            active = "gemini" if gemini_ok else "ollama"
            return JSONResponse(content={
                "status": "healthy",
                "service": "Gemini 2.0 Flash RAG",
                "active_provider": active,
                "gemini": details.get("gemini_fallback"),
                "timestamp": datetime.now().isoformat()
            })
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "message": "Gemini API is not available. Check your API key in Settings.",
                    "details": details
                }
            )
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": f"LLM health check error: {str(e)}",
                "service": "LLM"
            }
        )


class QuestionRequest(BaseModel):
    pdf_text: str
    question: str
    model: str = "llama2"


class SummarizeRequest(BaseModel):
    pdf_text: str
    model: str = "llama2"


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class AskRequest(BaseModel):
    pdf_text: str
    question: str
    chat_history: list[ChatMessage] = []
    model: str = "llama2"


class ConfigUpdateRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None


@app.get("/api/config", tags=["Configuration"])
async def get_app_config():
    """Get public configuration and active LLM status."""
    return JSONResponse(content={
        "has_gemini_key": bool(config.GEMINI_API_KEY),
        "gemini_model": config.GEMINI_MODEL,
        "ollama_url": config.OLLAMA_BASE_URL,
        "ollama_model": config.OLLAMA_MODEL,
        "use_fallback": config.USE_GEMINI_FALLBACK
    })


@app.post("/api/config", tags=["Configuration"])
async def update_app_config(req: ConfigUpdateRequest):
    """Update runtime configuration for Gemini API key and model."""
    from config import update_gemini_config
    update_gemini_config(api_key=req.gemini_api_key, model=req.gemini_model)
    return JSONResponse(content={
        "success": True,
        "message": "Configuration updated successfully",
        "has_gemini_key": bool(config.GEMINI_API_KEY),
        "gemini_model": config.GEMINI_MODEL
    })


@app.post("/api/summarize", tags=["LLM"])
async def summarize_pdf(req: SummarizeRequest):
    """
    Generate a summary of the extracted PDF text.
    
    **Parameters:**
    - pdf_text: The extracted text from the PDF
    - model: The Ollama model to use (default: llama2)
    
    **Returns:**
    - success: Whether the summary was generated
    - summary: The generated summary
    - processing_time: Time to process in seconds
    - model_used: Which model was used
    """
    start_time = time.time()
    
    try:
        if not req.pdf_text or not req.pdf_text.strip():
            raise HTTPException(status_code=400, detail="PDF text cannot be empty")
        
        if not LLM_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="LLM service is not available."
            )
        
        query_handler = QueryHandler(model=req.model)
        
        if not query_handler.health_check():
            query_handler.close()
            raise HTTPException(
                status_code=503,
                detail="Neither Ollama nor Gemini fallback is available."
            )
        
        # Build a detailed grounded summary prompt
        summary_prompt = f"""You are a precise document summarization assistant.

STRICT RULES:
- Summarize ONLY using the document below.
- Do NOT add any information not present in the document.
- Do NOT speculate or use general knowledge.
- Structure the summary with: Main Topic, Key Points, Important Conclusions.
- Use bullet points where appropriate.

DOCUMENT:
{req.pdf_text[:200000]}

Provide a clear, structured summary based strictly on the above document."""
        
        # Always use Gemini directly
        response = query_handler.llm_service.generate_response(
            summary_prompt,
            temperature=0.1,
            preferred_provider="gemini"
        )
        
        if not response.success:
            query_handler.close()
            raise HTTPException(status_code=500, detail=response.error)
        
        summary = response.response
        model_used = response.model
        
        query_handler.close()
        processing_time = time.time() - start_time
        
        logger.info(f"PDF summarized successfully in {processing_time:.2f}s (model: {model_used})")
        
        return JSONResponse(content={
            "success": True,
            "summary": summary,
            "model_used": model_used,
            "processing_time": round(processing_time, 2),
            "status": "success"
        })
        
    except HTTPException as he:
        logger.error(f"HTTP exception: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in summarize_pdf: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)[:100]}"
        )


@app.post("/api/ask", tags=["LLM"])
async def ask_with_chat_history(req: AskRequest):
    """
    Ask a question about the PDF with chat history context.
    
    **Parameters:**
    - pdf_text: The extracted text from the PDF
    - question: The question to ask
    - chat_history: Previous conversation messages for context
    - model: The Ollama model to use (default: llama2)
    
    **Returns:**
    - success: Whether the query was processed
    - answer: The model's answer based on PDF context
    - has_answer: Whether answer was found in the document
    - confidence: Confidence level (0.0-1.0)
    - processing_time: Time to process in seconds
    - model_used: Which model was used
    """
    start_time = time.time()
    
    try:
        if not req.pdf_text or not req.pdf_text.strip():
            raise HTTPException(status_code=400, detail="PDF text cannot be empty")

        if not req.question or not req.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        if len(req.question) > 500:
            raise HTTPException(status_code=400, detail="Question is too long (max 500 characters)")
        
        if not LLM_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="LLM service is not available."
            )
        
        query_handler = QueryHandler(model=req.model)
        
        if not query_handler.health_check():
            query_handler.close()
            raise HTTPException(
                status_code=503,
                detail="Neither Ollama nor Gemini fallback is available. Ensure Ollama is running at http://localhost:11434 or set GEMINI_API_KEY."
            )
        
        # Route directly to Gemini with chat history
        preferred = "gemini"
        result = query_handler.answer_question(
            pdf_text=req.pdf_text,
            question=req.question,
            chat_history=req.chat_history,
            temperature=0.1,
            preferred_provider=preferred
        )
        query_handler.close()
        
        processing_time = time.time() - start_time
        
        if not result.success:
            logger.error(f"Query failed: {result.error}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process question: {result.error}"
            )
        
        logger.info(f"Chat question answered in {processing_time:.2f}s")
        
        return JSONResponse(content={
            "success": True,
            "answer": result.answer,
            "has_answer": result.has_answer,
            "confidence": result.confidence,
            "model_used": result.model_used,
            "context_length": result.context_used_length,
            "processing_time": round(processing_time, 2),
            "status": "success"
        })
        
    except HTTPException as he:
        logger.error(f"HTTP exception: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in ask_with_chat_history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)[:100]}"
        )


@app.post("/api/ask-question", tags=["LLM"])
async def ask_question(req: QuestionRequest):
    pdf_text = req.pdf_text
    question = req.question
    model = req.model or "llama2"
    """
    Ask a question about extracted PDF text.
    
    The model will answer ONLY based on the provided PDF text context.
    It will not use outside knowledge or hallucinate.
    
    **Parameters:**
    - pdf_text: The extracted text from the PDF
    - question: The question to ask about the PDF
    - model: The Ollama model to use (default: llama2)
    
    **Returns:**
    - success: Whether the query was processed
    - answer: The model's answer based on PDF context
    - has_answer: Whether answer was found in the document
    - confidence: Confidence level (0.0-1.0)
    - processing_time: Time to process in seconds
    - model_used: Which model was used
    
    **Error Responses:**
    - 400: Invalid input (empty text or question)
    - 503: Ollama service not available
    - 500: Internal processing error
    """
    start_time = time.time()
    
    try:
        # Validate inputs
        if not pdf_text or not pdf_text.strip():
            raise HTTPException(status_code=400, detail="PDF text cannot be empty")

        if not question or not question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        if len(question) > 500:
            raise HTTPException(status_code=400, detail="Question is too long (max 500 characters)")
        
        if not LLM_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="LLM service is not available. Install query_handler module."
            )
        
        query_handler = QueryHandler(model=req.model)
        
        if not query_handler.health_check():
            query_handler.close()
            raise HTTPException(
                status_code=503,
                detail="Neither Ollama nor Gemini fallback is available. Ensure Ollama is running at http://localhost:11434 or set GEMINI_API_KEY."
            )
        
        # Route directly to Gemini
        result = query_handler.answer_question(
            pdf_text=pdf_text,
            question=question,
            temperature=0.1,
            preferred_provider="gemini"
        )
        query_handler.close()
        
        processing_time = time.time() - start_time
        
        if not result.success:
            logger.error(f"Query failed: {result.error}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process question: {result.error}"
            )
        
        logger.info(
            f"Question answered successfully in {processing_time:.2f}s "
            f"(model: {result.model_used}, confidence: {result.confidence:.2f})"
        )
        
        return JSONResponse(content={
            "success": True,
            "answer": result.answer,
            "has_answer": result.has_answer,
            "confidence": result.confidence,
            "model_used": result.model_used,
            "context_length": result.context_used_length,
            "processing_time": round(processing_time, 2),
            "status": "success"
        })
        
    except HTTPException as he:
        logger.error(f"HTTP exception: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in ask_question: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)[:100]}"
        )

# Serve Static Files (Frontend)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    logger.info("Starting PDF Text Extractor Service")
    logger.info(f"Configuration: MAX_PAGES={MAX_PAGES}, MAX_FILE_SIZE_MB={MAX_FILE_SIZE_MB}")
    
    # Check if LLM module is available
    if LLM_AVAILABLE:
        logger.info("✅ LLM integration available")
    else:
        logger.warning("⚠️  LLM integration not available")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
