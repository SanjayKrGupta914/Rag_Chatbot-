#!/usr/bin/env python3
"""
PDF Ink - Setup Verification Script
Run this to verify everything is working correctly
"""

import os
import sys
import socket
import subprocess
from pathlib import Path

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def check_port(port):
    """Check if a port is in use"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def verify_packages():
    """Verify required packages are installed"""
    print_header("✓ Checking Python Packages")
    
    required = {
        'fastapi': 'FastAPI',
        'uvicorn': 'Uvicorn',
        'pymupdf': 'PyMuPDF',
        'pymupdf4llm': 'PyMuPDF4LLM',
    }
    
    missing = []
    for module, name in required.items():
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} - NOT INSTALLED")
            missing.append(module)
    
    if missing:
        print(f"\n  Install missing packages:")
        print(f"  pip install {' '.join(missing)}")
        return False
    
    return True

def verify_files():
    """Verify required files exist"""
    print_header("✓ Checking Project Files")
    
    required_files = {
        'main.py': 'Backend Application',
        'static/index.html': 'Frontend HTML',
        'static/script.js': 'Frontend JavaScript',
        'static/style.css': 'Frontend Styles',
        'requirements.txt': 'Dependencies',
    }
    
    all_exist = True
    for file_path, description in required_files.items():
        full_path = Path(file_path)
        if full_path.exists():
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description} - NOT FOUND ({file_path})")
            all_exist = False
    
    return all_exist

def check_ports():
    """Check if ports are available"""
    print_header("✓ Checking Port Availability")
    
    ports = {
        8000: 'Backend API (FastAPI)',
        5500: 'Dev Server (Live Server)',
        3000: 'Common Dev Port',
    }
    
    for port, description in ports.items():
        if check_port(port):
            status = "🔴 IN USE"
        else:
            status = "🟢 AVAILABLE"
        print(f"  Port {port}: {status} - {description}")
    
    return not check_port(8000)  # Port 8000 should be free

def print_instructions():
    """Print setup instructions"""
    print_header("📖 Setup Instructions")
    
    print("""
1️⃣  START THE BACKEND (in terminal)
   
   cd "c:\\Users\\godre\\Desktop\\Morth\\Pdf Extractor"
   python main.py
   
   ✅ Wait for: "Uvicorn running on http://0.0.0.0:8000"

2️⃣  OPEN IN BROWSER
   
   ➜ http://localhost:8000
   
   ❌ NOT: http://localhost:5500 or http://localhost:3000

3️⃣  UPLOAD A PDF
   
   • Drag and drop a PDF file
   • Wait for extraction
   • View results

4️⃣  COMMON ISSUES
   
   Q: "Port 8000 already in use"
   A: Kill other processes: 
      Get-Process -Port 8000 | Stop-Process -Force
   
   Q: "API errors / 404 responses"
   A: Make sure you're on http://localhost:8000
      NOT any dev server port
   
   Q: "Module not found errors"
   A: Run: pip install -r requirements.txt --upgrade

""")

def test_api():
    """Test API endpoint"""
    print_header("⚡ Testing API Endpoint")
    
    try:
        import urllib.request
        import json
        
        url = "http://localhost:8000/api/health"
        
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                data = json.loads(response.read())
                print(f"  ✅ API is responding!")
                print(f"  Status: {data.get('status')}")
                print(f"  Service: {data.get('service')}")
                return True
        except urllib.error.URLError as e:
            print(f"  ❌ Cannot connect to API")
            print(f"  Error: {e}")
            print(f"  Make sure 'python main.py' is running")
            return False
    except Exception as e:
        print(f"  ⚠️  Test skipped: {e}")
        return None

def main():
    """Run all verifications"""
    os.chdir(Path(__file__).parent)
    
    print("\n" + "="*60)
    print("  PDF INK - SETUP VERIFICATION")
    print("="*60)
    
    results = {
        'Files': verify_files(),
        'Packages': verify_packages(),
        'Ports': check_ports(),
    }
    
    # Try API test
    api_test = test_api()
    
    print_instructions()
    
    # Summary
    print_header("📊 Summary")
    
    all_good = all(results.values())
    
    if all_good:
        if api_test:
            print("  🎉 Everything is working perfectly!")
            print("  → Open http://localhost:8000 in your browser")
        else:
            print("  ✅ Setup is complete!")
            print("  ⏳ Waiting for backend to start...")
            print("  → Run: python main.py")
            print("  → Then open http://localhost:8000")
    else:
        print("  ⚠️  Some issues detected above")
        print("  👆 Follow the instructions above to fix them")
    
    print("\n")
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())
