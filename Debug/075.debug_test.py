# -*- coding: utf-8 -*-
"""
테스트 목적:
SOXL의 yfinance 실시간/일봉 데이터 (df.tail(10)) 및 최신 종가를 출력하여
전일 종가가 몇 달러로 로드되고 있는지 정밀 검증합니다.
"""
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import yfinance as yf
from utils.market_data import MarketDataManager

def check_soxl_price():
    print("=== SOXL yfinance 일봉 데이터 조회 ===")
    df = yf.download("SOXL", period="1mo", progress=False)
    print("\n[최근 10일 일봉 데이터]")
    print(df.tail(10))
    
    mdm = MarketDataManager()
    close_val = mdm.get_latest_close("SOXL")
    print(f"\n-> MarketDataManager.get_latest_close('SOXL') 반환값: ${close_val}")

if __name__ == "__main__":
    check_soxl_price()
