# -*- coding: utf-8 -*-
"""
테스트 목적:
기존 프로젝트 내의 GoogleSheetManager(gspread 기반)를 활용하여
새로운 구글 시트(ID: 18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC6fw)의
'jj' 탭 내 CJ10:CM30(퉁치기 완료된 HTS 주문 범위) 데이터를 성공적으로 로드하는지 검증합니다.
"""
import os
import sys

# 프로젝트 루트 경로 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.google_sheet import GoogleSheetManager

def test_gspread_netted_orders():
    print("=== [Debug 072] gspread 기반 jj 탭 주문 조회 테스트 시작 ===")
    
    # 1. GoogleSheetManager 생성
    gsm = GoogleSheetManager()
    
    # 2. 신규 시트 ID 강제 세팅 (18KaZk-...)
    gsm.sheet_id = "18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC6fw"
    print(f"-> 대상 시트 ID: {gsm.sheet_id}")
    
    # 3. 연결
    if not gsm.connect():
        print("❌ 에러: 구글 시트 연결 실패")
        return
        
    # 4. 'jj' 탭 로드
    sheet = gsm.get_sheet_by_name("jj")
    if not sheet:
        print("❌ 에러: 'jj' 탭을 찾을 수 없습니다.")
        return
        
    print("-> 'jj' 탭 로드 성공. CJ10:CM30 범위 데이터 가져오는 중...")
    
    try:
        # gspread에서 범위 가져오기
        raw_vals = sheet.get_values("CJ10:CM30")
        print(f"-> 로드된 행 수: {len(raw_vals)}")
        
        parsed_orders = []
        for idx, row in enumerate(raw_vals):
            if not row or len(row) < 4:
                continue
            
            action = row[0].strip()   # 매도 / 매수
            order_type = row[1].strip() # LOC / MOC / 지정가 등
            price_str = row[2].strip() if len(row) > 2 else ""
            qty_str = row[3].strip() if len(row) > 3 else ""
            
            try:
                price = float(price_str) if price_str and price_str != '시장가' else 0.0
            except:
                price = 0.0
                
            try:
                qty = int(qty_str.replace(',', ''))
            except:
                qty = 0
                
            if qty > 0:
                parsed_orders.append({
                    "action": action,
                    "type": order_type,
                    "price": price,
                    "qty": qty
                })
                print(f"   [주문 {idx+1}] {action} | {order_type} | 단가: {price} | 수량: {qty}")
                
        print(f"\n-> 최종 파싱 성공 주문 수: {len(parsed_orders)}건")
        
    except Exception as e:
        print(f"❌ 데이터 로드 중 예외 발생: {e}")

if __name__ == "__main__":
    test_gspread_netted_orders()
