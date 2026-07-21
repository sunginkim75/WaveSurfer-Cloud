# -*- coding: utf-8 -*-
# 테스트 목적: 2026-04-20 기준 QQQ의 주간 RSI 값을 yfinance 데이터를 다운로드해 계산하고,
# 기존의 <= d 필터링과 < d_monday 필터링 시 매칭되는 RSI 값을 비교하여 
# 모드 판정이 어떻게 바뀌는지 확인합니다.

import sys
import os
import datetime
import pandas as pd
import yfinance as yf

# Wilder's RSI 계산 함수 (백테스터와 동일)
def calculate_wilders_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def test_rsi_difference():
    # 2026-04-20 전후의 데이터를 넉넉하게 가져옴
    start_date = "2025-04-20"
    end_date = "2026-05-01"
    
    print("QQQ 주간 데이터 다운로드 중...")
    df_qqq = yf.download("QQQ", start=start_date, end=end_date, interval="1wk", progress=False)
    close_qqq = df_qqq['Close'].dropna() if not isinstance(df_qqq['Close'], pd.DataFrame) else df_qqq['Close']['QQQ'].dropna()
    
    rsi_qqq = calculate_wilders_rsi(close_qqq, 14)
    df_qqq_clean = pd.DataFrame(index=close_qqq.index)
    df_qqq_clean['RSI'] = rsi_qqq
    df_qqq_clean['RSI_prev'] = rsi_qqq.shift(1)
    
    trends = []
    for idx in range(len(df_qqq_clean)):
        row = df_qqq_clean.iloc[idx]
        if pd.isna(row['RSI']) or pd.isna(row['RSI_prev']):
            trends.append("안정")
        elif row['RSI'] >= row['RSI_prev']:
            trends.append("상승")
        else:
            trends.append("하락")
    df_qqq_clean['Trend'] = trends

    # 2026-04-20 (월요일)에 해당하는 매핑 테스트
    d = pd.Timestamp("2026-04-20")
    d_monday = d - datetime.timedelta(days=d.weekday())
    
    print("\n--- 2026-04-20 (월요일) 기준 매핑 비교 ---")
    
    # 1. 기존 필터링 (<= d)
    prev_qqq_existing = df_qqq_clean[df_qqq_clean.index <= d]
    last_row_existing = prev_qqq_existing.iloc[-1]
    print(f"[기존 <= d 필터링] 매핑된 주봉 날짜: {prev_qqq_existing.index[-1].strftime('%Y-%m-%d')}")
    print(f"RSI: {last_row_existing['RSI']:.2f}, RSI_prev: {last_row_existing['RSI_prev']:.2f}, Trend: {last_row_existing['Trend']}")
    
    # 2. 개선 필터링 (< d_monday)
    prev_qqq_improved = df_qqq_clean[df_qqq_clean.index < d_monday]
    last_row_improved = prev_qqq_improved.iloc[-1]
    print(f"\n[개선 < d_monday 필터링] 매핑된 주봉 날짜: {prev_qqq_improved.index[-1].strftime('%Y-%m-%d')}")
    print(f"RSI: {last_row_improved['RSI']:.2f}, RSI_prev: {last_row_improved['RSI_prev']:.2f}, Trend: {last_row_improved['Trend']}")
    
    # 모드 판정 테스트
    def get_mode(trend, latest_rsi, prev_rsi):
        active_mode = "안전모드"
        if trend == "하락":
            if latest_rsi > 65: active_mode = "안전모드"
            elif 40 < latest_rsi < 50: active_mode = "안전모드"
            elif prev_rsi >= 50 > latest_rsi: active_mode = "안전모드"
        elif trend == "상승":
            if prev_rsi <= 50 < latest_rsi: active_mode = "공세모드"
            elif 50 < latest_rsi < 60: active_mode = "공세모드"
            elif latest_rsi < 35: active_mode = "공세모드"
        return active_mode

    mode_existing = get_mode(last_row_existing['Trend'], last_row_existing['RSI'], last_row_existing['RSI_prev'])
    mode_improved = get_mode(last_row_improved['Trend'], last_row_improved['RSI'], last_row_improved['RSI_prev'])
    
    print(f"\n기존 매핑 판정 결과: {mode_existing}")
    print(f"개선 매핑 판정 결과: {mode_improved}")

if __name__ == "__main__":
    test_rsi_difference()
