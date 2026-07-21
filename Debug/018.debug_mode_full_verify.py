# -*- coding: utf-8 -*-
# 테스트 목적: 2025년 1월 1일부터 현재까지의 전 기간에 대해 구글 시트 'JJ' 탭의 실제 매매 모드와 
# 로컬 백테스터 시뮬레이션 결과를 일자별로 1:1 전수 비교하여 모드 일치 여부를 검증합니다.

import os
import sys
import pandas as pd

# 프로젝트 루트 경로 설정
project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, project_root)

from google.oauth2 import service_account
from googleapiclient.discovery import build
from core.backtester import Backtester

GOOGLE_KEY_PATH = os.path.join(project_root, "config", "google_key.json")
SHEET_ID = "18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC6fw"

def main():
    print("=" * 80)
    print("2025-01-01 이후 전 기간 매매 모드 1:1 대조 검증 시작")
    print("=" * 80)
    
    try:
        # 1. 구글 시트 'JJ' 탭에서 거래일자(J) 및 매매모드(L) 로드
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="'JJ'!J10:L1000"  # 날짜(J), 매매모드(L)
        ).execute()
        
        rows = result.get("values", [])
        sheet_modes = {}
        for row in rows:
            if len(row) >= 3 and row[0] and row[2]:
                raw_date = str(row[0]).strip()
                # 날짜 형식 변환: "07.10.(금)" -> "2026-07-10" or "07.10"
                # 년도는 데이터 순서 및 상단 헤더의 맥락에 따라 2025년 또는 2026년으로 추정해야 함
                # 구글 시트는 시간 순서대로 작성되어 있으므로 날짜를 순차적으로 변환
                pass
        
        # 위 방식 대신 날짜가 명확한 'compare_result.txt' 등에서 사용한 파싱 규칙을 활용
        # JJ 시트의 행 중 7/1~7/10이 Row 31~37 이므로 역산하여 2025년도 날짜를 역추적함.
        # 더 확실한 비교를 위해, 구글 시트 'JJ'의 J열 날짜 포맷은 "MM.DD.(요일)" 형태입니다.
        # 연도는 2025년에서 시작해 12월을 지나 다시 1월이 되면 2026년으로 전이됩니다.
        year = 2025
        last_month = 0
        for i, row in enumerate(rows):
            if len(row) >= 3 and row[0] and row[2]:
                date_str = str(row[0]).strip()
                mode_str = str(row[2]).strip().replace("모드", "") # "안전 " -> "안전"
                
                parts = date_str.split('.')
                if len(parts) >= 2:
                    try:
                        month = int(parts[0])
                        day = int(parts[1].split('(')[0])
                        
                        # 12월에서 1월로 넘어가면 연도 증가
                        if last_month == 12 and month == 1:
                            year = 2026
                        last_month = month
                        
                        formatted_date = f"{year}-{month:02d}-{day:02d}"
                        sheet_modes[formatted_date] = mode_str
                    except ValueError:
                        continue
                        
        print(f"구글 시트 2025년 이후 데이터 {len(sheet_modes)}개 매핑 완료")
        
        # 2. 로컬 백테스터 실행 (2025-01-01 ~ 2026-07-15)
        bt_result = Backtester.run_backtest(
            ticker="SOXL",
            start_date_str="2025-01-01",
            end_date_str="2026-07-15",
            seed_amt=10000.0,
            safe_buy_pct=3.0,
            safe_sell_pct=0.2,
            agg_buy_pct=5.0,
            agg_sell_pct=2.5,
            split_count=7,
            update_period=10,
            compounding_profit_rate=80.0,
            compounding_loss_rate=30.0
        )
        
        tx_table = bt_result["detailedTxTable"]
        
        # 3. 대조 검증 수행
        print(f"\n검증 대상 거래일수: {len(tx_table)}일")
        print(f"{'날짜':<12} | {'시트 모드':<8} | {'백테스터 모드':<10} | {'결과'}")
        print("-" * 60)
        
        mismatches = []
        match_count = 0
        total_count = 0
        
        for row in tx_table:
            date_str = row["date"]
            if date_str in sheet_modes:
                total_count += 1
                sheet_m = sheet_modes[date_str]
                local_m = row["mode"].replace("모드", "")
                
                is_match = (sheet_m == local_m)
                if is_match:
                    match_count += 1
                else:
                    mismatches.append((date_str, sheet_m, local_m))
                    
        # 불일치 목록 출력 (최대 20개)
        if mismatches:
            print(f"\n[불일치 발생] 총 {len(mismatches)}건의 모드 불일치 발견:")
            for d, sm, lm in mismatches[:20]:
                print(f"  - 날짜: {d} | 시트: {sm} | 로컬: {lm}")
            if len(mismatches) > 20:
                print(f"  ...외 {len(mismatches)-20}건 추가 생략")
        else:
            print("\n[성공] 전 기간 불일치 0건!")
            
        print("\n" + "=" * 80)
        match_pct = (match_count / total_count * 100) if total_count > 0 else 0
        print(f"최종 일치 요약: 총 {total_count}일 중 {match_count}일 일치 (일치율: {match_pct:.2f}%)")
        print("=" * 80)
        
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    main()
