# -*- coding: utf-8 -*-
"""
테스트 목적:
새로 만들어진 SI_MOCK (task_c8c12734)의 매매 대조표 API 응답을 조회하여,
7/13일 이전의 날짜 행들이 대조표 리스트에서 완전히 제외되었는지,
그리고 7/13일 예약 주문 행에 주문 목표량 등이 올바르게 표시되는지 덤프하여 검증합니다.
"""
import urllib.request, json, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# API 호출
req = urllib.request.Request("http://localhost:8000/api/v1/tasks/task_c8c12734/matching")
try:
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())

    print("=== [SI_MOCK 매칭 테이블 덤프] ===")
    tx_table = result.get('detailedTxTable', [])
    print(f"총 행 수: {len(tx_table)}")
    for r in tx_table:
        print(f"날짜: {r.get('date')} | 종가: {r.get('close')} | 매매모드: {r.get('mode')} | 매수예정: {r.get('buyLimitAmt'):>10.2f} | LOC목표가: {r.get('targetBuy')} | 목표수량: {r.get('targetQty')} | 예수금: {r.get('cash'):>10.2f} | 총자산: {r.get('totalAsset'):>10.2f}")

except Exception as e:
    print(f"에러 발생: {e}")
