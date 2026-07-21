# -*- coding: utf-8 -*-
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_handler import DBHandler
from core.backtest_assembler import BacktestAssembler

def test_summary():
    db = DBHandler()
    config = db.load_json("config/config.json")
    task_config = config["tasks"][0] # SI_MOCK
    
    report = BacktestAssembler.assemble_matching_report(task_config)
    summary = report["summary"]
    print("=== [Summary 검증] ===")
    print(f" - realizedProfitVal (누적 실현손익): ${summary.get('realizedProfitVal'):.2f}")
    print(f" - realizedProfitRate (누적 실현수익률): {summary.get('realizedProfitRate'):.2f}%")
    print(f" - totalReturn (총자산 수익률): {summary.get('totalReturn'):.2f}%")

if __name__ == "__main__":
    test_summary()
