# 🚀 Quick Start Guide - PDF Ink with Ollama

Get PDF Ink with AI Q&A capabilities running in 5 minutes.

## Prerequisites

- Python 3.11+
- Ollama installed ([download here](https://ollama.ai))
- 8GB+ RAM
- 10GB+ disk space

## Installation (5 Minutes)

### Step 1: Download & Install Ollama

Visit https://ollama.ai and download for your OS.

### Step 2: Pull the Model

```bash
ollama pull llama2
```

This downloads a 3.8GB model (first time only).

### Step 3: Start Ollama

**Windows**: Ollama starts automatically

**macOS/Linux**:
```bash
ollama serve
```

### Step 4: Install Python Dependencies

```bash
cd "Pdf Extractor"
pip install -r requirements.txt
```

### Step 5: Start the Application

```bash
python main.py
```

You'll see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 6: Open in Browser

Navigate to: **http://localhost:8000**

## Using the Application

### Extracting Text from PDF

1. Click the upload area or drag & drop a PDF
2. Wait for "Extraction complete" message
3. View extracted text in the text box

### Asking Questions About Your PDF

1. Scroll down to the Q&A section
2. Enter your question (e.g., "What is the main topic?")
3. Click "Ask" or press Enter
4. Get instant answer with confidence score

### Example Questions

**For a tech document:**
- "What are the system requirements?"
- "What is the API endpoint for user authentication?"
- "List the main features described in this document"

**For a report:**
- "What was the total revenue?"
- "When was this report created?"
- "What are the recommendations?"

**For a research paper:**
- "What methodology was used?"
- "What were the findings?"
- "How does this compare to prior work?"

## Troubleshooting

### "API connection issue"

**Solution**: Make sure backend is running
```bash
# In new terminal:
python main.py
```

### "LLM service unavailable"

**Solution**: Make sure Ollama is running
```bash
# In new terminal:
ollama serve
```

### "Model 'llama2' not found"

**Solution**: Pull the model
```bash
ollama pull llama2
ollama list  # verify it's there
```

### "Out of Memory" error

**Solution**: Use a smaller model
```bash
ollama pull orca-mini
```

Then change in `main.py` line ~315:
```python
handler = QueryHandler(model='orca-mini')
```

## What's Next?

### Advanced Setup

- [Ollama Setup Guide](OLLAMA_SETUP.md) - Full configuration options
- [Testing & Deployment](LLM_TESTING_DEPLOYMENT.md) - Production deployment

### Custom Models

Try other models for different performance/accuracy:

```bash
ollama pull mistral        # Fast (4.4GB)
ollama pull neural-chat    # Conversational (5.1GB)
ollama pull llama2:13b     # More accurate (9GB)
```

### Tips for Best Results

1. **Extract complete PDFs** - Ensures context is available
2. **Ask specific questions** - Better results than vague questions
3. **Use confidence scores** - Answers < 40% confidence may need verification
4. **Enable GPU** - Speeds up inference significantly
5. **Monitor response time** - Accept 2-10 second wait times

## Common Questions

**Q: Is my data sent anywhere?**
A: No! Everything runs locally on your machine. Zero data leaves your device.

**Q: Can I use different models?**
A: Yes! Ollama supports 30+ models. Just download and switch in settings.

**Q: What if answers seem wrong?**
A: The confidence score indicates accuracy. Low confidence answers need verification.

**Q: How can I make it faster?**
A: Use GPU acceleration (automatic for NVIDIA/AMD/Apple Silicon) or try a smaller model.

**Q: Can I ask about things not in the PDF?**
A: The LLM will tell you "not in document" if the answer isn't there.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl/Cmd + K** | Copy extracted text |
| **Ctrl/Cmd + D** | Download extracted text |
| **Enter** (in question box) | Submit question |

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8GB | 16GB+ |
| Disk | 10GB | 20GB+ |
| GPU | None | NVIDIA/AMD/Apple |
| CPU | 4 cores | 8+ cores |

## Performance Expectations

| Operation | Time | Notes |
|-----------|------|-------|
| PDF extraction | 1-5 sec | Depends on PDF size |
| Q&A inference | 2-10 sec | Depends on model/GPU |
| Ollama startup | 3-5 sec | One-time on boot |

## Next Steps

1. Try with your own PDFs
2. Test different questions
3. Experiment with different models
4. Read [OLLAMA_SETUP.md](OLLAMA_SETUP.md) for advanced options
5. Check [LLM_TESTING_DEPLOYMENT.md](LLM_TESTING_DEPLOYMENT.md) for production deployment

## Support

For issues:
1. Check troubleshooting section above
2. Review detailed guides: OLLAMA_SETUP.md, LLM_TESTING_DEPLOYMENT.md
3. Verify Ollama health: `curl http://localhost:11434/api/tags`
4. Check backend health: `curl http://localhost:8000/api/health`

---

**Happy extracting! 📄✨**
