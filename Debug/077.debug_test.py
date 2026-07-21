# -*- coding: utf-8 -*-
"""
테스트 목적:
BacktestAssembler.assemble_matching_table 함수를 실행하여,
투자 이력 그리드 테이블 맨 아래에 덧붙여지는 예약 행의 날짜가
한국 시간 새벽 01시 기준 7/22가 아닌 현재 미국 장 날짜인 '2026-07-21'로 정확히 생성되는지 자가 검증합니다.
"""
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_handler import DBHandler
from core.backtest_assembler import BacktestAssembler

def test_matching_table():
    print("=== BacktestAssembler 매매 대조표 날짜 검증 ===")
    db = DBHandler()
    config = db.load_json("config/config.json")
    task_config = config["tasks"][0] # SI_MOCK
    
    rows = BacktestAssembler.assemble_matching_table(task_config)
    print(f"-> 반환된 총 대조표 행 수: {len(rows)}개")
    if rows:
        last_row = rows[-1]
        print("\n[마지막 행(예측 행) 정보]:")
        print(f" - Date: {last_row.get('date')}")
        print(f" - targetBuy: {last_row.get('targetBuy')}")
        print(f" - targetQty: {last_row.get('targetQty')}")

if __name__ == "__main__":
    test_matching_table()
