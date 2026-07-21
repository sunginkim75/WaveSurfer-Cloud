# -*- coding: utf-8 -*-
"""
테스트 목적:
현재 실행 중인 모든 활성 태스크들의 당일 원본 주문 목록(Original Orders)과
수동 퉁치기 엔진을 거친 HTS 최종 전송 주문 목록(Netted Orders)을
콘솔에 전부 출력하여, 새로 생성한 배치/태스크가 퉁치기 제외 및 정상 작동하는지 교차 검증합니다.
"""
import os
import sys
import datetime

# 프로젝트 루트 경로 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from utils.db_handler import DBHandler
from core.strategies.surfer_batch import SurferBatchStrategy
from core.strategies.netting_handler import process_and_save_netted_orders
from utils.market_data import MarketDataManager

def verify_all_tasks_netted_orders():
    print("=== [Debug 073] 모든 Task 당일 퉁치기 주문 대조 검증 스크립트 ===")
    
    db = DBHandler()
    config = db.load_json("config/config.json")
    mdm = MarketDataManager()
    
    tasks = [t for t in config.get("tasks", []) if t.get("is_active", True)]
    print(f"-> 활성화된 총 태스크 수: {len(tasks)}개")
    
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    for task in tasks:
        task_id = task["id"]
        ticker = task["ticker"]
        strategy_name = task.get("strategy", "SURFER_BATCH")
        print(f"\n==================================================")
        print(f"▶ 태스크: {task.get('nickname', task_id)} ({ticker} / {strategy_name})")
        print(f"   작동모드: {task.get('operation_mode')} | 생성일: {task.get('created_at')}")
        
        if strategy_name != "SURFER_BATCH":
            print("   (WAVE SURFER 전략이 아니므로 수동 퉁치기 검증을 건너뜁니다.)")
            continue
            
        strategy = SurferBatchStrategy(task)
        close_val = mdm.get_latest_close(ticker)
        rsi_vals = mdm.get_weekly_rsi_data(task.get("rsi_ticker", "QQQ"))
        
        print(f"   {ticker} 현재가: ${close_val:.2f}")
        if rsi_vals:
            print(f"   QQQ RSI: 2주전 {rsi_vals[0]:.2f}, 1주전 {rsi_vals[1]:.2f}")
            
        batches = db.load_json(f"config/trade_batches_{task_id}.json", default_data=[])
        print(f"   보유 배치 목록 ({len(batches)}개):")
        for b in batches:
            print(f"     - ID: {b.get('id')} | buyDate: {b.get('buyDate')} | buyPrice: ${b.get('buyPrice')} | qty: {b.get('qty')}주 | cycleDays: {b.get('cycleDays')}")
            
        # 1차 원본 주문 도출
        original_orders = []
        current_mode = task.get("last_mode", "안전모드")
        
        if rsi_vals:
            prev_rsi, latest_rsi, _ = rsi_vals
            is_safe = (prev_rsi > 65 and prev_rsi > latest_rsi) or (40 < prev_rsi < 50 and prev_rsi > latest_rsi) or (latest_rsi < 50 and prev_rsi > 50)
            is_agg = (prev_rsi < 35 and prev_rsi < latest_rsi) or (50 < prev_rsi < 60 and prev_rsi < latest_rsi) or (latest_rsi > 50 and prev_rsi < 50)
            if is_safe: current_mode = "안전모드"
            elif is_agg: current_mode = "공세모드"
            
        # 매도 원본 계산 (cycleDays <= 0 가드 적용 상태)
        for idx, batch in enumerate(batches):
            buy_price = batch.get("buyPrice", 0)
            qty = batch.get("qty", 0)
            cycle_days = batch.get("cycleDays", 0)
            batch_mode = batch.get("buyMode", "안전모드")
            buy_date = batch.get("buyDate", "")
            
            # 당일 매수 배치 제외 가드
            if cycle_days <= 0 or buy_date == today_str:
                print(f"     ⚠️ 배치 {batch.get('id')}는 오늘 생성/매수된 건이므로 매도 주문에서 제외됩니다.")
                continue
                
            limit_days = 7 if batch_mode == "공세모드" else 30
            if cycle_days >= limit_days:
                original_orders.append({
                    "action": "SELL", "order_type": "MOC", "qty": qty, "price": 0.01,
                    "batch_id": batch.get("id"), "reason": "MOC 청산", "tier": idx + 1
                })
            else:
                pct = strategy.agg_sell_pct if batch_mode == "공세모드" else strategy.safe_sell_pct
                target_sell = buy_price * (1 + (pct / 100))
                original_orders.append({
                    "action": "SELL", "order_type": "LOC", "qty": qty, "price": round(target_sell, 2),
                    "batch_id": batch.get("id"), "reason": f"LOC 매도대기 (목표가 {target_sell:.2f})", "tier": idx + 1
                })
                
        # 매수 원본 계산
        buy_pct = strategy.agg_buy_pct if current_mode == "공세모드" else strategy.safe_buy_pct
        target_buy = close_val * (1 + (buy_pct / 100))
        buy_limit_amt = strategy.last_compounding_cash / strategy.split_count
        buy_qty = int(buy_limit_amt // target_buy)
        if buy_qty > 0:
            original_orders.append({
                "action": "BUY", "order_type": "LOC", "qty": buy_qty, "price": round(target_buy, 2),
                "reason": f"LOC 신규매수", "mode": current_mode, "tier": 0
            })
            
        print("\n   --- [1단계] 퉁치기 전 원본 주문 목록 ---")
        for idx, o in enumerate(original_orders):
            print(f"     [{idx+1}] {o['action']} | {o['order_type']} | {o['qty']}주 | ${o['price']} (티어: {o['tier']})")
            
        # 퉁치기 수행
        hts_orders = process_and_save_netted_orders(ticker, task_id, original_orders, today_str)
        
        print("\n   --- [2단계] HTS 최종 주문 목록 (퉁치기 압축) ---")
        if not hts_orders:
            print("     (상쇄되어 전송할 주문 없음)")
        for idx, o in enumerate(hts_orders):
            type_str = "MOC" if o["order_type"] == "34" else "LOC"
            print(f"     [{idx+1}] {o['action']} | {type_str} | {o['qty']}주 | ${o['price']}")
            
    print("\n==================================================")

if __name__ == "__main__":
    verify_all_tasks_netted_orders()
