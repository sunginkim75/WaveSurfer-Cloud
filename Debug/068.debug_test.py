# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트 '1SMiFIa3FWIKmhlSytuHvSS6rA6_0wP6PSa8Nf8CSUrs'의 전체 탭(Sheet) 목록을 조회하여
과거 무한매수(TQQQ) 매매 이력이 들어있는 데이터 원천이 어디인지 찾습니다.
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

def inspect_sheet_tabs():
    print("=== [Debug 068] 구글 시트 탭 목록 조회 시작 ===")
    
    if not os.path.exists(GOOGLE_KEY_PATH):
        print(f"❌ 에러: 구글 키 파일이 존재하지 않습니다: {GOOGLE_KEY_PATH}")
        return
        
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_KEY_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)
    
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        sheets = spreadsheet.get("sheets", [])
        
        print(f"\n총 탭 수: {len(sheets)}")
        for idx, sheet in enumerate(sheets):
            title = sheet.get("properties", {}).get("title")
            grid_props = sheet.get("properties", {}).get("gridProperties", {})
            rows = grid_props.get("rowCount", 0)
            cols = grid_props.get("columnCount", 0)
            print(f"[{idx + 1}] 탭 이름: {title:<25} | 행 수: {rows:<5} | 열 수: {cols}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    inspect_sheet_tabs()
