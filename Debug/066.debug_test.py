# -*- coding: utf-8 -*-
"""
테스트 목적:
무한매수 태스크인 SI_TQQQ (task_ce7c4efe)의 매매 대조표 API 응답을 조회하여,
7/12일 거래일자 행에 거래 구분 BUY가 왜 나오는지 그 원인을 파악하기 위해 덤프합니다.
"""
import urllib.request
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

req = urllib.request.Request("http://localhost:8000/api/v1/tasks/task_ce7c4efe/matching")
try:
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())

    print("=== [SI_TQQQ 매칭 테이블 덤프] ===")
    tx_table = result.get('detailedTxTable', [])
    print(f"총 행 수: {len(tx_table)}")
    for r in tx_table[-10:]: # 최근 10행만 출력
        print(f"날짜: {r.get('date')} | 종가: {r.get('close')} | 매매모드: {r.get('mode')} | 거래구분: {r.get('tradeType')} | 매수예정: {r.get('buyLimitAmt')} | LOC목표가: {r.get('targetBuy')} | 목표수량: {r.get('targetQty')} | 예수금: {r.get('cash')} | 총자산: {r.get('totalAsset')}")

except Exception as e:
    print(f"에러 발생: {e}")
