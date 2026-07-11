import os
import sys
import json
import datetime
# Path 조정을 통해 utils와 core 모듈 임포트 가능하도록 설정
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.db_handler import DBHandler
from utils.market_data import MarketDataManager
from core.strategies.strategy_factory import StrategyFactory
# 강제 임포트하여 팩토리에 등록되도록 함
from core.strategies.surfer_batch import SurferBatchStrategy

def main():
    print("=== DBHandler Test ===")
    db = DBHandler()
    test_file = "config/test_data.json"
    db.save_json(test_file, {"status": "ok", "value": 123})
    data = db.load_json(test_file)
    print(f"Loaded Data: {data}")
    # Update and test .bak creation
    db.save_json(test_file, {"status": "updated", "value": 456})
    print(f"Is .bak created? {os.path.exists(test_file + '.bak')}")

    print("\n=== MarketDataManager Test ===")
    md = MarketDataManager()
    # SOXL 종가 테스트 (yfinance 연동 검증)
    close_price = md.get_latest_close("SOXL")
    print(f"SOXL Latest Close: {close_price}")
    # QQQ RSI 테스트
    qqq_rsi = md.get_rsi("QQQ")
    print(f"QQQ RSI: {qqq_rsi}")

    print("\n=== SurferBatchStrategy Test ===")
    task_config = {
        "id": "test_1",
        "strategy": "SURFER_BATCH",
        "ticker": "SOXL",
        "rsi_ticker": "QQQ",
        "safe_buy_pct": 2.5,
        "safe_sell_pct": 0.5,
        "agg_buy_pct": 4.0,
        "agg_sell_pct": 2.0,
        "split_count": 7,
        "seed_amt": 10000
    }
    
    # 팩토리에서 전략 불러오기
    strategy = StrategyFactory.get_strategy(task_config)
    print(f"Loaded strategy: {type(strategy).__name__}")
    
    # 임의로 체결 1건 발생시켜서 배치 생성
    print("Simulating BUY contract...")
    strategy.on_trade_contracted({
        "type": "BUY",
        "qty": 5,
        "price": close_price if close_price else 20.0,
        "mode": "공세모드",
        "date": "2026-07-09" # 어제 날짜로 세팅하여 LOC 매도 계산에 포함되게 함
    })
    
    # LOC/MOC 계산
    print("Calculating orders...")
    orders = strategy.calculate_orders()
    for order in orders:
        print(order)

if __name__ == "__main__":
    main()
