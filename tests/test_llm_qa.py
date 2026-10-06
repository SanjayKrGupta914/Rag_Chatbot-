import requests
import json

BASE = "http://localhost:8000"

SAMPLE_TEXT = """
This is a sample document used to verify the LLM Q&A integration.
The project name is PDF Ink. The release year is 2024.
Features include accurate text extraction, local LLM Q&A, and privacy.
"""

def test_ask_question():
    url = f"{BASE}/api/ask-question"
    payload = {
        "pdf_text": SAMPLE_TEXT,
        "question": "What is the project name?",
        "model": "llama2"
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        print('Status:', r.status_code)
        try:
            print(json.dumps(r.json(), indent=2))
        except Exception:
            print('Non-JSON response:', r.text)
    except Exception as e:
        print('Request failed:', e)

if __name__ == '__main__':
    test_ask_question()
