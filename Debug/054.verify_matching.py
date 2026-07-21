# -*- coding: utf-8 -*-
"""
테스트 목적:
수정 후 매칭 API에서 특정 날짜의 buyPrice, buyQty, sellPrice, realized 값이 정확한지 검증합니다.
"""
import urllib.request, json, time

time.sleep(5)

req = urllib.request.Request(
    "http://localhost:8000/api/v1/tasks/task_009a82ba/matching",
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req) as r:
    result = json.loads(r.read())

rows = result.get("detailedTxTable", [])
print(f"총 {len(rows)}행")

# 매수가/매수수량이 있는 행만 출력
print("\n=== 매수가/수량이 있는 행 ===")
for row in rows:
    bp = row.get("buyPrice")
    bq = row.get("buyQty")
    if bp and bp != "" and bq and bq != "":
        sp = row.get("sellPrice", "-")
        sd = row.get("sellDate", "")
        realized = row.get("realized", "-")
        print(f"  {row['date']} 매수={bp}@{bq} 매도일={sd} 매도가={sp} 실현={realized}")
