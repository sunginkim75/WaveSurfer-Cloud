# -*- coding: utf-8 -*-
# 테스트 목적: 구글 시트 'JJ' 탭에서 6월 5일 전후의 거래 데이터(날짜, 종가, 매매모드)를 추출하고,
# 로컬에서 계산된 QQQ RSI 및 매매모드 판정과 비교하여 불일치 원인을 진단합니다.

import os
import sys
import pandas as pd
import datetime

# 프로젝트 루트 경로 설정
project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, project_root)

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    import yfinance as yf
except ImportError:
    os.system(f"{sys.executable} -m pip install google-auth google-api-python-client yfinance pandas -q")
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    import yfinance as yf

GOOGLE_KEY_PATH = os.path.join(project_root, "config", "google_key.json")
SHEET_ID = "18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC6fw"

def main():
    print("=" * 70)
    print("6/5 매매 모드 불일치 원인 분석 테스트")
    print("=" * 70)
    
    try:
        # 1. 구글 시트 'JJ' 시트 전체 로드
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="'JJ'!J1:AP1000"  # J(거래일자), K(종가), L(매매모드), AP(총자산)
        ).execute()
        
        rows = result.get("values", [])
        print(f"구글 시트 'JJ' 탭 총 {len(rows)}개 행 읽음\n")
        
        # 6/5 근처의 데이터 필터링
        print("--- [구글 시트] 6월 5일 전후의 매매 기록 ---")
        sheet_records = []
        for i, row in enumerate(rows):
            if len(row) >= 3 and row[0] and row[1]:
                date_str = str(row[0]).strip()
                if "06." in date_str or "05." in date_str or "07." in date_str:  # 5, 6, 7월 데이터 수집
                    print(f"Row {i+1:3d}: 날짜={row[0]:12s} | 종가={row[1]:8s} | 매매모드={row[2]:6s}")
                    sheet_records.append({
                        "row_num": i+1,
                        "date_str": date_str,
                        "close": row[1],
                        "mode": row[2]
                    })
                    
    except Exception as e:
        print(f"구글 시트 로드 오류: {e}")

if __name__ == "__main__":
    main()
