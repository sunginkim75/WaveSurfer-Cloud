# -*- coding: utf-8 -*-
"""
테스트 목적:
키움증권 실전 API(mode='real') 서버에 접속하여
김성인 님의 5573176310 계좌의 미국주식 주문/체결 내역 상세 API(TR: ust22312)를 호출하고,
돌아오는 원시 JSON 데이터를 덤프하여 체결 이력 파싱 필드명을 디버깅합니다.
"""
import sys
import os
import json
import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kiwoom_api_client import KiwoomAPIClient

def test_order_history_check():
    print("=== [Debug 069] 실전 계좌 TQQQ 주문체결이력 조회 디버그 ===")
    
    client = KiwoomAPIClient()
    client.mode = "real"
    client.load_config()
    
    acct_no = "5573176310"
    ticker = "TQQQ"
    
    # 최근 10일 조회 범위 설정
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=10)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    
    token = client.get_token(acct_no)
    if not token:
        print("❌ 에러: 토큰 발급 실패")
        return
        
    # 테스트할 바디 조합 목록
    body_variations = [
        # 1. 기본 조합 (inqr_strt_dt / inqr_end_dt)
        {
            "acct_no": acct_no,
            "stex_tp": "ND",
            "stk_cd": ticker,
            "inqr_strt_dt": start_date,
            "inqr_end_dt": end_date
        },
        # 2. 조회구분 및 체결구분 추가
        {
            "acct_no": acct_no,
            "stex_tp": "ND",
            "stk_cd": ticker,
            "inqr_strt_dt": start_date,
            "inqr_end_dt": end_date,
            "ccld_dvs": "0", # 전체
            "ord_dvs": "0"   # 전체
        },
        # 3. 영문 파라미터 변형 (start_date / end_date / match_dvs)
        {
            "acct_no": acct_no,
            "stex_tp": "ND",
            "stk_cd": ticker,
            "start_dt": start_date,
            "end_dt": end_date,
            "ccld_tp": "0"
        },
        # 4. inqr_dvs 추가
        {
            "acct_no": acct_no,
            "stex_tp": "ND",
            "stk_cd": ticker,
            "inqr_strt_dt": start_date,
            "inqr_end_dt": end_date,
            "inqr_dvs": "0",
            "ccld_dvs": "0"
        },
        # 5. 아주 단순한 파라미터 (계좌와 거래소만)
        {
            "acct_no": acct_no,
            "stex_tp": "ND",
            "stk_cd": ticker
        }
    ]
    
    url = f"{client.base_url}/api/us/acnt/match"
    import requests
    print("=== 파라미터 스캔 시작 ===")
    for idx, body in enumerate(body_variations):
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "api-id": "ust22312",
            "authorization": f"Bearer {token}"
        }
        try:
            response = requests.post(url, headers=headers, json=body, timeout=5)
            res_json = response.json()
            status = response.status_code
            print(f"[*] 조합 {idx + 1} - Status: {status}")
            print(f"    Body: {body}")
            print(f"    Res: {json.dumps(res_json, indent=2, ensure_ascii=False)[:300]}...\n")
        except Exception as e:
            print(f"[!] 조합 {idx + 1} 에러: {e}")
            
    print("=== 파라미터 스캔 완료 ===")

if __name__ == "__main__":
    test_order_history_check()
