# -*- coding: utf-8 -*-
# 테스트 목적: 구글 시트의 'QQQRSI' 탭(gid=1808479922)에서 데이터를 읽어와 구조 분석 및 RSI 계산 방식 파악

import os
import sys

# 프로젝트 루트 경로 설정
project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, project_root)

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    print("google-auth 패키지 설치 중...")
    os.system(f"{sys.executable} -m pip install google-auth google-auth-httplib2 google-api-python-client -q")
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

GOOGLE_KEY_PATH = os.path.join(project_root, "config", "google_key.json")
SHEET_ID = "18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC6fw"

def main():
    print("=" * 70)
    print("구글 시트 QQQRSI 데이터 로드 및 분석")
    print("=" * 70)
    
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)
        
        # QQQRSI 탭 데이터 읽기 (수식 포함하여 넉넉하게 200행까지)
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="'QQQRSI'!A1:Z200",
            valueRenderOption="FORMULA"
        ).execute()
        
        rows = result.get("values", [])
        print(f"QQQRSI 시트 총 {len(rows)}개 행 읽음\n")
        
        for i, row in enumerate(rows[:60]):  # 상위 60행만 우선 출력하여 구조 파악
            # 비어있는 컬럼들을 가독성을 위해 간략화
            non_empty_indices = [idx for idx, val in enumerate(row) if val is not None and str(val).strip()]
            if non_empty_indices:
                max_idx = max(non_empty_indices)
                display_row = row[:max_idx + 1]
                print(f"Row {i+1:3d}: {display_row}")
            else:
                print(f"Row {i+1:3d}: [Empty Row]")
                
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    main()
