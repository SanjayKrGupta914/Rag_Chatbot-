#!/usr/bin/env python3
"""Test new /summarize and /ask endpoints."""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Sample PDF text for testing
SAMPLE_PDF_TEXT = """
Python is a high-level, interpreted programming language known for its simplicity and readability.
It was created by Guido van Rossum and first released in 1991.
Python supports multiple programming paradigms including object-oriented, functional, and procedural programming.

Key features of Python:
1. Easy to learn and read syntax
2. Dynamic typing
3. Automatic memory management
4. Extensive standard library
5. Cross-platform compatibility

Python is used for web development, data science, artificial intelligence, machine learning, and automation.
Popular frameworks include Django, Flask for web development, and NumPy, Pandas for data science.

Python's community is one of the largest and most active in the programming world.
The language continues to evolve with regular releases and improvements.
"""

def test_summarize():
    """Test the /summarize endpoint."""
    print("\n=== Testing /summarize endpoint ===")
    
    payload = {
        "pdf_text": SAMPLE_PDF_TEXT,
        "model": "llama2"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/summarize", json=payload, timeout=60)
        print(f"Status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            print(f"✓ Success: {data.get('status')}")
            print(f"Summary: {data.get('summary', '')[:200]}...")
            print(f"Model used: {data.get('model_used')}")
            print(f"Processing time: {data.get('processing_time')}s")
        else:
            print(f"✗ Error: {response.text}")
    except Exception as e:
        print(f"✗ Exception: {e}")

def test_ask():
    """Test the /ask endpoint with chat history."""
    print("\n=== Testing /ask endpoint (with chat history) ===")
    
    chat_history = []
    
    # First question
    payload1 = {
        "pdf_text": SAMPLE_PDF_TEXT,
        "question": "When was Python created?",
        "chat_history": chat_history,
        "model": "llama2"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/ask", json=payload1, timeout=60)
        print(f"\nQuestion 1 Status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            print(f"✓ Answer: {data.get('answer', '')[:150]}...")
            print(f"Has answer: {data.get('has_answer')}")
            print(f"Confidence: {data.get('confidence')}")
            
            # Add to history
            chat_history.append({"role": "user", "content": "When was Python created?"})
            chat_history.append({"role": "assistant", "content": data.get('answer', '')})
        else:
            print(f"✗ Error: {response.text}")
    except Exception as e:
        print(f"✗ Exception: {e}")
    
    # Second question (with history)
    payload2 = {
        "pdf_text": SAMPLE_PDF_TEXT,
        "question": "What are the key features mentioned?",
        "chat_history": chat_history,
        "model": "llama2"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/ask", json=payload2, timeout=60)
        print(f"\nQuestion 2 Status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            print(f"✓ Answer: {data.get('answer', '')[:150]}...")
            print(f"Has answer: {data.get('has_answer')}")
            print(f"Chat history length: {len(chat_history)}")
        else:
            print(f"✗ Error: {response.text}")
    except Exception as e:
        print(f"✗ Exception: {e}")

def test_health():
    """Test health check."""
    print("\n=== Testing health endpoints ===")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print(f"API Health: {response.status_code} - {response.json().get('status')}")
    except Exception as e:
        print(f"API Health check failed: {e}")
    
    try:
        response = requests.get(f"{BASE_URL}/api/llm/health", timeout=5)
        print(f"LLM Health: {response.status_code} - {response.json().get('status')}")
    except Exception as e:
        print(f"LLM Health check failed: {e}")

if __name__ == "__main__":
    print("Starting endpoint tests...")
    test_health()
    test_summarize()
    test_ask()
    print("\n=== Tests complete ===")
