# -*- coding: utf-8 -*-
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_handler import DBHandler
from core.backtest_assembler import BacktestAssembler

def test_unclosed_row_fields():
    db = DBHandler()
    config = db.load_json("config/config.json")
    task_config = config["tasks"][0] # SI_MOCK
    
    rows = BacktestAssembler.assemble_matching_table(task_config)
    last_row = rows[-1]
    print("=== [7/21 미완성 장중 행 검증] ===")
    print(f" - Date: {last_row.get('date')}")
    print(f" - Close: {last_row.get('close')}")
    print(f" - Cash: '{last_row.get('cash')}'")
    print(f" - HeldQty: '{last_row.get('heldQty')}'")
    print(f" - EvalAmt: '{last_row.get('evalAmt')}'")
    print(f" - TotalAsset: '{last_row.get('totalAsset')}'")
    print(f" - TotalProfitRate: '{last_row.get('totalProfitRate')}'")

if __name__ == "__main__":
    test_unclosed_row_fields()
