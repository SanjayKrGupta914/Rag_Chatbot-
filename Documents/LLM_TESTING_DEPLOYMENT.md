# 📋 LLM Integration Testing & Deployment Guide

Complete guide for testing the Ollama LLM integration with PDF Ink and deploying the system to production.

## Table of Contents

1. [Pre-Testing Checklist](#pre-testing-checklist)
2. [Testing Procedures](#testing-procedures)
3. [Hallucination Prevention Verification](#hallucination-prevention-verification)
4. [Deployment Guide](#deployment-guide)
5. [Troubleshooting](#troubleshooting)

## Pre-Testing Checklist

Before running tests, ensure:

- [ ] Ollama is installed and running on `localhost:11434`
- [ ] llama2 model is installed: `ollama pull llama2`
- [ ] FastAPI backend is running on port 8000
- [ ] PyMuPDF4LLM >= 0.3.4 is installed
- [ ] All dependencies in `requirements.txt` are installed
- [ ] Sample PDFs are available for testing

## Testing Procedures

### 1. Backend API Health Checks

#### Test LLM Health Endpoint

```bash
# Check if LLM service is available
curl -X GET http://localhost:8000/api/llm/health

# Expected Response (200 OK):
# {"status": "ok", "model": "llama2", "available_models": ["llama2:latest"]}

# If Ollama is offline, expect 503:
# {"detail": "Ollama service unavailable"}
```

#### Test PDF Extraction Endpoint

```bash
# Extract text from a test PDF
curl -X POST http://localhost:8000/api/extract \
  -F "file=@test_document.pdf"

# Expected Response (200 OK):
# {
#   "text": "extracted document text...",
#   "page_count": 5,
#   "character_count": 12543,
#   "filename": "test_document.pdf"
# }
```

### 2. Frontend Application Tests

#### Test 1: Basic PDF Upload and Extraction

1. Start the application in your browser
2. Click the upload area
3. Select a test PDF with clear, readable text
4. Verify:
   - ✓ Document extracts without errors
   - ✓ Text appears in the output box
   - ✓ Page count and character count display correctly
   - ✓ Download, Copy, and Clear buttons are available

#### Test 2: Q&A Section Availability

1. After extracting a PDF
2. Scroll to the Q&A section below the extracted text
3. Verify:
   - ✓ Question input field is visible
   - ✓ "Ask" button is enabled (if Ollama is running)
   - ✓ Response area is hidden initially

#### Test 3: Simple Question Query

1. Ask a straightforward question in the Q&A field
2. Example PDF: README with project description
3. Example Question: "What is the project name?"
4. Verify:
   - ✓ Loading state shows during processing
   - ✓ Answer appears in response area
   - ✓ Metadata shows model, time, confidence
   - ✓ Processing completes within 10 seconds

#### Test 4: Multi-Paragraph Context

1. Extract a larger PDF (20+ pages)
2. Ask a question that requires reading multiple sections
3. Example: "What are the main features described in this document?"
4. Verify:
   - ✓ LLM correctly processes chunked contexts
   - ✓ Answer references multiple parts of document
   - ✓ No hallucination about content not in PDF

#### Test 5: Input Validation

1. Test question length limit:
   ```
   - Enter a question > 500 characters
   - Expected: Toast warning, text truncated to 500 chars
   ```

2. Test empty question submission:
   ```
   - Click Ask without entering a question
   - Expected: "Please enter a question" error toast
   ```

3. Test without extracted text:
   ```
   - Don't extract a PDF first
   - Try to ask a question
   - Expected: "Please extract a PDF first" error
   ```

### 3. API Endpoint Testing

#### POST /api/ask-question

**Test Parameters:**

```json
{
  "pdf_text": "Full extracted text from PDF (can be thousands of characters)",
  "question": "What is the main topic?",
  "model": "llama2"
}
```

**Expected Response:**

```json
{
  "success": true,
  "answer": "The main topic is...",
  "has_answer": true,
  "confidence": 0.95,
  "processing_time": 2.34,
  "model_used": "llama2",
  "context_length": 4000
}
```

**Test Scenarios:**

1. **Valid Request**
   ```bash
   curl -X POST http://localhost:8000/api/ask-question \
     -H "Content-Type: application/json" \
     -d '{
       "pdf_text": "Sample text...",
       "question": "What is this about?",
       "model": "llama2"
     }'
   ```

2. **Missing Parameters**
   ```bash
   # Missing pdf_text - expect 400 error
   # Missing question - expect 400 error
   ```

3. **Ollama Unavailable**
   ```bash
   # Stop Ollama and try request
   # Expected: 503 error with "LLM service unavailable"
   ```

4. **Large Document**
   ```bash
   # Test with 50,000+ character document
   # Expected: Automatic chunking, response within timeout
   ```

## Hallucination Prevention Verification

### Test Suite for Hallucination Detection

#### Test 1: Missing Information Response

**PDF Content**: Tech docs with no mention of pricing

**Question**: "What is the pricing model?"

**Expected Behavior**:
- ✅ Answer indicates information not in document
- ✅ Confidence score is low (< 0.3)
- ✅ `has_answer` field is `false`

**Acceptable Responses**:
- "The pricing information is not provided in this document."
- "This document does not contain pricing details."
- "The answer is not available in the provided document."

**Unacceptable Responses** (Hallucination):
- "The pricing is $99/month" (made up)
- "Based on industry standards, it costs..." (external knowledge)

#### Test 2: Factual Answer Verification

**PDF Content**: Clear factual statement - "Product launched in 2022"

**Question**: "When was the product launched?"

**Expected Behavior**:
- ✅ Correct answer: "2022"
- ✅ High confidence (> 0.7)
- ✅ `has_answer` is `true`

#### Test 3: Context Window Accuracy

**Large PDF**: 100+ page document

**Question**: "What is mentioned on page 87?"

Expected Behavior**:
- ✅ LLM processes relevant chunks
- ✅ Accurate answer from specific section
- ✅ Confidence reflects answer certainty

#### Test 4: Ambiguous Question Handling

**PDF Content**: Reference to multiple products/features

**Question**: "Which one is better?"

**Expected Behavior**:
- ⚠️ LLM requests clarification or states ambiguity
- ✅ Doesn't assume which entity is being compared
- ✅ Low-medium confidence (0.3-0.6)

#### Test 5: Mathematical Accuracy

**PDF Content**: "Sales increased from 100 to 150 units"

**Question**: "What was the percentage increase?"

**Expected Behavior**:
- ✅ Correct answer: "50% increase"
- ✅ Shows calculation reasoning
- ✅ High confidence

#### Test 6: Negative Case - Out of Domain

**PDF Content**: Economics textbook

**Question**: "Tell me jokes about penguins"

**Expected Behavior**:
- ✅ Answer: "This document doesn't contain jokes about penguins"
- ✅ Low confidence
- ✅ Does NOT generate penguin jokes

### Confidence Score Interpretation

| Confidence | Meaning | Action |
|------------|---------|--------|
| 0.0-0.2 | Very Likely Hallucination | ❌ Don't trust answer |
| 0.2-0.4 | Probably Not in Document | ⚠️  Verify manually |
| 0.4-0.6 | Uncertain | ℹ️ Cross-check answer |
| 0.6-0.8 | Likely Accurate | ✓ Generally trustworthy |
| 0.8-1.0 | High Confidence | ✅ Very likely accurate |

## Deployment Guide

### Development Environment

**Directory Setup:**
```
Pdf Extractor/
├── main.py
├── llm_service.py
├── query_handler.py
├── requirements.txt
├── static/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── OLLAMA_SETUP.md
└── LLM_TESTING_DEPLOYMENT.md
```

**Run Backend:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python main.py
# or
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Production Deployment

#### Option 1: Docker Deployment

**Create Dockerfile:**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY llm_service.py .
COPY query_handler.py .
COPY static/ ./static/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')"

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Docker Compose (with Ollama):**

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: pdfink-ollama
    ports:
      - "11434:11434"
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - pdfink

  backend:
    build: .
    container_name: pdfink-backend
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - ollama
    networks:
      - pdfink
    command: uvicorn main:app --host 0.0.0.0 --port 8000

  frontend:
    image: nginx:alpine
    container_name: pdfink-frontend
    ports:
      - "80:80"
    volumes:
      - ./static:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    networks:
      - pdfink

volumes:
  ollama_data:

networks:
  pdfink:
    driver: bridge
```

**Deploy:**
```bash
docker-compose up -d
```

#### Option 2: Server Deployment (Linux/Ubuntu)

**Setup Steps:**

1. **Install Python & Dependencies**
```bash
sudo apt-get update
sudo apt-get install python3.11 python3-pip nginx supervisor
```

2. **Install Ollama**
```bash
curl https://ollama.ai/install.sh | sh
ollama serve &  # Run in background
ollama pull llama2
```

3. **Deploy Application**
```bash
cd /opt/pdfink
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **Configure Supervisor (for process management)**
```bash
sudo nano /etc/supervisor/conf.d/pdfink.conf
```

Add:
```ini
[program:pdfink-backend]
directory=/opt/pdfink
command=/opt/pdfink/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
user=pdfink
autostart=true
autorestart=true
stderr_logfile=/var/log/pdfink/err.log
stdout_logfile=/var/log/pdfink/out.log
```

5. **Start Services**
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start pdfink-backend
```

6. **Configure Nginx Reverse Proxy**
```bash
sudo nano /etc/nginx/sites-available/pdfink
```

Add:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {
        root /opt/pdfink/static;
        try_files $uri $uri/ =404;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
```

7. **Enable and Restart Nginx**
```bash
sudo ln -s /etc/nginx/sites-available/pdfink /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Environment Variables

**Create `.env` file:**
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_TIMEOUT=300
CORS_ORIGINS=*
LOG_LEVEL=info
```

**Load in `main.py`:**
```python
from dotenv import load_dotenv
import os

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))
```

## Performance Optimization

### Recommended Configurations

**Light Load (< 10 concurrent users)**:
- Model: `orca-mini`
- Max context: 4000 chars
- Timeout: 60 seconds

**Medium Load (10-50 concurrent users)**:
- Model: `llama2`
- Max context: 8000 chars
- Timeout: 120 seconds

**Heavy Load (50+ concurrent users)**:
- Consider load balancing
- Model: `mistral` (better throughput)
- Max context: 6000 chars
- Implement caching layer (Redis)

### Caching Implementation

For frequently asked questions on same documents:

```python
# In main.py, add Redis caching
from redis import Redis
import hashlib

redis_client = Redis(host='localhost', port=6379, db=0)

@app.post("/api/ask-question")
async def ask_question(request: QuestionRequest):
    # Create cache key from pdf hash and question
    cache_key = f"qa:{hashlib.md5(request.pdf_text.encode()).hexdigest()}:{request.question}"
    
    # Check cache
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Process normally
    response = await QueryHandler.answer_question(...)
    
    # Cache for 1 hour
    redis_client.setex(cache_key, 3600, json.dumps(response))
    
    return response
```

## Troubleshooting

### Common Issues at Deployment

1. **Port Already in Use**
   ```bash
   # Check what's using the port
   lsof -i :8000
   # Kill process if needed
   kill -9 <PID>
   ```

2. **Ollama Connection Refused**
   ```bash
   # Verify Ollama is running
   curl http://localhost:11434/api/tags
   
   # If not running, start it
   ollama serve
   ```

3. **Out of Memory During Inference**
   ```python
   # In query_handler.py, reduce context
   max_context_length = 4000  # Down from 8000
   ```

4. **Slow Response Times**
   ```bash
   # Check GPU usage
   nvidia-smi  # For NVIDIA
   
   # Use faster model if available
   ollama pull orca-mini
   ```

5. **Nginx 502 Bad Gateway**
   ```bash
   # Check backend is running
   curl http://127.0.0.1:8000/api/health
   
   # Check Nginx logs
   sudo tail -f /var/log/nginx/error.log
   ```

## Monitoring & Logging

### Application Logs

```bash
# Development
python main.py  # Logs to console

# Production with Supervisor
sudo tail -f /var/log/pdfink/out.log
sudo tail -f /var/log/pdfink/err.log
```

### Metrics to Monitor

- Request latency (target: < 5s for typical queries)
- Ollama health status
- System resource usage (CPU, RAM, GPU)
- Error rates
- Cache hit ratio (if implemented)

### Health Check Endpoint

```bash
# Check all systems
curl http://localhost:8000/api/health

# Response
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00Z",
  "database": "ok",
  "llm_service": "ok"
}
```

## Rollback Procedure

If issues occur in production:

1. **Identify Issue**
   - Check error logs
   - Review recent changes
   - Test locally to reproduce

2. **Rollback Steps**
   ```bash
   # Stop current version
   docker-compose down
   # or
   sudo supervisorctl stop pdfink-backend
   
   # Checkout previous version
   git checkout <previous-commit>
   
   # Rebuild/reinstall
   docker-compose up -d
   # or
   pip install -r requirements.txt --force-reinstall
   sudo supervisorctl start pdfink-backend
   
   # Verify
   curl http://localhost:8000/api/health
   ```

3. **Validation**
   - Run smoke tests
   - Check error logs
   - Monitor for anomalies

## Success Criteria

Application is production-ready when:

- ✅ All API endpoints respond correctly
- ✅ Hallucination prevention working (< 20% invalid responses)
- ✅ Response time < 5 seconds for typical queries
- ✅ System handles 100+ page PDFs
- ✅ Graceful degradation when Ollama unavailable
- ✅ Error messages are user-friendly
- ✅ Monitoring and logging configured
- ✅ Documentation complete

---

**Last Updated**: 2024
**Version**: 1.0
**Status**: Production Ready
