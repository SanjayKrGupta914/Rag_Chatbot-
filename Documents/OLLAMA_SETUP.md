# 🤖 Ollama LLM Setup Guide

This guide provides step-by-step instructions for setting up Ollama and configuring it with PDF Ink's Q&A feature.

## What is Ollama?

Ollama is a lightweight framework for running large language models locally on your machine. It provides fast inference without needing cloud services, keeping your data private and maintaining complete offline capability.

## Prerequisites

- **Operating System**: Windows, macOS, or Linux
- **Minimum RAM**: 8GB (16GB+ recommended for larger models)
- **Disk Space**: 5-10GB free space (depending on model size)
- **GPU (optional)**: NVIDIA, AMD, or Apple Silicon for faster inference

## Installation

### Windows

1. **Download Ollama**
   - Visit https://ollama.ai/download/windows
   - Download the Ollama installer (.exe)
   - Run the installer and follow the on-screen instructions

2. **Verify Installation**
   ```powershell
   ollama --version
   ```
   You should see the version number if installation was successful.

### macOS

1. **Download Ollama**
   - Visit https://ollama.ai/download/mac
   - Download the appropriate version (Intel or Apple Silicon)
   - Install as a regular macOS application

2. **Verify Installation**
   ```bash
   ollama --version
   ```

### Linux

1. **Download and Install**
   ```bash
   curl https://ollama.ai/install.sh | sh
   ```

2. **Verify Installation**
   ```bash
   ollama --version
   ```

## Starting Ollama

### Windows

Ollama starts automatically as a background service. You can verify it's running:

```powershell
# Check if Ollama service is running
Get-Service Ollama
```

### macOS & Linux

Start Ollama manually:

```bash
ollama serve
```

This will start the Ollama server on `localhost:11434`

## Pulling Models

### Using llama2 (Recommended for PDF Ink)

The default model for PDF Ink is **llama2**, a 7B parameter model that's fast and accurate.

```bash
# Pull the llama2 model (3.8GB)
ollama pull llama2
```

### Alternative Models

You can use other models depending on your needs:

**For Faster Responses:**
```bash
# Mistral 7B - Fast and efficient
ollama pull mistral

# Neural Chat - Optimized for conversations
ollama pull neural-chat
```

**For Better Accuracy:**
```bash
# Llama 2 13B - Larger model, more accurate (9GB)
ollama pull llama2:13b

# Orca Mini - Smaller but very capable (3.3GB)
ollama pull orca-mini
```

**GPU-Accelerated Models:**
If you have an NVIDIA GPU:
```bash
# Larger models become feasible
ollama pull neural-chat
ollama pull dolphin-mixtral
```

## Configuring PDF Ink with Ollama

### Default Configuration

PDF Ink is pre-configured to use:
- **Model**: `llama2`
- **URL**: `http://localhost:11434`
- **Temperature**: `0.3` (optimized for factual, document-based answers)

### Using a Different Model

1. **Open `main.py` in the PDF Extractor directory**

2. **Find the `/api/ask-question` endpoint** (around line 310-340)

3. **Change the model parameter**:
   ```python
   # In the endpoint, where QueryHandler is called:
   # Change this line:
   handler = QueryHandler(model='llama2')
   
   # To use your desired model:
   handler = QueryHandler(model='mistral')
   # or
   handler = QueryHandler(model='neural-chat')
   ```

4. **Restart the backend** for changes to take effect

## Verifying Setup

### Health Check

The backend automatically checks Ollama health on startup. You'll see:

**✓ Success**:
```
✓ LLM service ready for Q&A
```

**✗ Failed**:
```
⚠️ LLM service unavailable - Q&A features disabled
```

### Manual Health Check

```bash
# Check if Ollama is responding
curl http://localhost:11434/api/tags

# Expected response shows available models:
# {"models": [{"name": "llama2:latest", ...}]}
```

## Troubleshooting

### Ollama Not Running

**Symptom**: "Cannot connect to LLM service" error

**Solution**:
```bash
# Windows (PowerShell)
Get-Service Ollama | Start-Service

# macOS/Linux
ollama serve
```

### Model Not Found

**Symptom**: "Model 'llama2' not found" error

**Solution**:
```bash
# Pull the model
ollama pull llama2

# Verify it's installed
ollama list
```

### Out of Memory

**Symptom**: Queries hang or crash with memory error

**Solutions**:
1. Close other applications to free RAM
2. Use a smaller model:
   ```bash
   ollama pull orca-mini
   ```
3. Increase virtual memory (Windows) or swap (Linux)

### Slow Responses

**Solutions**:
1. Check Ollama logs for errors
2. Use a faster model:
   ```bash
   ollama pull mistral
   ```
3. Reduce the context window in `query_handler.py`:
   - Find: `max_context_length=8000`
   - Change to: `max_context_length=4000`

### Port Already in Use

**Symptom**: "Address already in use" error

**Solution - Windows**:
```powershell
# Find process using port 11434
netstat -ano | findstr :11434

# Kill the process (replace PID with actual ID)
taskkill /PID <PID> /F
```

**Solution - macOS/Linux**:
```bash
# Find process using port 11434
lsof -i :11434

# Kill the process
kill -9 <PID>
```

## Advanced Configuration

### Custom Temperature Settings

Temperature controls response randomness:
- **0.0-0.3**: More factual and consistent (good for document Q&A)
- **0.5-0.7**: Balanced
- **0.8-1.0**: More creative and varied

To change temperature in PDF Ink, edit `llm_service.py`:

```python
# Find this line in OllamaService.generate_response():
"temperature": 0.3,

# Change to your preferred value:
"temperature": 0.5,
```

### Context Window Management

PDF Ink automatically chunks documents to manage context. To adjust:

Edit `query_handler.py`:

```python
# Current settings
max_context_length = 8000  # Max tokens to send to LLM
chunk_size = 4000          # Size of each chunk
overlap = 500              # Overlap between chunks

# For faster processing with small documents:
max_context_length = 4000
chunk_size = 2000
overlap = 250

# For more thorough analysis of large documents:
max_context_length = 12000
chunk_size = 6000
overlap = 1000
```

## Performance Optimization

### GPU Acceleration

**NVIDIA GPUs**:
Ollama automatically uses CUDA if available. No configuration needed.

**AMD GPUs**:
Ensure ROCm is installed and Ollama detects it automatically.

**Apple Silicon**:
Ollama uses Metal acceleration automatically on M1/M2/M3 Macs.

### CPU-Only Optimization

If not using GPU, optimize CPU usage:

```bash
# Limit number of threads (replace 4 with your CPU core count)
ollama serve --num-thread 4
```

## Model Comparison for PDF Q&A

| Model | Size | Speed | Accuracy | VRAM | Best For |
|-------|------|-------|----------|------|----------|
| orca-mini | 3.3GB | ⚡⚡⚡ | ⭐⭐⭐ | 4GB | Small documents, fast responses |
| llama2 | 3.8GB | ⚡⚡ | ⭐⭐⭐⭐ | 6GB | General use (recommended) |
| mistral | 4.4GB | ⚡⚡⚡ | ⭐⭐⭐⭐ | 7GB | Fast and accurate |
| llama2:13b | 9GB | ⚡ | ⭐⭐⭐⭐⭐ | 16GB | Long documents, best accuracy |
| neural-chat | 5.1GB | ⚡⚡ | ⭐⭐⭐⭐ | 8GB | Conversational quality |

## Q&A Feature Behavior

### How It Works

1. **Extract PDF**: You upload a PDF and PDF Ink extracts all text
2. **Ask Question**: You enter a question about the PDF
3. **Chunking**: PDF Ink splits the text into manageable chunks
4. **LLM Processing**: Ollama generates an answer based only on the PDF content
5. **Validation**: PDF Ink checks if the answer came from the document
6. **Response**: You get the answer with confidence score and metadata

### Hallucination Prevention

PDF Ink uses several techniques to prevent the LLM from making up information:

1. **System Instruction**: Explicit instruction to answer only from the document
2. **Temperature**: Set to 0.3 for factual, consistent responses
3. **Response Validation**: Detects phrases like "not in document" or "based on general knowledge"
4. **Confidence Scoring**: 0-100% score indicating how confident the answer is

### Response Metadata

Each answer includes:
- **Model**: Which model generated the response
- **Answer Found**: Whether the answer was found in the document
- **Confidence**: 0-100% score of answer reliability
- **Time**: How long the inference took
- **Context**: How many characters were provided to the LLM

## Best Practices

1. **Extract Complete PDFs**: Ensure the entire PDF is extracted before asking questions
2. **Ask Specific Questions**: More specific questions get better answers
3. **Use Different Models to Compare**: If unsure about an answer, try a different model
4. **Keep Ollama Updated**: Regularly pull updated model versions
5. **Monitor Resource Usage**: Watch RAM/CPU usage during inference

## Security & Privacy

- ✅ All data stays on your machine
- ✅ No data sent to external servers
- ✅ No internet required after model download
- ✅ Complete privacy for sensitive documents

## Additional Resources

- **Ollama Documentation**: https://github.com/jmorganca/ollama
- **Available Models**: https://ollama.ai/library
- **Community Models**: https://ollama.ai/search
- **GPU Support**: https://github.com/jmorganca/ollama#gpu-support

## Support

If you encounter issues:

1. Check this guide's Troubleshooting section
2. Review Ollama logs:
   ```bash
   # Check recent Ollama activity
   ollama list
   ollama show llama2
   ```
3. Verify network connectivity and port availability
4. Try with a smaller model first
5. Check system resources (RAM, disk space)

## 🌐 Gemini Cloud Fallback

If Ollama is not installed, not running, or encounters an error, PDF Ink automatically falls back to Google's **Gemini API** (`gemini-2.5-flash`).

### Enabling Gemini Fallback

Set your API key in the `.env` file or environment:

```env
GEMINI_API_KEY=your_google_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
USE_GEMINI_FALLBACK=true
```

When Ollama is unavailable, queries will automatically route through Gemini without interrupting the user experience.

---

**Last Updated**: 2026
**Compatible with**: PDF Ink v1.0+, Ollama, Google Gemini API
