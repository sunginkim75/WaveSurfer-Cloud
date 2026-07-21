# -*- coding: utf-8 -*-
"""
테스트 목적: SURFER_BATCH 전략을 사용하는 태스크(task_4233ffb4)를 대상으로
BacktestAssembler.assemble_matching_table을 실행하여
다음 영업일 예정 주문 행이 올바르게 생성되고 에러 없이 리턴되는지 검증합니다.
"""
import os
import sys

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.backtest_assembler import BacktestAssembler
from utils.db_handler import DBHandler

def main():
    db = DBHandler()
    config = db.load_json("config/config.json")
    tasks = config.get("tasks", [])
    
    # 1. SURFER_BATCH 전략을 쓰는 태스크 검증
    task_config_ws = next((t for t in tasks if t.get("id") == "task_009a82ba"), None)
    if task_config_ws:
        print(f"\n태스크 {task_config_ws['id']} ({task_config_ws['nickname']}) 매칭 테이블 조립 시작...")
        try:
            report_ws = BacktestAssembler.assemble_matching_report(task_config_ws)
            rows = report_ws.get("detailedTxTable", [])
            print(f"조립 성공. 전체 행 수: {len(rows)}")
            
            if rows:
                print("\n--- 마지막 3개 행 데이터 ---")
                for r in rows[-3:]:
                    print(f"날짜: {r.get('date')} | 종가: {r.get('close')} | 모드: {r.get('mode')} | "
                          f"LOC매수목표(targetBuy): {r.get('targetBuy')} | 목표량(targetQty): {r.get('targetQty')} | "
                          f"실제매수량(buyQty): {r.get('buyQty')} | 실제매수금(buyAmt): {r.get('buyAmt')} | "
                          f"보유량(heldQty): {r.get('heldQty')} | 수익률(totalProfitRate): {r.get('totalProfitRate')}% | "
                          f"DD(drawdown): {r.get('drawdown')}% | 총자산: {r.get('totalAsset')}")
                
                last_row = rows[-1]
                next_date = BacktestAssembler.get_next_order_date()
                found_next_date = False
                for r in rows[-3:]:
                    if r.get("date") == next_date:
                        found_next_date = True
                        break
                
                if found_next_date or last_row.get("buyQty", "").endswith("(예정)") or last_row.get("sellDate") == "예정":
                    print(f"\n[성공] 다음 영업일 예정 행({next_date})이 포함되어 있습니다.")
                else:
                    print(f"\n[경고] 다음 영업일 예정 행({next_date})이 보이지 않습니다.")
            else:
                print("[실패] 반환된 행이 없습니다.")
        except Exception as e:
            import traceback
            print(f"[오류 발생]: {e}")
            traceback.print_exc()
            
    # 2. INFINITE_BUY 전략을 쓰는 태스크 검증
    task_config_ib = next((t for t in tasks if t.get("id") == "task_ce7c4efe"), None)
    if task_config_ib:
        print(f"\n태스크 {task_config_ib['id']} ({task_config_ib['nickname']}) 매칭 테이블 조립 시작...")
        try:
            report_ib = BacktestAssembler.assemble_matching_report(task_config_ib)
            rows = report_ib.get("detailedTxTable", [])
            print(f"조립 성공. 전체 행 수: {len(rows)}")
            
            if rows:
                print("\n--- 마지막 3개 행 데이터 ---")
                for r in rows[-3:]:
                    print(f"날짜: {r.get('date')} | 타입: {r.get('type')} | 가격: {r.get('price')} | "
                          f"수량: {r.get('qty')} | 금액: {r.get('amount')} | 누적원금: {r.get('total_cost')} | "
                          f"T값: {r.get('t_value')} | 총자산: {r.get('totalAsset')}")
            else:
                print("[실패] 반환된 행이 없습니다. (아직 거래 내역이 없을 수 있습니다)")
        except Exception as e:
            import traceback
            print(f"[오류 발생]: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    main()
