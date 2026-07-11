# -*- coding: utf-8 -*-
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import logging
from typing import Dict, List, Any, Tuple, Optional

logger = logging.getLogger(__name__)

class Backtester:
    """
    WaveSurfer-Cloud 백테스트 엔진.
    기존 Google Sheets API 의존성 없이 yfinance 데이터를 활용하여
    로컬(서버)에서 고속으로 백테스트 시뮬레이션을 실행합니다.
    """

    @staticmethod
    def calculate_wilders_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """
        Wilder's Smoothing 방식의 RSI 계산
        """
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        
        # Wilder's Smoothing (Exponential Moving Average with alpha=1/period)
        avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @classmethod
    def get_market_data(cls, ticker: str, start_date_str: str, end_date_str: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        백테스트에 필요한 대상 종목의 일봉 데이터와 QQQ의 주간 RSI 데이터를 yfinance로부터 수집합니다.
        RSI 계산의 안정성을 위해 시작일(start_date)보다 1년 전부터 데이터를 수집합니다.
        """
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        
        # RSI 14주 계산을 위해 QQQ 데이터는 시작일 기준 1년 전부터 받아옴
        qqq_start_date = start_date - datetime.timedelta(days=365)
        qqq_start_str = qqq_start_date.strftime("%Y-%m-%d")
        
        logger.info(f"Downloading QQQ weekly data from {qqq_start_str} to {end_date_str}")
        df_qqq = yf.download("QQQ", start=qqq_start_str, end=end_date_str, interval="1wk", progress=False)
        if df_qqq.empty:
            raise ValueError("QQQ 주간 데이터를 불러오지 못했습니다.")
            
        # QQQ MultiIndex 처리 방지
        if isinstance(df_qqq.columns, pd.MultiIndex):
            close_qqq = df_qqq['Close']['QQQ']
        else:
            close_qqq = df_qqq['Close']
            
        close_qqq = close_qqq.dropna()
        rsi_qqq = cls.calculate_wilders_rsi(close_qqq, 14)
        
        # QQQ 데이터프레임 구성 (RSI, 전주 RSI, Trend 포함)
        df_qqq_clean = pd.DataFrame(index=close_qqq.index)
        df_qqq_clean['RSI'] = rsi_qqq
        df_qqq_clean['RSI_prev'] = rsi_qqq.shift(1)
        
        # 상승/하락 트렌드 판정
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

        # 대상 종목 일봉 데이터 로드
        logger.info(f"Downloading target {ticker} daily data from {start_date_str} to {end_date_str}")
        df_target = yf.download(ticker, start=start_date_str, end=end_date_str, interval="1d", progress=False)
        if df_target.empty:
            raise ValueError(f"{ticker} 일일 종가 데이터를 불러오지 못했습니다.")
            
        if isinstance(df_target.columns, pd.MultiIndex):
            df_target_clean = pd.DataFrame(index=df_target.index)
            df_target_clean['Close'] = df_target['Close'][ticker]
        else:
            df_target_clean = pd.DataFrame(index=df_target.index)
            df_target_clean['Close'] = df_target['Close']
            
        df_target_clean = df_target_clean.dropna()
        
        return df_target_clean, df_qqq_clean

    @classmethod
    def run_backtest(cls, 
                     ticker: str,
                     start_date_str: str = "2018-07-27",
                     end_date_str: Optional[str] = None,
                     seed_amt: float = 10000.0,
                     safe_buy_pct: float = 3.0,
                     safe_sell_pct: float = 0.2,
                     agg_buy_pct: float = 5.0,
                     agg_sell_pct: float = 2.5,
                     split_count: int = 7,
                     update_period: int = 10,
                     compounding_profit_rate: float = 80.0,
                     compounding_loss_rate: float = 30.0) -> Dict[str, Any]:
        """
        파이썬 기반 백테스트 시뮬레이션 핵심 로직 실행.
        """
        if not end_date_str:
            end_date_str = datetime.date.today().strftime("%Y-%m-%d")
            
        df_target, df_qqq = cls.get_market_data(ticker, start_date_str, end_date_str)
        
        # 1. 일봉 데이터와 QQQ 주간 RSI 데이터 매핑
        sim_dates_data = []
        for d in df_target.index:
            # 해당 일봉 날짜 d와 같거나 이전인 가장 최근의 QQQ 주간 RSI 행 매핑
            prev_qqq_rows = df_qqq[df_qqq.index <= d]
            if prev_qqq_rows.empty:
                rsi = 50.0
                prev_rsi = 50.0
                trend = "하락"
            else:
                last_row = prev_qqq_rows.iloc[-1]
                rsi = float(last_row['RSI'])
                prev_rsi = float(last_row['RSI_prev']) if not pd.isna(last_row['RSI_prev']) else rsi
                trend = str(last_row['Trend'])
                
            sim_dates_data.append({
                "date": d.strftime("%Y-%m-%d"),
                "close": float(df_target.loc[d, 'Close']),
                "rsi": rsi,
                "prev_rsi": prev_rsi,
                "trend": trend,
                "mode": "안전모드"
            })
            
        # 2. 백테스트 시뮬레이션 본게임
        cash = seed_amt
        last_compounding_cash = seed_amt
        buy_batches = [] # {buyPrice, qty, cycleDays, buyMode, buyDate}
        sim_tx_log = []
        sim_history = []
        
        for i, today in enumerate(sim_dates_data):
            prev = sim_dates_data[i - 1] if i > 0 else None
            today_close = today["close"]
            
            # (1) 당일 장마감 시점 매도 조건 판정
            today_realized_profit = 0.0
            
            for b in range(len(buy_batches) - 1, -1, -1):
                batch = buy_batches[b]
                
                if batch["buyMode"] == "공세모드":
                    target_sell = batch["buyPrice"] * (1 + (agg_sell_pct / 100))
                    limit_days = 7
                else:
                    target_sell = batch["buyPrice"] * (1 + (safe_sell_pct / 100))
                    limit_days = 30
                    
                should_sell = False
                sell_type = "LOC 매도"
                
                if batch["cycleDays"] > 0 and today_close >= target_sell:
                    should_sell = True
                    sell_type = "LOC 매도"
                elif batch["cycleDays"] >= limit_days:
                    should_sell = True
                    sell_type = "MOC 청산"
                    
                if should_sell:
                    revenue = batch["qty"] * today_close
                    cash += revenue
                    buy_cost = batch["buyPrice"] * batch["qty"]
                    profit = revenue - buy_cost
                    today_realized_profit += profit
                    
                    sim_tx_log.append({
                        "date": today["date"],
                        "type": sell_type,
                        "price": today_close,
                        "qty": batch["qty"],
                        "amount": revenue,
                        "holdings": sum(x["qty"] for x in buy_batches) - batch["qty"],
                        "cash": cash,
                        "buyDate": batch["buyDate"],
                        "buyPrice": batch["buyPrice"]
                    })
                    buy_batches.pop(b)
                    
            today["realized"] = today_realized_profit
            
            # (2) 당일 매매모드 판정
            current_mode = "안전모드"
            if buy_batches:
                current_mode = buy_batches[-1]["buyMode"]
                
            trend = today["trend"]
            latest_rsi = today["rsi"]
            prev_rsi = today["prev_rsi"]
            
            if trend == "하락":
                if latest_rsi > 65:
                    current_mode = "안전모드"
                elif 40 < latest_rsi < 50:
                    current_mode = "안전모드"
                elif prev_rsi >= 50 > latest_rsi:
                    current_mode = "안전모드"
            elif trend == "상승":
                if prev_rsi <= 50 < latest_rsi:
                    current_mode = "공세모드"
                elif 50 < latest_rsi < 60:
                    current_mode = "공세모드"
                elif latest_rsi < 35:
                    current_mode = "공세모드"
                    
            today["mode"] = current_mode
            
            # (3) LOC 매수 검사 및 실행
            base_price_for_buy = prev["close"] if prev else today_close
            if current_mode == "공세모드":
                target_buy = base_price_for_buy * (1 + (agg_buy_pct / 100))
            else:
                target_buy = base_price_for_buy * (1 + (safe_buy_pct / 100))
                
            if today_close <= target_buy:
                buy_limit_amt = last_compounding_cash / split_count
                buy_qty = int(buy_limit_amt // target_buy)
                cost = buy_qty * today_close
                
                if buy_qty > 0 and cash >= cost:
                    cash -= cost
                    buy_batches.append({
                        "buyPrice": today_close,
                        "qty": buy_qty,
                        "cycleDays": 0,
                        "buyMode": current_mode,
                        "buyDate": today["date"]
                    })
                    
                    sim_tx_log.append({
                        "date": today["date"],
                        "type": "LOC 매수",
                        "price": today_close,
                        "qty": buy_qty,
                        "amount": cost,
                        "holdings": sum(x["qty"] for x in buy_batches),
                        "cash": cash
                    })
                    
            # (4) 10거래일 단위 복리 주기 반영
            buy_limit_amt = last_compounding_cash / split_count
            compounding_amt_val = 0.0
            is_compounding_day = False
            
            if i > 0 and (i + 1) % update_period == 0:
                bfs = 0.0
                for idx in range(i - (update_period - 1), i + 1):
                    if idx >= 0 and idx < len(sim_dates_data):
                        bfs += sim_dates_data[idx].get("realized", 0.0)
                        
                if bfs < 0:
                    compounding_amt_val = bfs * (compounding_loss_rate / 100)
                else:
                    compounding_amt_val = bfs * (compounding_profit_rate / 100)
                    
                last_compounding_cash += compounding_amt_val
                last_compounding_cash = max(1000.0, last_compounding_cash)
                is_compounding_day = True
                
            # (5) 기존 매수 배치들의 경과일(cycleDays) 1 증가
            for batch in buy_batches:
                batch["cycleDays"] += 1
                
            # 자산 평가액 계산
            eval_amt = sum(b["qty"] * today_close for b in buy_batches)
            total_asset = cash + eval_amt
            
            sim_history.append({
                "date": today["date"],
                "totalAsset": total_asset,
                "cash": cash,
                "evalAmt": eval_amt,
                "close": today_close,
                "mdd": 0.0,
                "buyLimitAmt": buy_limit_amt,
                "compoundingAmt": compounding_amt_val if is_compounding_day else 0.0,
                "updatedCompoundingCash": last_compounding_cash if is_compounding_day else 0.0
            })
            
        # 3. 최종 연산 및 통계 산출
        final_close = sim_dates_data[-1]["close"] if sim_dates_data else 0.0
        final_asset = cash + sum(b["qty"] * final_close for b in buy_batches)
        total_return = ((final_asset - seed_amt) / seed_amt) * 100.0
        realized_profit_val = final_asset - seed_amt
        
        # MDD 계산
        peak = seed_amt
        mdd = 0.0
        for h in sim_history:
            if h["totalAsset"] > peak:
                peak = h["totalAsset"]
            dd = ((h["totalAsset"] - peak) / peak) * 100.0
            h["mdd"] = float(abs(dd))
            if dd < mdd:
                mdd = dd
                
        # CAGR 계산
        years = len(sim_dates_data) / 252.0
        cagr = ((final_asset / seed_amt) ** (1.0 / years) - 1.0) * 100.0 if years > 0 else total_return
        
        # 엑셀 대조용 상세 테이블 구성
        row_map = {}
        for d in sim_dates_data:
            row_map[d["date"]] = {
                "date": d["date"],
                "close": d["close"],
                "mode": d["mode"],
                "buyLimitAmt": "",
                "buyQty": "",
                "buyAmt": "",
                "targetSell": "",
                "sellDate": "",
                "sellPrice": "",
                "sellQty": "",
                "sellAmt": "",
                "cash": "",
                "todayRealized": "-",
                "compoundingAmt": "",
                "updatedCompoundingCash": "",
                "profitAmt": "",
                "accumProfit": ""
            }
            
        for h in sim_history:
            dt = h["date"]
            if dt in row_map:
                row_map[dt]["cash"] = h["cash"]
                row_map[dt]["buyLimitAmt"] = h["buyLimitAmt"]
                if h["compoundingAmt"] != 0:
                    row_map[dt]["compoundingAmt"] = h["compoundingAmt"]
                    row_map[dt]["updatedCompoundingCash"] = h["updatedCompoundingCash"]
                    
        for tx in sim_tx_log:
            if tx["type"] == "LOC 매수":
                dt = tx["date"]
                if dt in row_map:
                    row_map[dt]["buyQty"] = f"{tx['qty']}주"
                    row_map[dt]["buyAmt"] = tx["amount"]
                    
                    if row_map[dt]["mode"] == "공세모드":
                        target_val = tx["price"] * (1 + (agg_sell_pct / 100))
                    else:
                        target_val = tx["price"] * (1 + (safe_sell_pct / 100))
                    row_map[dt]["targetSell"] = target_val
                    
        for tx in sim_tx_log:
            if "매도" in tx["type"] or "청산" in tx["type"]:
                buy_dt = tx.get("buyDate")
                if buy_dt and buy_dt in row_map:
                    r = row_map[buy_dt]
                    r["sellDate"] = tx["date"]
                    r["sellPrice"] = tx["price"]
                    r["sellQty"] = f"{tx['qty']}주"
                    r["sellAmt"] = tx["amount"]
                    
                    buy_amt_num = tx["qty"] * tx["buyPrice"]
                    sell_amt_num = tx["amount"]
                    profit_num = sell_amt_num - buy_amt_num
                    r["profitAmt"] = profit_num
                    
        accum_realized = 0.0
        for d in sim_dates_data:
            dt = d["date"]
            r = row_map[dt]
            
            today_total_realized = 0.0
            for row in row_map.values():
                if row["sellDate"] == dt and row["profitAmt"] != "":
                    today_total_realized += float(row["profitAmt"])
                    
            if today_total_realized != 0.0:
                accum_realized += today_total_realized
                r["todayRealized"] = today_total_realized
                r["accumProfit"] = accum_realized
            else:
                r["todayRealized"] = "-"
                if accum_realized != 0.0:
                    r["accumProfit"] = accum_realized
                    
        detailed_tx_table = list(row_map.values())
        
        return {
            "ticker": ticker,
            "startDate": start_date_str,
            "endDate": end_date_str,
            "params": {
                "safeBuyPct": safe_buy_pct,
                "safeSellPct": safe_sell_pct,
                "aggBuyPct": agg_buy_pct,
                "aggSellPct": agg_sell_pct,
                "splitCount": split_count,
                "updatePeriod": update_period,
                "compoundingProfitRate": compounding_profit_rate,
                "compoundingLossRate": compounding_loss_rate,
                "seedAmt": seed_amt
            },
            "summary": {
                "totalReturn": float(total_return),
                "mdd": float(abs(mdd)),
                "cagr": float(cagr),
                "realizedProfitVal": float(realized_profit_val)
            },
            "history": sim_history,
            "detailedTxTable": detailed_tx_table
        }
