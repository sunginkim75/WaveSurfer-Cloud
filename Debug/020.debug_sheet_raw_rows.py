# -*- coding: utf-8 -*-
# 테스트 목적: 구글 시트 'JJ' 탭의 실제 행 데이터(J열 ~ AC열)를 로드하여 
# 매수/매도 매칭 레이아웃과 MOC 매도일의 기록 양식을 원본 그대로 파악합니다.

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
        
        # 최신 거래 내역이 위치한 2026-07-01 전후 행 읽기
        # J10:AC50 범위 조회 (2026년 6~7월 거래구간 포함)
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="'JJ'!J1:AC45"
        ).execute()
        
        rows = result.get("values", [])
        
        output = []
        output.append("=" * 120)
        output.append("구글 시트 'JJ' 탭 원본 행 데이터 (J열 ~ AC열)")
        output.append("=" * 120)
        
        # 헤더 출력
        if len(rows) > 8:
            header_row = rows[8] # 9행이 헤더
            output.append("Col Index: " + " | ".join(f"{chr(74 + idx)}:{val}" for idx, val in enumerate(header_row)))
            output.append("-" * 120)
            
        for i, row in enumerate(rows):
            # 6월 1일 이후 행 필터링 및 출력
            if i >= 9: # 10행부터 데이터
                # 패딩을 채워 20개 컬럼 맞춤
                cols = [row[idx] if idx < len(row) else "" for idx in range(20)]
                # 날짜가 비어있지 않은 경우 출력
                if cols[0]:
                    col_str = " | ".join(f"{chr(74 + idx)}: {cols[idx]}" for idx in range(20))
                    output.append(f"Row {i+1:3d}: {col_str}")
                    
        result_path = os.path.join(project_root, "Debug", "raw_sheet_rows.txt")
        with open(result_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output))
        print(f"원본 데이터가 파일에 저장되었습니다: {result_path}")
        
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    main()
