# -*- coding: utf-8 -*-
"""
테스트 목적:
키움증권 실전 API(mode='real') 서버에 접속하여
김성인 님의 5573176310 계좌의 App Key와 App Secret...
"""
import sys
import os
import json

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kiwoom_api_client import KiwoomAPIClient

def test_tqqq_balance_check():
    print("=== [Debug 065] 실전 계좌 (5573176310) TQQQ 원시 잔고 조회 디버그 ===")
    
    client = KiwoomAPIClient()
    client.mode = "real"  # 실전 서버 접속 강제
    client.load_config()  # config.json 로드
    
    acct_no = "5573176310"
    ticker = "TQQQ"
    
    acct_info = client.accounts.get(acct_no)
    if not acct_info:
        print(f"❌ 에러: accounts 목록에 '{acct_no}' 계좌가 없습니다.")
        return
        
    print(f"-> 계좌번호: {acct_no}")
    print(f"-> 닉네임: {acct_info.get('nickname')}")
    
    # OAuth 토큰 발급
    print("\n[단계 1] OAuth 토큰 발급 시도...")
    try:
        token = client.get_token(acct_no, force_refresh=True)
        if token:
            print(f"[SUCCESS] Token 발급 성공! Token (일부): {token[:15]}...")
        else:
            print("[FAIL] 토큰 발급 실패: 빈 토큰이 반환되었습니다.")
            return
    except Exception as e:
        print(f"[ERROR] 토큰 발급 중 예외 발생: {e}")
        return
        
    # 원장잔고조회 API 호출
    print("\n[단계 2] 키움 해외주식 잔고 조회 API (ust21070) 원시 응답 확인...")
    try:
        print(f"-> {ticker} 잔고 조회 API 직접 호출 중...")
        balance_data = client.get_us_balance(acct_no, exchange="ND", symbol=ticker)
        
        print("\n=== [결과] 잔고 조회 API 응답 데이터 ===")
        print(json.dumps(balance_data, indent=4, ensure_ascii=False))
        
        # 파일로 임시 저장하여 상세 검토할 수 있도록 백업
        backup_path = "Debug/065.response_dump.json"
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(balance_data, f, indent=4, ensure_ascii=False)
        print(f"\n[성공] 원시 응답 JSON이 '{backup_path}'에 백업되었습니다.")
        
    except Exception as e:
        print(f"[ERROR] API 호출 중 예외 발생: {e}")
        
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    test_tqqq_balance_check()
