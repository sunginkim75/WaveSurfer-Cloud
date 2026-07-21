# -*- coding: utf-8 -*-
"""
테스트 목적: 8000번 포트를 사용하는 프로세스를 찾아서 확인하고, uvicorn의 무한 리로드 원인을 분석하기 위한 진단 스크립트.
"""
import os
import subprocess
import sys

def check_port_8000():
    print("=== 8000번 포트 점유 프로세스 확인 ===")
    try:
        # Windows의 netstat 명령어로 8000 포트 확인
        result = subprocess.run(
            ["netstat", "-ano"], 
            capture_output=True, 
            text=True, 
            encoding="cp949", 
            errors="ignore"
        )
        lines = result.stdout.splitlines()
        found = False
        for line in lines:
            if ":8000" in line:
                print(line)
                found = True
        if not found:
            print("8000번 포트를 점유 중인 프로세스가 없습니다.")
    except Exception as e:
        print(f"포트 확인 실패: {e}")

if __name__ == "__main__":
    check_port_8000()
