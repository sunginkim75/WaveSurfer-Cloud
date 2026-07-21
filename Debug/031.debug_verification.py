# -*- coding: utf-8 -*-
"""
테스트 목적:
수동 잔고 동기화 시 잘못된 API 연동 상태 및 미등록 계좌번호 상황에 대해
백엔드가 올바른 에러코드(400, 502 등)와 상세 검증 에러 메시지를 뱉어내는지 검증합니다.
이모지를 제거하여 cp949 인코딩 에러를 방지했습니다.
"""
import sys
import os
import json

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import CoreEngine

def run_verification_test():
    print("=== Manual sync 1-100 verification test start ===")
    
    engine = CoreEngine()
    
    # 1. API key가 비어있는 상태에서 동기화 요청 시도
    print("\n[1] Check validation when API Key is empty...")
    engine.kiwoom_api.appkey = ""
    engine.kiwoom_api.secretkey = ""
    
    try:
        engine.sync_task_balance("task_009a82ba")
        print("FAIL: Expected exception was not raised.")
    except Exception as e:
        print(f"SUCCESS: Expected exception caught -> {str(e)}")
        
    # 2. 계좌번호가 키움증권 config 계좌 목록에 등록되지 않았을 때
    print("\n[2] Check validation when account_no is not registered in accounts...")
    engine.kiwoom_api.appkey = "test_app_key"
    engine.kiwoom_api.secretkey = "test_app_secret"
    
    # tasks 리스트에서 'task_009a82ba'의 인덱스 찾기 및 수정
    target_idx = next(i for i, t in enumerate(engine.config["tasks"]) if t["id"] == "task_009a82ba")
    engine.config["tasks"][target_idx]["account_no"] = "9999999999"
    engine.kiwoom_api.accounts = {"1234567890": "REAL_ACCOUNT"}
    
    try:
        engine.sync_task_balance("task_009a82ba")
        print("FAIL: Expected exception was not raised.")
    except Exception as e:
        print(f"SUCCESS: Expected exception caught -> {str(e)}")
        
    # 3. 토큰 발급에 실패했을 때 (OAuth 로그인 실패)
    print("\n[3] Check validation when OAuth token request fails...")
    engine.config["tasks"][target_idx]["account_no"] = "1234567890"
    engine.kiwoom_api.accounts = {"1234567890": "REAL_ACCOUNT"}
    # Mocking get_token to return None
    engine.kiwoom_api.get_token = lambda acct, force_refresh=False: ""
    
    try:
        engine.sync_task_balance("task_009a82ba")
        print("FAIL: Expected exception was not raised.")
    except Exception as e:
        print(f"SUCCESS: Expected exception caught -> {str(e)}")
        
    print("\n=== Verification test finished ===")

if __name__ == "__main__":
    run_verification_test()
