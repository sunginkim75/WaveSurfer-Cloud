# -*- coding: utf-8 -*-
# 테스트 목적: 구글 시트 'JJ' 탭의 AD열 ~ AH열 부근의 추가 자금 / 자금 갱신 데이터와 헤더를 로드하여
# 추가 자금 추가가 어떤 식으로 연동되고 있는지 분석합니다.

import os
import sys

# 프로젝트 루트 경로 설정
project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, project_root)

from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_KEY_PATH = os.path.join(project_root, "config", "google_key.json")
SHEET_ID = "18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC6fw"

def main():
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)
        
        # J1:AJ15 범위 조회 (헤더 및 데이터 15행)
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="'JJ'!J1:AJ20"
        ).execute()
        
        rows = result.get("values", [])
        
        output = []
        output.append("=" * 140)
        output.append("구글 시트 'JJ' 탭 확장 데이터 (J열 ~ AJ열)")
        output.append("=" * 140)
        
        # 헤더 출력 (9행)
        if len(rows) > 8:
            header_row = rows[8]
            output.append("Col Headers: " + " | ".join(f"{idx+10}:{val}" for idx, val in enumerate(header_row)))
            output.append("-" * 140)
            
        for i, row in enumerate(rows):
            if i >= 9: # 10행부터 데이터
                cols = [row[idx] if idx < len(row) else "" for idx in range(27)] # J ~ AJ는 총 27개 열
                if cols[0]:
                    col_str = " | ".join(f"{idx+10}: {cols[idx]}" for idx in range(len(cols)))
                    output.append(f"Row {i+1:3d}: {col_str}")
                    
        result_path = os.path.join(project_root, "Debug", "more_sheet_cols.txt")
        with open(result_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output))
        print(f"상세 데이터가 파일에 저장되었습니다: {result_path}")
        
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    main()
