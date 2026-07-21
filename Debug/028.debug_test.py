# -*- coding: utf-8 -*-
"""
테스트 목적: 구글 시트 'SI_TQQQ' 탭의 A1:AH30 범위에서 실제 수식(Formula)을 추출하여 별% 계산 및 주문 생성 공식의 구조적 정합성을 대조 분석합니다.
"""
import os
import sys

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from google.oauth2 import service_account
from googleapiclient.discovery import build

GOOGLE_KEY_PATH = os.path.join(project_root, "config", "google_key.json")
SHEET_ID = "1SMiFIa3FWIKmhlSytuHvSS6rA6_0wP6PSa8Nf8CSUrs"

def col_letter(idx):
    if idx < 26:
        return chr(65 + idx)
    return chr(64 + idx // 26) + chr(65 + idx % 26)

def main():
    try:
        if not os.path.exists(GOOGLE_KEY_PATH):
            print(f"구글 키 파일이 존재하지 않습니다: {GOOGLE_KEY_PATH}")
            return
            
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)
        
        # valueRenderOption="FORMULA"를 사용하여 수식 자체를 조회
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="'SI_TQQQ'!A1:AH30",
            valueRenderOption="FORMULA"
        ).execute()
        
        rows = result.get("values", [])
        
        output = []
        output.append("=" * 160)
        output.append("구글 시트 'SI_TQQQ' 탭 실제 수식(Formula) 분석 내역")
        output.append("=" * 160)
        
        for i, row in enumerate(rows):
            if not any(str(cell).strip() for cell in row if cell):
                continue
            parts = []
            for idx, val in enumerate(row):
                if val and str(val).strip():
                    parts.append(f"{col_letter(idx)}: {val}")
            if parts:
                output.append(f"Row {i+1:2d}: {' | '.join(parts)}")
                    
        result_path = os.path.join(project_root, "Debug", "tqqq_formulas.txt")
        with open(result_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output))
        print(f"SI_TQQQ 수식 추출 완료. 파일 저장 위치: {result_path}")
        
    except Exception as e:
        print(f"오류 발생: {e}")

if __name__ == "__main__":
    main()
