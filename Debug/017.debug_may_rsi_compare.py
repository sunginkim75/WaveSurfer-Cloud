# -*- coding: utf-8 -*-
# 테스트 목적: 2026년 5월 1일 ~ 6월 15일 기간의 구글 시트 QQQRSI 데이터와 
# 로컬에서 계산된 QQQ RSI 및 모드 판정을 일자별로 상세히 비교합니다.

import os
import sys
import pandas as pd
import numpy as np

# 프로젝트 루트 경로 설정
project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, project_root)

from google.oauth2 import service_account
from googleapiclient.discovery import build
import yfinance as yf

GOOGLE_KEY_PATH = os.path.join(project_root, "config", "google_key.json")
SHEET_ID = "18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC6fw"

def main():
    output = []
    output.append("=" * 80)
    output.append("2026년 5월 ~ 6월 QQQ RSI 및 모드 상세 대조 분석")
    output.append("=" * 80)
    
    try:
        # 1. 구글 시트 QQQRSI 로드
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)
        # QQQRSI 탭 전체 데이터 읽기
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="'QQQRSI'!B4:K500"  # 날짜(B), Close(C), RSI(I), Mode(K)
        ).execute()
        
        rows = result.get("values", [])
        sheet_data = []
        for r in rows:
            if len(r) >= 8 and r[0] and r[1]:
                date_str = str(r[0]).replace(". ", "-").strip()
                # 2026년 데이터만 수집
                if "2026-" in date_str:
                    try:
                        close_val = float(str(r[1]).replace(",", ""))
                        rsi_val = float(str(r[7]).replace(",", "")) if r[7] else np.nan
                        mode_val = str(r[9]).strip() if len(r) > 9 and r[9] else "N/A"
                        sheet_data.append({
                            "date": date_str,
                            "sheet_close": close_val,
                            "sheet_rsi": rsi_val,
                            "sheet_mode": mode_val
                        })
                    except ValueError:
                        continue
        
        df_sheet = pd.DataFrame(sheet_data)
        df_sheet['date'] = pd.to_datetime(df_sheet['date'])
        
        # 2. 로컬 yfinance 로드 및 계산
        df_yf = yf.download("QQQ", start="2025-01-01", end="2026-07-15", auto_adjust=False, progress=False)
        if isinstance(df_yf.columns, pd.MultiIndex):
            df_yf.columns = df_yf.columns.get_level_values(0)
        close_yf = df_yf['Close'].dropna()
        
        # 금요일 리샘플링
        weekly_close = close_yf.resample('W-FRI').last().dropna()
        df_weekly = pd.DataFrame(weekly_close)
        df_weekly.columns = ['local_close']
        
        # SMA RSI 계산 (14주)
        delta = df_weekly['local_close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        
        period = 14
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        df_weekly['local_rsi'] = (100 - (100 / (1 + rs))).round(2)
        df_weekly['local_rsi_prev'] = df_weekly['local_rsi'].shift(1)
        
        # 모드 계산 (구글 시트 공식 100% 복제)
        local_modes = []
        current_mode = "안전"
        for idx in range(len(df_weekly)):
            if idx < 2:
                local_modes.append("안전")
                continue
                
            # 2주 전(idx-2)과 1주 전(idx-1)의 RSI 값 사용
            prev_rsi = df_weekly.iloc[idx - 2]['local_rsi']
            latest_rsi = df_weekly.iloc[idx - 1]['local_rsi']
            
            if pd.isna(latest_rsi) or pd.isna(prev_rsi):
                local_modes.append(current_mode)
                continue
                
            # 안전모드 전환 조건
            is_safe_condition = (
                (prev_rsi > 65 and prev_rsi > latest_rsi) or
                (40 < prev_rsi < 50 and prev_rsi > latest_rsi) or
                (latest_rsi < 50 and prev_rsi > 50)
            )
            
            # 공세모드 전환 조건
            is_aggressive_condition = (
                (prev_rsi < 35 and prev_rsi < latest_rsi) or
                (50 < prev_rsi < 60 and prev_rsi < latest_rsi) or
                (latest_rsi > 50 and prev_rsi < 50)
            )
            
            if is_safe_condition:
                current_mode = "안전"
            elif is_aggressive_condition:
                current_mode = "공세"
            # 조건 불만족 시 current_mode 유지 (OFFSET 상속)
            
            local_modes.append(current_mode)
            
        df_weekly['local_mode'] = local_modes
        
        # 3. 병합 및 비교 출력
        df_compare = df_sheet.merge(df_weekly, left_on='date', right_index=True, how='inner')
        output.append(f"\n{'날짜':<12} | {'시트 종가':<8} | {'로컬 종가':<8} | {'시트 RSI':<8} | {'로컬 RSI':<8} | {'시트 모드':<6} | {'로컬 모드':<6}")
        output.append("-" * 90)
        
        for idx, row in df_compare.iterrows():
            output.append(f"{row['date'].strftime('%Y-%m-%d'):<12} | {row['sheet_close']:<9.2f} | {row['local_close']:<9.2f} | {row['sheet_rsi']:<8.2f} | {row['local_rsi']:<8.2f} | {row['sheet_mode']:<8s} | {row['local_mode']:<8s}")
            
    except Exception as e:
        output.append(f"에러 발생: {e}")
        
    result_path = os.path.join(project_root, "Debug", "may_rsi_compare_result.txt")
    with open(result_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    print(f"결과가 파일에 저장되었습니다: {result_path}")

if __name__ == "__main__":
    main()
