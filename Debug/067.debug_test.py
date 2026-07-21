# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트 'SI_TQQQ' 탭의 별% 공식(R열 셀들)을 무한매수 V2.2 일반형(a분할) 공식에 맞게
=(10-K8/2*(40/E15))/100 수식으로 자동 업데이트합니다.
E15는 분할수(30), K8은 T값입니다.
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

def update_google_sheet_formulas():
    print("=== [Debug 067] 구글 시트 수식 자동 교정 테스트 시작 ===")
    
    if not os.path.exists(GOOGLE_KEY_PATH):
        print(f"❌ 에러: 구글 키 파일이 존재하지 않습니다: {GOOGLE_KEY_PATH}")
        return
        
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_KEY_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=creds)
    
    # 교정할 셀 위치와 일반형 공식 매핑
    # E15가 분할수(30), K8이 T값
    formula_to_write = "=(10-K8/2*(40/E15))/100"
    
    targets = {
        "R5": formula_to_write,
        "R8": formula_to_write,
        "R12": formula_to_write,
        "R14": formula_to_write,
        "R20": formula_to_write
    }
    
    try:
        # 서비스 계정 정보 출력 (사용자 권한 추가용)
        with open(GOOGLE_KEY_PATH, "r", encoding="utf-8") as f:
            key_data = json = eval(f.read())
            client_email = key_data.get("client_email")
            print(f"-> 사용 서비스 계정: {client_email}")
            print("-> (만약 쓰기 오류 발생 시, 위 이메일을 구글 시트에 '편집자'로 추가해 주셔야 합니다.)\n")

        for cell, formula in targets.items():
            print(f"-> {cell} 셀 수정 중: {formula}")
            body = {
                "values": [[formula]]
            }
            service.spreadsheets().values().update(
                spreadsheetId=SHEET_ID,
                range=f"'SI_TQQQ'!{cell}",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            print(f"   [성공] {cell} 셀 업데이트 완료.")
            
        print("\n=== [완료] 구글 시트 별% 공식 수식 교정 완료! ===")
        
    except Exception as e:
        print(f"\n❌ [오류 발생] 시트 수식 업데이트 실패: {e}")
        print("-> 권한 에러(403 Forbidden 등)가 난 경우, 구글 시트의 [공유] 버튼을 눌러")
        print(f"   '{client_email}' 서비스 계정 이메일에 [편집자] 권한을 추가해 주세요.")

if __name__ == "__main__":
    update_google_sheet_formulas()
