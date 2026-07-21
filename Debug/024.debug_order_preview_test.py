# -*- coding: utf-8 -*-
"""
테스트 목적: 무한매수 V2.2 1회차 주문 생성 여부 및 yfinance TQQQ 데이터 수집 테스트
"""
import sys
import os
import json

# 프로젝트 루트 디렉토리를 path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.market_data import MarketDataManager
from core.strategies.infinite_buy import InfiniteBuyStrategy
from utils.db_handler import DBHandler

def main():
    print("=== TQQQ 종가 테스트 ===")
    md = MarketDataManager()
    close_price = md.get_latest_close("TQQQ")
    print(f"TQQQ 최신 종가: {close_price}")

    # 가상 태스크 생성
    task_config = {
        "id": "task_ce7c4efe",
        "account_no": "123415678",
        "nickname": "SI_TQQQ",
        "strategy": "INFINITE_BUY",
        "ticker": "TQQQ",
        "rsi_ticker": "QQQ",
        "seed_amt": 10000,
        "split_count": 40,
        "losscut_mode": True,
        "ib_limit_sell_pct": 10,
        "ib_loc_buy_pct": 0,
        "ib_losscut_pct": -10,
        "is_active": True
    }

    # batches 강제 초기화 (T값 = 0.0)
    db = DBHandler()
    batches_file = f"config/trade_batches_task_ce7c4efe.json"
    if os.path.exists(batches_file):
        os.remove(batches_file)
    print("batches_file 초기화 완료 (T값 = 0.0)")

    strategy = InfiniteBuyStrategy(task_config)
    orders = strategy.calculate_orders()
    
    print("\n=== 생성된 주문 ===")
    print(json.dumps(orders, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()
