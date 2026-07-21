# -*- coding: utf-8 -*-
"""
테스트 목적:
사용자님의 WaveSurfer 구글 시트(ID: 18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC9fw) 내
'jj' 탭의 퉁치기가 완료된 최종 HTS 주문 영역인 'CJ10:CM30' 데이터를 Google Sheets API로 읽어와
정상적으로 파싱할 수 있는지 검증합니다.
"""
import os
import sys
import json

# 프로젝트 루트 경로 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_KEY_PATH = os.path.join(project_root, "config", "google_key.json")
SHEET_ID = "18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC9fw"

def read_netted_orders_from_sheet():
    print("=== [Debug 071] 구글 시트 jj 탭 퉁치기 결과 주문 조회 시작 ===")
    
    if not os.path.exists(GOOGLE_KEY_PATH):
        print(f"❌ 에러: 구글 키 파일이 존재하지 않습니다: {GOOGLE_KEY_PATH}")
        return
        
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_KEY_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)
    
    try:
        # jj 탭의 CJ10:CM30 범위 요청 (구분, Type, Price, Qty)
        range_name = "'jj'!CJ10:CM30"
        print(f"-> {range_name} 범위 데이터 요청 중...")
        
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=range_name
        ).execute()
        
        rows = result.get("values", [])
        print(f"-> 조회 성공: 총 {len(rows)}행 로드됨.")
        
        parsed_orders = []
        for idx, r in enumerate(rows):
            if not r or len(r) < 4:
                continue
            
            action = r[0].strip()   # 매도 / 매수
            order_type = r[1].strip() # LOC / MOC / 지정가 등
            
            try:
                price = float(r[2]) if r[2] and r[2] != '시장가' else 0.0
            except:
                price = 0.0
                
            try:
                qty = int(r[3])
            except:
                qty = 0
                
            if qty > 0:
                parsed_orders.append({
                    "action": action,
                    "type": order_type,
                    "price": price,
                    "qty": qty
                })
                print(f"   [주문 {idx+1}] 구분: {action} | 유형: {order_type} | 가격: {price} | 수량: {qty}")
                
        print(f"\n-> 최종 파싱된 유효 주문 수: {len(parsed_orders)}건")
        
    except Exception as e:
        print(f"❌ 구글 시트 조회 실패: {e}")
        print("-> 권한 에러(403) 발생 시, 구글 시트의 [공유] 설정에")
        try:
            with open(GOOGLE_KEY_PATH, "r", encoding="utf-8") as key_f:
                key_data = json.load(key_f)
                print(f"   서비스 계정 이메일: '{key_data.get('client_email')}'")
        except:
            pass

if __name__ == "__main__":
    read_netted_orders_from_sheet()
