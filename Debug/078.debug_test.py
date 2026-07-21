# -*- coding: utf-8 -*-
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_handler import DBHandler
from core.backtest_assembler import BacktestAssembler

def test_simulated_matching():
    print("=== [Debug 078] 가상 체결 백테스팅 대조표 검증 ===")
    db = DBHandler()
    config = db.load_json("config/config.json")
    task_config = config["tasks"][0] # SI_MOCK (created_at: 2026-07-13)
    
    rows = BacktestAssembler.assemble_matching_table(task_config)
    print(f"-> 반환된 총 대조표 행 수: {len(rows)}개")
    for r in rows:
        c_str = f"${r.get('close'):.2f}" if isinstance(r.get('close'), (int, float)) else "-"
        tb_str = f"${r.get('targetBuy'):.2f}" if isinstance(r.get('targetBuy'), (int, float)) else "-"
        bp_str = f"${r.get('buyPrice'):.2f}" if isinstance(r.get('buyPrice'), (int, float)) else "-"
        sp_str = f"${r.get('sellPrice'):.2f}" if isinstance(r.get('sellPrice'), (int, float)) else "-"
        
        print(f"[{r.get('date')}] 종가: {c_str} | 모드: {r.get('mode')} | 목표매수가: {tb_str} | 매수단가: {bp_str} ({r.get('buyQty')}주) | 매도단가: {sp_str} ({r.get('sellQty')})")

if __name__ == "__main__":
    test_simulated_matching()
