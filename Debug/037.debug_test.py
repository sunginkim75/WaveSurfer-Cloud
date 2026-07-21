# -*- coding: utf-8 -*-
"""
테스트 목적:
키움증권 실전 API(mode='real') 서버에 직접 접속하여
김성인 님의 실전 계좌(6307709110)의 App Key와 App Secret을 이용해
OAuth 토큰 발급 및 해외주식 잔고 조회(TR: ust21070)를 수동으로 실행하고 결과를 검증합니다.
"""
import sys
import os
import json

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kiwoom_api_client import KiwoomAPIClient

def test_manual_balance_check():
    print("=== [Debug 037] 실전 계좌 (6307709110) 수동 조회 테스트 시작 ===")
    
    # 1. API 클라이언트 생성 (real 모드로 강제 설정)
    client = KiwoomAPIClient()
    client.mode = "real"  # 실전 서버 접속 강제 설정
    client.load_config()  # config.json 로드
    
    acct_no = "6307709110"
    
    # 2. 계좌 정보 확인
    acct_info = client.accounts.get(acct_no)
    if not acct_info:
        print(f"❌ 에러: accounts 목록에 '{acct_no}' 계좌가 없습니다.")
        return
        
    print(f"-> 계좌번호: {acct_no}")
    print(f"-> 닉네임: {acct_info.get('nickname')}")
    print(f"-> App Key: {acct_info.get('app_key')[:10]}...")
    
    # 3. OAuth 토큰 발급 시도
    print("\n[단계 1] OAuth 토큰 발급/갱신 시도 중...")
    try:
        token = client.get_token(acct_no, force_refresh=True)
        if token:
            print(f"[SUCCESS] Token발급 성공! Token (일부): {token[:15]}...")
        else:
            print("[FAIL] 토큰 발급 실패: 빈 토큰이 반환되었습니다.")
            return
    except Exception as e:
        print(f"[ERROR] 토큰 발급 중 예외 발생: {e}")
        return
        
    # 4. 실제 키움 잔고 TR (ust21070) 호출 시도 (SOXL 대상)
    print("\n[단계 2] 키움 해외주식 잔고 조회 API (ust21070) 호출 중...")
    try:
        print("-> SOXL 잔고 조회 시도...")
        balance_data = client.get_us_balance(acct_no, exchange="NY", symbol="SOXL")
        
        print("\n=== [결과] 잔고 조회 API 성공! ===")
        print(json.dumps(balance_data, indent=4, ensure_ascii=False))
        
    except Exception as e:
        print(f"[ERROR] API 호출 중 예외 발생: {e}")
        
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    test_manual_balance_check()
