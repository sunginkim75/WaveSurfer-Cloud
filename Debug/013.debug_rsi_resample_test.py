# -*- coding: utf-8 -*-
# 테스트 목적: pandas.resample('W-FRI').last() 방식을 통해 생성한 주간 종가 기반 SMA RSI가 
# 구글 시트의 QQQRSI 데이터와 정확히 매칭되는지 오차율을 계산하여 검증합니다.

import os
import sys
import pandas as pd
import numpy as np

# 프로젝트 루트 경로 설정
project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, project_root)

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    import yfinance as yf
except ImportError:
    os.system(f"{sys.executable} -m pip install google-auth google-api-python-client yfinance pandas -q")
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    import yfinance as yf

GOOGLE_KEY_PATH = os.path.join(project_root, "config", "google_key.json")
SHEET_ID = "18KaZk-kz7eN2dRDV1xjd9XQKvXwZhHgi6iRkC9sC6fw"

def main():
    print("=" * 70)
    print("Pandas Resample('W-FRI') 활용 QQQ RSI 오차 검증")
    print("=" * 70)
    
    try:
        # 1. 구글 시트 데이터 로드
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range="'QQQRSI'!B5:J100"  # 날짜(B), Close(C), RSI(I) 읽기
        ).execute()
        
        sheet_rows = result.get("values", [])
        sheet_data = []
        for r in sheet_rows:
            if len(r) >= 8 and r[0] and r[1]:
                try:
                    date_str = r[0].replace(". ", "-").strip() # "2018. 05. 04" -> "2018-05-04"
                    close_val = float(str(r[1]).replace(",", ""))
                    rsi_val = float(str(r[7]).replace(",", "")) if len(r) > 7 and r[7] else None
                    sheet_data.append({
                        "date": date_str,
                        "sheet_close": close_val,
                        "sheet_rsi": rsi_val
                    })
                except ValueError:
                    continue
        
        df_sheet = pd.DataFrame(sheet_data)
        df_sheet['date'] = pd.to_datetime(df_sheet['date'])
        print(f"구글 시트 데이터 로드 완료: {len(df_sheet)}건")
        
        # 2. yfinance 로컬 데이터 다운로드
        start_date = "2018-04-01"
        end_date = "2026-07-15"
        print("yfinance에서 QQQ 일봉 데이터 다운로드 중...")
        df_yf = yf.download("QQQ", start=start_date, end=end_date, auto_adjust=False, progress=False)
        
        if isinstance(df_yf.columns, pd.MultiIndex):
            df_yf.columns = df_yf.columns.get_level_values(0)
            
        close_yf = df_yf['Close'].dropna()
        
        # resample('W-FRI').last() 적용하여 금요일 기준 주봉 완성
        weekly_close = close_yf.resample('W-FRI').last().dropna()
        
        # 데이터프레임으로 변환
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
        
        # 3. 구글 시트 날짜와 머지하여 비교
        df_compare = df_sheet.merge(df_weekly, left_on='date', right_index=True, how='inner')
        print(f"\n매칭된 데이터 비교 (총 {len(df_compare)}건 중 상위 30건):")
        print(f"{'날짜':<12} | {'시트 종가':<8} | {'로컬 종가':<8} | {'시트 RSI':<8} | {'로컬 RSI':<8} | {'오차'}")
        print("-" * 75)
        
        errors = []
        for idx, row in df_compare.iterrows():
            rsi_diff = abs(row['sheet_rsi'] - row['local_rsi']) if pd.notna(row['sheet_rsi']) and pd.notna(row['local_rsi']) else 0
            if pd.notna(row['sheet_rsi']) and pd.notna(row['local_rsi']):
                errors.append(rsi_diff)
            
            if idx < 30:
                rsi_s = f"{row['sheet_rsi']:.2f}" if pd.notna(row['sheet_rsi']) else "N/A"
                rsi_l = f"{row['local_rsi']:.2f}" if pd.notna(row['local_rsi']) else "N/A"
                err_s = f"{rsi_diff:.2f}" if pd.notna(row['sheet_rsi']) and pd.notna(row['local_rsi']) else "N/A"
                print(f"{row['date'].strftime('%Y-%m-%d'):<12} | {row['sheet_close']:<9.2f} | {row['local_close']:<9.2f} | {rsi_s:<8} | {rsi_l:<8} | {err_s}")
                
        if errors:
            print(f"\nRSI 최대 오차: {max(errors):.4f}")
            print(f"RSI 평균 오차: {np.mean(errors):.4f}")
            if max(errors) < 0.1:
                print("\n[성공] resample('W-FRI').last() 방식의 로컬 SMA RSI와 구글 시트 RSI가 완벽히 일치합니다!")
            else:
                print("\n[주의] 오차가 발생했습니다. 확인이 필요합니다.")
                
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    main()
