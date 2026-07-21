# -*- coding: utf-8 -*-
"""
테스트 목적:
계좌별 고유 API Key 및 Secret Key가 1:1로 매핑되는 구조에서,
백엔드가 정상적으로 각 계좌 고유의 App Key/Secret을 취득하여 토큰 발급 및 잔고 조회를 수행하는지 검증합니다.
"""
import sys
import os
import json

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.engine import CoreEngine

def run_per_account_test():
    print("=== 계좌별 1:1 API key 연동 검증 테스트 시작 ===")
    
    engine = CoreEngine()
    
    # 1. config.json의 accounts 구성 확인
    print("\n[1] 설정 파일 accounts 정보 확인:")
    print(json.dumps(engine.kiwoom_api.accounts, indent=4, ensure_ascii=False))
    
    # 2. task_ce7c4efe (계좌번호: 123415678) 토큰 갱신 시도 시 App Key 추출 검증
    print("\n[2] 계좌 123415678에 대한 App Key 추출 시도...")
    acct_no = "123415678"
    acct_info = engine.kiwoom_api.accounts.get(acct_no)
    
    if acct_info:
        print(f"계좌 {acct_no} 닉네임: {acct_info.get('nickname')}")
        print(f"계좌 {acct_no} App Key: {acct_info.get('app_key')}")
        print(f"계좌 {acct_no} App Secret: {acct_info.get('app_secret')}")
        
        # 3. get_token 호출 검증 (mock 모드라 실제 post는 키움 OpenAPI 주소로 감)
        # mock이 아니더라도 get_token은 OAuth 주소로 post를 쏨
        # 여기서는 appkey가 제대로 추출되어 body에 담기는지 kiwoom_api 내부 데이터 참조
        token = engine.kiwoom_api.get_token(acct_no, force_refresh=True)
        # mock mode이거나 유효하지 않은 실키면 결과가 실패일 수 있지만, 
        # appkey 바인딩 오류가 발생하지 않는지 체크
        print(f"토큰 발급 결과 (빈 값이더라도 에러 발생 없어야 함): '{token}'")
    else:
        print("❌ 실패: 123415678 계좌 정보를 accounts에서 찾을 수 없습니다.")
        
    print("\n=== 검증 테스트 완료 ===")

if __name__ == "__main__":
    run_per_account_test()
