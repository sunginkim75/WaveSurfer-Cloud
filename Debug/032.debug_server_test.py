# -*- coding: utf-8 -*-
"""
테스트 목적: 수정된 main.py의 Uvicorn 서버 실행 상태 검증.
--dev 인수가 없을 때 reload가 꺼진 상태로 서버가 정상 기동되고, 8000번 포트로 GET / 요청 시 200 OK를 반환하는지 테스트.
"""

import subprocess
import time
import urllib.request
import json
import sys
import os

def test_server():
    print("1. FastAPI (main.py) 서버를 백그라운드에서 실행합니다...")
    # main.py가 있는 루트 디렉토리로 작업 경로 설정
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 윈도우 환경에서 cmd 창이 뜨지 않도록 설정
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
    proc = subprocess.Popen(
        ["uv", "run", "python", "main.py"],
        cwd=cwd,
        startupinfo=startupinfo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 서버 기동 대기
    print("2. 서버 기동을 위해 3초 대기합니다...")
    time.sleep(3)
    
    # 서버 상태 체크
    success = False
    try:
        print("3. http://localhost:8000/ 에 상태 확인 요청을 보냅니다...")
        with urllib.request.urlopen("http://localhost:8000/", timeout=5) as response:
            status = response.getcode()
            body = response.read().decode('utf-8')
            data = json.loads(body)
            print(f"응답 코드: {status}")
            print(f"응답 바디: {body}")
            
            if status == 200 and data.get("status") == "ok":
                print("★ 검증 완료: 서버가 정상 작동 중입니다!")
                success = True
            else:
                print("★ 검증 실패: 응답이 올바르지 않습니다.")
    except Exception as e:
        print(f"★ 검증 실패: 서버 요청 중 에러 발생 - {e}")
    finally:
        print("4. 백그라운드 서버 프로세스를 종료합니다.")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    test_server()
