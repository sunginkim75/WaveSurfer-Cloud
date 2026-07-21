# -*- coding: utf-8 -*-
"""
테스트 목적:
사용자가 제공해 주신 실제 매매이력 구글 시트(Spreadsheet ID: 18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC6fw)의
gid=1019115050 탭 이름을 파악하고, 그 안의 데이터를 조회하여 어떤 구조로 매매 기록이
저장되어 있는지 분석합니다.
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
SHEET_ID = "18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC6fw"
TARGET_GID = 1019115050

def analyze_new_history_sheet():
    print("=== [Debug 070] 신규 제공 매매이력 시트 분석 시작 ===")
    
    if not os.path.exists(GOOGLE_KEY_PATH):
        print(f"❌ 에러: 구글 키 파일이 존재하지 않습니다: {GOOGLE_KEY_PATH}")
        return
        
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_KEY_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)
    
    try:
        # 1. 스프레드시트 메타데이터 조회하여 GID에 매핑되는 탭 명칭 획득
        spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        sheets = spreadsheet.get("sheets", [])
        
        target_tab_title = None
        for s in sheets:
            props = s.get("properties", {})
            gid = props.get("sheetId")
            title = props.get("title")
            if gid == TARGET_GID:
                target_tab_title = title
                break
                
        if not target_tab_title:
            # 못 찾은 경우 기본값 대입 또는 첫 번째 탭 시도
            print(f"-> GID {TARGET_GID}에 대응하는 탭을 찾지 못했습니다. 목록 중 매칭 시도.")
            if sheets:
                target_tab_title = sheets[0].get("properties", {}).get("title")
                print(f"   [우회] 첫 번째 탭 '{target_tab_title}'을 대상으로 조회합니다.")
            else:
                print("❌ 에러: 탭 목록이 비어 있습니다.")
                return
        else:
            print(f"-> GID {TARGET_GID} 에 대응하는 탭 이름 획득: '{target_tab_title}'")
            
        # 2. 해당 탭의 데이터 긁어오기 (A열 ~ Z열 범위)
        range_name = f"'{target_tab_title}'!A1:Z100"
        print(f"-> {range_name} 범위 데이터 요청 중...")
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=range_name
        ).execute()
        
        rows = result.get("values", [])
        print(f"-> 수집 완료: 총 {len(rows)} 행")
        
        # 덤프 파일 저장
        output_path = "Debug/070.sheet_rows_dump.txt"
        with open(output_path, "w", encoding="utf-8") as f:
            for idx, r in enumerate(rows):
                line = f"Row {idx + 1:2d}: " + " | ".join(f"{c_idx+1}({chr(65+c_idx)}): {val}" for c_idx, val in enumerate(r))
                f.write(line + "\n")
                if idx < 30: # 콘솔에는 상위 30행만 출력
                    print(line)
                    
        print(f"\n=== [성공] 전체 {len(rows)}개 행 데이터가 '{output_path}'에 덤프되었습니다. ===")
        
    except Exception as e:
        print(f"❌ 구글 시트 조회 실패: {e}")
        print("-> 403 Permission Denied 에러 발생 시, 이 시트의 공유 권한에 서비스 계정 이메일을 추가해야 합니다.")
        # 서비스 계정 이메일 출력
        try:
            with open(GOOGLE_KEY_PATH, "r", encoding="utf-8") as key_f:
                key_data = json.load(key_f)
                print(f"-> 공유 대상 서비스 계정: {key_data.get('client_email')}")
        except:
            pass

if __name__ == "__main__":
    analyze_new_history_sheet()
