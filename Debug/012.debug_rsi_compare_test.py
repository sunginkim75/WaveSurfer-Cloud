# -*- coding: utf-8 -*-
# 테스트 목적: 구글 시트 'QQQRSI' 탭의 실제 데이터(날짜, 종가, RSI)와 
# yfinance 데이터를 매주 금요일 종가로 추출하여 계산한 SMA RSI의 일치 여부를 검증합니다.

import os
import sys
import pandas as pd
import numpy as np
import datetime

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

def calculate_sma_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # 구글 시트 수식인 SUM(OFFSET(...))/14 와 동일한 단순 이동평균(SMA) 계산
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.round(2)

def main():
    print("=" * 70)
    print("구글 시트 QQQ RSI vs 로컬 SMA RSI 비교 검증")
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
        print(f"구글 시트 데이터 파싱 완료: {len(df_sheet)}건")
        
        # 2. yfinance 로컬 데이터 다운로드
        start_date = "2018-04-01"
        end_date = "2026-07-15"
        print("yfinance에서 QQQ 일봉 데이터 다운로드 중...")
        df_yf = yf.download("QQQ", start=start_date, end=end_date, auto_adjust=False, progress=False)
        
        # DataFrame MultiIndex 대응
        if isinstance(df_yf.columns, pd.MultiIndex):
            df_yf.columns = df_yf.columns.get_level_values(0)
            
        close_yf = df_yf['Close'].dropna()
        
        # 매주 금요일 종가만 추출 (구글 시트 날짜와 맞춤)
        # 구글 시트에 있는 금요일 날짜를 기준으로 yfinance 데이터 매핑
        local_data = []
        for idx, row in df_sheet.iterrows():
            target_date = row['date']
            # 만약 금요일이 휴장일인 경우, 해당 주 마지막 거래일 종가를 가져옴
            if target_date in close_yf.index:
                price = close_yf.loc[target_date]
            else:
                # 3일 이내에 있는 가장 가까운 과거 거래일 찾기
                prices_before = close_yf[close_yf.index <= target_date]
                if not prices_before.empty:
                    price = prices_before.iloc[-1]
                else:
                    price = np.nan
            local_data.append({
                "date": target_date,
                "local_close": float(price)
            })
            
        df_local = pd.DataFrame(local_data)
        df_local.set_index('date', inplace=True)
        
        # 로컬에서 SMA RSI 계산
        df_local['local_rsi'] = calculate_sma_rsi(df_local['local_close'], 14)
        
        # 3. 비교 분석 및 출력
        df_compare = df_sheet.merge(df_local, on='date', how='inner')
        print(f"\n매칭된 데이터 비교 (총 {len(df_compare)}건 중 상위 30건):")
        print(f"{'날짜':<12} | {'시트 종가':<8} | {'로컬 종가':<8} | {'시트 RSI':<8} | {'로컬 RSI':<8} | {'오차'}")
        print("-" * 75)
        
        errors = []
        for idx, row in df_compare.iterrows():
            close_diff = abs(row['sheet_close'] - row['local_close'])
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
                print("\n[성공] 로컬 SMA RSI와 구글 시트 RSI가 거의 완벽히 일치합니다!")
            else:
                print("\n[주의] 오차가 발생했습니다. 로직이나 날짜 매핑을 다시 확인해야 합니다.")
                
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    main()
