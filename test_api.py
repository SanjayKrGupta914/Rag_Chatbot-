#!/usr/bin/env python3
"""
Quick test to verify PDF Ink is working
Run with: python test_api.py
"""

import sys
import json
import urllib.request
import urllib.error

def test_health_endpoint():
    """Test the health check endpoint"""
    url = "http://localhost:8000/api/health"
    
    try:
        print("Testing API health endpoint...")
        print(f"URL: {url}")
        
        with urllib.request.urlopen(url, timeout=2) as response:
            data = json.loads(response.read().decode())
            
            print("\n✅ SUCCESS! Backend is responding:\n")
            print(f"  Status: {data.get('status')}")
            print(f"  Service: {data.get('service')}")
            print(f"  Timestamp: {data.get('timestamp')}")
            
            print("\n✅ You can now:")
            print("  1. Open http://localhost:8000 in your browser")
            print("  2. Upload a PDF file")
            print("  3. View extracted text")
            
            return True
            
    except urllib.error.URLError as e:
        print(f"\n❌ FAILED: Cannot connect to backend")
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("  1. You have run: python main.py")
        print("  2. It shows: 'Uvicorn running on http://0.0.0.0:8000'")
        print("  3. Backend process is still running")
        
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_health_endpoint()
    sys.exit(0 if success else 1)
