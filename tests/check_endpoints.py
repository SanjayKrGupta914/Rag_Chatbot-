import time, requests
base='http://127.0.0.1:8000'
# Wait briefly for server to start
for i in range(10):
    try:
        r=requests.get(base+'/api/health', timeout=2)
        if r.status_code==200:
            print('Server up')
            break
    except Exception:
        time.sleep(0.5)
else:
    print('Server did not respond to /api/health')

paths=[('/api/health','GET'),('/api/llm/health','GET'),('/api/ask-question','OPTIONS')]
for path,method in paths:
    try:
        if method=='GET':
            r=requests.get(base+path, timeout=10)
        else:
            r=requests.options(base+path, timeout=10)
        print(path, r.status_code)
        try:
            print(r.json())
        except Exception:
            print(r.text[:400])
    except Exception as e:
        print(path, 'ERROR', e)

# Try POST
try:
    payload={'pdf_text':'Sample PDF. Name: PDF Ink.','question':'What is the project name?','model':'llama2'}
    r=requests.post(base+'/api/ask-question', json=payload, timeout=15)
    print('/api/ask-question POST', r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text[:400])
except Exception as e:
    print('/api/ask-question POST ERROR', e)
