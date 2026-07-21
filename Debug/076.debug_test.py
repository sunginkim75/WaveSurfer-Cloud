# -*- coding: utf-8 -*-
"""
테스트 목적:
미국 동부시간(NY) 기준 현재 장중 여부를 판별하여,
미완성 장중 데이터를 제외하고 100% 마감 완료된 최신 영업일 종가($136.81)를
정확하게 추출하는 로직을 자가 테스트합니다.
"""
import os
import sys
import datetime
from zoneinfo import ZoneInfo

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import yfinance as yf

def test_ny_close_logic():
    print("=== 미국 장중 미완성 일봉 제외 로직 테스트 ===")
    df = yf.download("SOXL", period="1mo", progress=False)
    close_series = df['Close']['SOXL'].dropna()
    
    ny_tz = ZoneInfo("America/New_York")
    now_ny = datetime.datetime.now(ny_tz)
    today_ny_str = now_ny.strftime("%Y-%m-%d")
    
    print(f"-> 현재 미국 동부시간(NY): {now_ny.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"-> yfinance 최신 2개 행:")
    print(close_series.tail(2))
    
    last_date = close_series.index[-1].strftime("%Y-%m-%d")
    print(f"-> df의 마지막 날짜: {last_date}")
    
    if last_date == today_ny_str and now_ny.hour < 16:
        print("-> [판별] 현재 미국 21일 장 진행 중(마감 전)입니다.")
        print(f"-> [적용 종가] 7월 20일 확정 종가: ${close_series.iloc[-2]:.2f}")
    else:
        print(f"-> [적용 종가] 마감 완료 종가: ${close_series.iloc[-1]:.2f}")

if __name__ == "__main__":
    test_ny_close_logic()
