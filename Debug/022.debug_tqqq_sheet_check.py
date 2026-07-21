# -*- coding: utf-8 -*-
# 테스트 목적: 구글 시트 'SI_TQQQ' 탭의 상단 헤더와 첫 20행 데이터를 가져와서
# 무한매수 전략의 고유 컬럼과 동작 방식을 확인합니다.

import os
import sys

# 프로젝트 루트 경로 설정
project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, project_root)

from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_KEY_PATH = os.path.join(project_root, "config", "google_key.json")
# 유저가 알려준 새로운 시트 ID
SHEET_ID = "1SMiFIa3FWIKmhlSytuHvSS6rA6_0wP6PSa8Nf8CSUrs"

def main():
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)
        
        # 1행부터 30행까지, A열부터 Z열까지 넓게 조회
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="'SI_TQQQ'!A1:Z30"
        ).execute()
        
        rows = result.get("values", [])
        
        output = []
        output.append("=" * 140)
        output.append("구글 시트 'SI_TQQQ' 탭 데이터 (A열 ~ Z열)")
        output.append("=" * 140)
        
        for i, row in enumerate(rows):
            cols = [row[idx] if idx < len(row) else "" for idx in range(len(row))]
            col_str = " | ".join(f"{idx+1}({chr(65+idx) if idx < 26 else 'A'+chr(65+idx-26)}): {val}" for idx, val in enumerate(cols))
            output.append(f"Row {i+1:2d}: {col_str}")
            
        result_path = os.path.join(project_root, "Debug", "tqqq_sheet_rows.txt")
        with open(result_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output))
        print(f"SI_TQQQ 시트 데이터가 저장되었습니다: {result_path}")
        
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    main()
