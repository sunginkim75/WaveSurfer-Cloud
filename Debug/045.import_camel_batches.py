# -*- coding: utf-8 -*-
"""
테스트 목적:
로컬 trade_batches JSON DB에 카멜케이스(buyDate, buyQty, buyPrice) 리스트 스펙으로
7월 활성 배치 2개(총 91주, 평단 $186.68)를 정확히 이식하여 API 500 에러를 해결합니다.
"""
import json
import os

batch_db_path = r"C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\config\trade_batches_task_009a82ba.json"

# 올바른 카멜케이스 리스트 스펙
active_batches = [
    {
        "batchId": "bt_260701_1",
        "buyDate": "2026-07-01",
        "buyQty": 37,
        "buyPrice": 217.55,
        "isSafe": True,
        "isActive": True
    },
    {
        "batchId": "bt_260710_2",
        "buyDate": "2026-07-10",
        "buyQty": 54,
        "buyPrice": 165.54,
        "isSafe": False,
        "isActive": True
    }
]

os.makedirs(os.path.dirname(batch_db_path), exist_ok=True)

# 딕셔너리로 감싸지 않고 바로 리스트 형태로 저장
with open(batch_db_path, "w", encoding="utf-8") as f:
    json.dump(active_batches, f, indent=4, ensure_ascii=False)

print("[OK] 카멜케이스 리스트 형태로 7월 활성 배치 2개 이식 완료!")
