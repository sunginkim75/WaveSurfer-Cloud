# -*- coding: utf-8 -*-
# 테스트 목적: 구글 시트의 'WAVE SURFER 가이드' 탭(gid=698402042) 및 'JJ' 탭(gid=879227790)에서 
# 모드 가이드 공식과 6월 5일 전후 데이터를 로드하여 로컬 매매 모드 계산 방식과의 차이점을 규명합니다.

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
    output = []
    output.append("=" * 80)
    output.append("구글 시트 'WAVE SURFER 가이드' 및 'JJ' 탭 6/5 전후 분석")
    output.append("=" * 80)
    
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)
        
        # 1. WAVE SURFER 가이드 시트 내용 읽기 (A1:H50)
        guide_result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="'WAVE SURFER 가이드'!A1:H50"
        ).execute()
        guide_rows = guide_result.get("values", [])
        output.append("\n--- [WAVE SURFER 가이드] 탭 데이터 ---")
        for i, row in enumerate(guide_rows):
            non_empty = [c for c in row if c and str(c).strip()]
            if non_empty:
                output.append(f"Row {i+1:2d}: {row}")
                
        # 2. JJ 시트에서 6월 데이터 읽기
        jj_result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="'JJ'!J1:M1000"  # J(거래일자), K(종가), L(매매모드), M(변동률)
        ).execute()
        jj_rows = jj_result.get("values", [])
        
        output.append("\n--- [JJ 시트] 5월 ~ 7월 매매 모드 기록 ---")
        for i, row in enumerate(jj_rows):
            if len(row) >= 3 and row[0] and row[1]:
                date_str = str(row[0]).strip()
                # 5월, 6월, 7월에 속하는 행만 출력
                if any(m in date_str for m in ["05.", "06.", "07."]):
                    output.append(f"Row {i+1:3d} (JJ): 날짜={row[0]:12s} | 종가={row[1]:8s} | 매매모드={row[2]:6s}")
                    
    except Exception as e:
        output.append(f"에러 발생: {e}")

    # 파일 쓰기
    result_path = os.path.join(project_root, "Debug", "mode_guide_result.txt")
    with open(result_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    print(f"결과가 파일에 저장되었습니다: {result_path}")

if __name__ == "__main__":
    main()
