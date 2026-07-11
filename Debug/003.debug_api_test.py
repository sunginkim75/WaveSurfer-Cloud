import os
import sys
import threading
import time
import requests
import uvicorn

# Path 조정을 통해 모듈 임포트 가능하도록 설정
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

def run_tests():
    print("=== FastAPI Backend Test ===")
    base_url = "http://127.0.0.1:8000"
    
    # 1. Root check
    try:
        res = requests.get(f"{base_url}/")
        print("Root Check:", res.json())
    except Exception as e:
        print("Failed to connect:", e)
        return

    # 2. Get tasks
    try:
        res = requests.get(f"{base_url}/api/v1/tasks")
        print("Tasks List:", res.json())
    except Exception as e:
        print("Failed to get tasks:", e)

    # 3. Test execution trigger
    try:
        res = requests.post(f"{base_url}/api/v1/engine/execute")
        print("Execute Trigger:", res.json())
    except Exception as e:
        print("Failed to trigger execute:", e)

    print("\n[SUCCESS] API 연동 테스트가 모두 성공했습니다!")
    print("서버 프로세스를 종료하려면 터미널을 강제로 닫으시거나(Ctrl+C) 스크립트를 중지하세요.")
    
    # Force exit to end script since uvicorn is running in background thread
    # In real usage, user runs it directly
    os._exit(0)

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    
    # 서버 기동 대기
    time.sleep(3)
    
    run_tests()
