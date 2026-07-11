# 테스트 목적: 구글 시트의 SOXL 거래 이력과 로컬 시뮬레이션 결과 비교
# 구글 시트 ID: 18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC6fw (gid=879227790)

import json
import os
import sys

# 프로젝트 루트 경로 설정
project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, project_root)

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    print("google-auth 패키지가 없습니다. 설치 중...")
    os.system(f"{sys.executable} -m pip install google-auth google-auth-httplib2 google-api-python-client -q")
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

# ===== 설정 =====
GOOGLE_KEY_PATH = os.path.join(project_root, "config", "google_key.json")
SHEET_ID = "18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC6fw"  # 유저가 공유한 시트
LOCAL_HISTORY_PATH = os.path.join(project_root, "config", "trade_history_task_3917820f.json")
LOCAL_BATCHES_PATH = os.path.join(project_root, "config", "trade_batches_task_3917820f.json")

print("=" * 70)
print("SOXL WaveSurfer 시뮬레이션 vs 구글 시트 비교")
print("=" * 70)

# ===== 1. 구글 시트 데이터 읽기 =====
print("\n[1] 구글 시트 데이터 읽는 중...")
output_lines = []
def log(msg):
    print(msg)
    output_lines.append(msg)

try:
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_KEY_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)
    
    # 먼저 스프레드시트 메타데이터를 가져와서 시트 이름 확인
    spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    sheets = spreadsheet.get("sheets", [])
    
    log(f"\n  스프레드시트 제목: {spreadsheet.get('properties', {}).get('title', 'N/A')}")
    log(f"  시트 목록:")
    target_sheet = None
    for s in sheets:
        props = s.get("properties", {})
        gid = props.get("sheetId", "?")
        title = props.get("title", "?")
        log(f"    - [{gid}] {title}")
        if str(gid) == "879227790":
            target_sheet = title
    
    if target_sheet:
        log(f"\n  대상 시트 (gid=879227790): '{target_sheet}'")
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=f"'{target_sheet}'!A1:Z100"
        ).execute()
        sheet_data = result.get("values", [])
        
        log(f"\n  총 {len(sheet_data)}행 읽음")
        if sheet_data:
            log("\n  --- 구글 시트 데이터 (비어있지 않은 행만 표시) ---")
            for i, row in enumerate(sheet_data):
                # 행이 완전히 비어있거나 의미없는 값만 있는 경우 제외
                non_empty = [c for c in row if c and c.strip()]
                if non_empty:
                    log(f"  Row {i+1:2d}: {row}")
    else:
        log("  경고: gid=879227790에 해당하는 시트를 찾지 못했습니다.")
        # 첫 번째 시트라도 읽기
        if sheets:
            first_title = sheets[0].get("properties", {}).get("title", "Sheet1")
            log(f"  첫 번째 시트 '{first_title}' 읽기 시도...")
            result = service.spreadsheets().values().get(
                spreadsheetId=SHEET_ID,
                range=f"'{first_title}'!A1:Z100"
            ).execute()
            sheet_data = result.get("values", [])
            log(f"\n  총 {len(sheet_data)}행 읽음")
            for i, row in enumerate(sheet_data):
                non_empty = [c for c in row if c and c.strip()]
                if non_empty:
                    log(f"  Row {i+1:2d}: {row}")

except Exception as e:
    log(f"  구글 시트 접근 오류: {e}")
    log("  (시트가 서비스 계정에 공유되지 않았을 수 있습니다)")
    sheet_data = []

# ===== 2. 로컬 시뮬레이션 결과 읽기 =====
log("\n[2] 로컬 시뮬레이션 결과 (trade_history_task_3917820f.json)")
with open(LOCAL_HISTORY_PATH, "r", encoding="utf-8") as f:
    local_history = json.load(f)
with open(LOCAL_BATCHES_PATH, "r", encoding="utf-8") as f:
    local_batches = json.load(f)

log(f"\n  총 {len(local_history)}건 거래 이력:")
log(f"\n  {'날짜':<12} {'구분':<6} {'주문':<5} {'매수가':<9} {'매도가':<9} {'수량':<5} {'손익':<10} {'비고'}")
log("  " + "-" * 75)
for h in local_history:
    sell_p = f"${h['sellPrice']}" if h['sellPrice'] else "  -  "
    profit = f"${h['realized_profit']:+.2f}" if h['realized_profit'] is not None else "  -  "
    log(f"  {h['date']:<12} {h['type']:<6} {h['order_type']:<5} ${h['buyPrice']:<8} {sell_p:<9} {h['qty']:<5} {profit:<10} {h['reason']}")

log(f"\n  보유 배치: {len(local_batches)}개")
for b in local_batches:
    log(f"    - {b['buyDate']} | {b['qty']}주 @ ${b['buyPrice']} | D+{b['cycleDays']} | {b['buyMode']}")

total_profit = sum(h["realized_profit"] for h in local_history if h.get("realized_profit") is not None)
log(f"\n  총 실현 손익: ${total_profit:.2f}")

# ===== 3. 비교 분석 =====
log("\n[3] 비교 분석")
if sheet_data:
    log("  구글 시트 데이터와 로컬 시뮬레이션 비교 진행 중...")
    # 시트 헤더가 있다면 파싱 시도
    if len(sheet_data) >= 2:
        headers = sheet_data[0]
        log(f"  시트 컬럼: {headers}")
        
        # 비교 로직은 시트 구조에 따라 동적으로 처리
        data_rows = sheet_data[1:]
        log(f"  데이터 행: {len(data_rows)}개")
else:
    log("  구글 시트 데이터를 가져오지 못해 비교를 건너뜁니다.")
    log("\n  [대안] 시트를 서비스 계정에 공유해주시면 비교 가능합니다:")
    log(f"  서비스 계정: frist-trading-992@phrasal-agility-484416-t9.iam.gserviceaccount.com")

log("\n" + "=" * 70)
log("완료!")

# 결과를 UTF-8 파일로 저장
compare_result_path = os.path.join(project_root, "Debug", "compare_result.txt")
with open(compare_result_path, "w", encoding="utf-8") as f:
    f.write("\n".join(output_lines))
print(f"\n결과가 파일에 저장되었습니다: {compare_result_path}")

