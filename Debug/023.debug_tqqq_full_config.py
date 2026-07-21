# -*- coding: utf-8 -*-
# 테스트 목적: 구글 시트 'SI_TQQQ' 탭의 설정 영역(A1:AH30)을 넓게 가져와서
# 무한매수 전략의 모든 설정 파라미터와 주문 생성 로직을 완전히 파악합니다.

import os
import sys

project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, project_root)

from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_KEY_PATH = os.path.join(project_root, "config", "google_key.json")
SHEET_ID = "1SMiFIa3FWIKmhlSytuHvSS6rA6_0wP6PSa8Nf8CSUrs"

def col_letter(idx):
    """0-based index -> column letter (A, B, ... Z, AA, AB ...)"""
    if idx < 26:
        return chr(65 + idx)
    return chr(64 + idx // 26) + chr(65 + idx % 26)

def main():
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)
        
        # A1:AH30 범위 넓게 조회
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="'SI_TQQQ'!A1:AH30"
        ).execute()
        
        rows = result.get("values", [])
        
        output = []
        output.append("=" * 160)
        output.append("구글 시트 'SI_TQQQ' 탭 전체 설정 영역 (A1:AH30)")
        output.append("=" * 160)
        
        for i, row in enumerate(rows):
            # 비어있는 행은 건너뛰기
            if not any(cell.strip() for cell in row if cell):
                output.append(f"Row {i+1:2d}: (빈 행)")
                continue
            parts = []
            for idx, val in enumerate(row):
                if val and str(val).strip():
                    parts.append(f"{col_letter(idx)}: {val}")
            if parts:
                output.append(f"Row {i+1:2d}: {' | '.join(parts)}")
            else:
                output.append(f"Row {i+1:2d}: (빈 행)")
        
        # 시트의 다른 탭 목록도 확인
        output.append("")
        output.append("=" * 80)
        output.append("시트 내 전체 탭 목록:")
        output.append("=" * 80)
        meta = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        for sheet in meta.get("sheets", []):
            props = sheet.get("properties", {})
            output.append(f"  - {props.get('title')} (gid: {props.get('sheetId')})")
                    
        result_path = os.path.join(project_root, "Debug", "tqqq_full_config.txt")
        with open(result_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output))
        print(f"SI_TQQQ 전체 설정 데이터가 저장되었습니다: {result_path}")
        
    except Exception as e:
        print(f"에러 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
