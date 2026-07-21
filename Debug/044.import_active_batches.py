# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트의 복리 다중 배치 상태를 안전하게 로컬 JSON DB로 마이그레이션(이식)합니다.
실제 키움 계좌 원장(91주 @ $186.68)과 구글 시트 날짜별 진입 수량을 기반으로 역산하여,
[37주 @ $217.55] 및 [54주 @ $165.54] 의 2개 다중 배치로 구성하여 주입합니다.
"""
import json
import os

batch_db_path = r"C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\config\trade_batches_task_009a82ba.json"

# 주입할 실제 구글 시트 기반 7월 활성 배치 리스트
active_batches = [
    {
        "batch_id": "bt_260701_1",
        "buy_date": "2026-07-01",
        "buy_qty": 37,
        "buy_price": 217.55,
        "is_safe": True,
        "is_active": True
    },
    {
        "batch_id": "bt_260710_2",
        "buy_date": "2026-07-10",
        "buy_qty": 54,
        "buy_price": 165.54,
        "is_safe": False,
        "is_active": True
    }
]

# JSON DB에 기입
db_data = {
    "task_id": "task_009a82ba",
    "batches": active_batches
}

os.makedirs(os.path.dirname(batch_db_path), exist_ok=True)

with open(batch_db_path, "w", encoding="utf-8") as f:
    json.dump(db_data, f, indent=4, ensure_ascii=False)

print("[OK] 구글 시트 기반 활성 배치 2개 (총 91주, 평단 $186.68) 로컬 JSON DB 이식 완료!")
