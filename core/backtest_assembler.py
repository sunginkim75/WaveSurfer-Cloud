# -*- coding: utf-8 -*-
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import os
import logging
from typing import Dict, List, Any, Tuple, Optional
from utils.db_handler import DBHandler
from core.backtester import Backtester

logger = logging.getLogger(__name__)

class BacktestAssembler:
    """
    실제 운영 중인 Task의 체결 내역(batches, history)과 yfinance 시장 데이터를 
    결합하여, 구글 시트 엑셀 양식과 100% 대응되는 일자별 진행 현황표를 조립합니다.
    """

    @classmethod
    def assemble_matching_table(cls, task_config: dict) -> List[Dict[str, Any]]:
        db = DBHandler()
        task_id = task_config.get("id")
        
        # 1. 실제 체결 데이터 로드
        batches_file = f"config/trade_batches_{task_id}.json"
        history_file = f"config/trade_history_{task_id}.json"
        
        batches = db.load_json(batches_file, default_data=[])
        history = db.load_json(history_file, default_data=[])
        
        # 2. 시작일 설정 (체결 내역 중 가장 빠른 매수일자 또는 최근 3개월)
        all_dates = []
        for b in batches:
            if b.get("buyDate"): all_dates.append(b["buyDate"])
        for h in history:
            if h.get("buyDate"): all_dates.append(h["buyDate"])
            if h.get("date"): all_dates.append(h["date"])
            
        if all_dates:
            # 안전하게 파싱 후 정렬하여 최초 시작일 획득
            parsed_dates = []
            for dt in all_dates:
                try:
                    parsed_dates.append(datetime.datetime.strptime(dt, "%Y-%m-%d"))
                except:
                    pass
            if parsed_dates:
                # 첫 거래일 10일 전부터 시작하여 표의 마진 확보
                start_date = min(parsed_dates) - datetime.timedelta(days=15)
                start_date_str = start_date.strftime("%Y-%m-%d")
            else:
                start_date_str = (datetime.date.today() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
        else:
            # 거래 데이터가 없으면 최근 90일
            start_date_str = (datetime.date.today() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
            
        end_date_str = datetime.date.today().strftime("%Y-%m-%d")
        
        ticker = task_config.get("ticker", "SOXL")
        rsi_ticker = task_config.get("rsi_ticker", "QQQ")
        
        # 3. yfinance에서 시장 데이터 획득
        try:
            df_target, df_qqq = Backtester.get_market_data(ticker, start_date_str, end_date_str)
        except Exception as e:
            logger.error(f"시장 데이터 다운로드 에러: {e}")
            # 다운로드 실패 시 빈 리스트 반환
            return []
            
        # 4. 영업일별 날짜와 QQQ RSI 매핑 진행
        sim_dates_data = []
        for d in df_target.index:
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
            
        # 5. 매수/매도 매칭을 위한 맵 구조화
        # buy_date별 실제 매수 및 매도 체결 데이터 결합
        # key: buy_date (매수일자) -> list of matching trades
        matching_trades = {}
        
        # A. 완료된 역사적 체결 (history) 매핑
        for h in history:
            b_date = h.get("buyDate")
            if not b_date:
                # 만약 과거 데이터에 buyDate가 없으면 매도 날짜 당일로 임시 세팅
                b_date = h.get("date")
            if not b_date:
                continue
                
            if b_date not in matching_trades:
                matching_trades[b_date] = []
                
            matching_trades[b_date].append({
                "is_sold": True,
                "buyPrice": h.get("buyPrice", 0.0),
                "buyQty": h.get("qty", 0),
                "buyAmt": h.get("buyPrice", 0.0) * h.get("qty", 0),
                "buyMode": h.get("buyMode", "공세모드" if h.get("realized_profit", 0) > 0 else "안전모드"),
                "sellDate": h.get("date", ""),
                "sellPrice": h.get("sellPrice", 0.0),
                "sellQty": f"{h.get('qty', 0)}주",
                "sellAmt": h.get("sellPrice", 0.0) * h.get("qty", 0),
                "realized_profit": h.get("realized_profit", 0.0)
            })
            
        # B. 미실현 보유 중 배치 (batches) 매핑
        for b in batches:
            b_date = b.get("buyDate")
            if not b_date:
                continue
                
            if b_date not in matching_trades:
                matching_trades[b_date] = []
                
            matching_trades[b_date].append({
                "is_sold": False,
                "buyPrice": b.get("buyPrice", 0.0),
                "buyQty": b.get("qty", 0),
                "buyAmt": b.get("buyPrice", 0.0) * b.get("qty", 0),
                "buyMode": b.get("buyMode", "안전모드"),
                "cycleDays": b.get("cycleDays", 0),
                "sellDate": "보유중",
                "sellPrice": "-",
                "sellQty": "-",
                "sellAmt": "-",
                "realized_profit": 0.0
            })
            
        # 6. 매 영업일 루프를 돌면서 엑셀 17열 대조 데이터 생성
        seed_amt = float(task_config.get("seed_amt", 10000.0))
        last_compounding_cash = seed_amt
        split_count = int(task_config.get("split_count", 7))
        update_period = int(task_config.get("update_period", 10))
        compounding_profit_rate = float(task_config.get("compounding_profit_rate", 80.0))
        compounding_loss_rate = float(task_config.get("compounding_loss_rate", 30.0))
        
        safe_buy_pct = float(task_config.get("safe_buy_pct", 3.0))
        safe_sell_pct = float(task_config.get("safe_sell_pct", 0.2))
        agg_buy_pct = float(task_config.get("agg_buy_pct", 5.0))
        agg_sell_pct = float(task_config.get("agg_sell_pct", 2.5))
        
        # 수수료 상수
        commission_rate = 0.00044 # 0.044%
        sec_fee_rate = 0.0000278 # 0.00278%
        
        table_rows = []
        accum_profit = 0.0
        
        # 보유 배치들 추적용 (MOC 매도일 계산용)
        # 매 영업일 인덱스를 구하기 위해 날짜 목록 추출
        trade_dates_list = [d["date"] for d in sim_dates_data]
        
        # 봇의 모드 전환 룰 적용을 위한 전역 변수
        active_mode = "안전모드"
        
        for i, today in enumerate(sim_dates_data):
            date_str = today["date"]
            today_close = today["close"]
            prev = sim_dates_data[i - 1] if i > 0 else None
            
            # (1) 변동률
            change_pct = 0.0
            if prev:
                change_pct = ((today_close - prev["close"]) / prev["close"]) * 100.0
                
            # (2) 당일 매매모드 결정 (백테스터와 동일한 트렌드 기반 모드 판정)
            # 단, 이전에 실제 체결된 매수 배치가 존재한다면 그 배치의 모드를 이어받습니다.
            past_buys = []
            for dt, trades in matching_trades.items():
                if dt < date_str:
                    past_buys.extend(trades)
            if past_buys:
                # 가장 마지막에 체결된 매수의 모드를 기본값으로 계승
                # 날짜 정렬 후 최신 매수 모드 추출
                sorted_past_buys = sorted(past_buys, key=lambda x: x.get("buyDate", date_str))
                if sorted_past_buys:
                    active_mode = sorted_past_buys[-1]["buyMode"]
                    
            trend = today["trend"]
            latest_rsi = today["rsi"]
            prev_rsi = today["prev_rsi"]
            
            if trend == "하락":
                if latest_rsi > 65: active_mode = "안전모드"
                elif 40 < latest_rsi < 50: active_mode = "안전모드"
                elif prev_rsi >= 50 > latest_rsi: active_mode = "안전모드"
            elif trend == "상승":
                if prev_rsi <= 50 < latest_rsi: active_mode = "공세모드"
                elif 50 < latest_rsi < 60: active_mode = "공세모드"
                elif latest_rsi < 35: active_mode = "공세모드"
                
            # (3) 당일 실현손익 합산
            today_realized_profit = 0.0
            # 오늘 날짜로 매도 완료된 모든 거래 찾기
            today_sells = []
            for dt, trades in matching_trades.items():
                for t in trades:
                    if t.get("is_sold") and t.get("sellDate") == date_str:
                        today_sells.append(t)
                        today_realized_profit += t.get("realized_profit", 0.0)
                        
            # (4) 10거래일 단위 복리 주기 반영 (실제 실현손익 흐름에 맞춰 복리 가산)
            compounding_amt_val = 0.0
            is_compounding_day = False
            
            # 이전 10일간의 당일실현손익 계산
            if i > 0 and (i + 1) % update_period == 0:
                # 10일간의 실현손익 합산
                bfs = 0.0
                # 이 테이블에서는 실제 봇의 실현손익 흐름을 활용합니다
                for idx in range(i - (update_period - 1), i + 1):
                    if idx >= 0 and idx < len(table_rows):
                        bfs += float(table_rows[idx].get("realizedNum", 0.0))
                # 현재 날짜(오늘) 발생한 실현손익 추가
                bfs += today_realized_profit
                
                if bfs < 0:
                    compounding_amt_val = bfs * (compounding_loss_rate / 100)
                else:
                    compounding_amt_val = bfs * (compounding_profit_rate / 100)
                    
                last_compounding_cash += compounding_amt_val
                last_compounding_cash = max(1000.0, last_compounding_cash)
                is_compounding_day = True
                
            # (5) 매수예정액 계산
            buy_limit_amt = last_compounding_cash / split_count
            
            # (6) LOC 매수목표가 계산 (전일 종가 기준)
            base_price = prev["close"] if prev else today_close
            if active_mode == "공세모드":
                target_buy = base_price * (1 + (agg_buy_pct / 100))
            else:
                target_buy = base_price * (1 + (safe_buy_pct / 100))
                
            target_qty = int(buy_limit_amt // target_buy) if target_buy > 0 else 0
            
            # (7) 실제 매수/매도 체결 데이터 매핑 (오늘 buyDate 인 거래들)
            today_trades = matching_trades.get(date_str, [])
            
            # 오늘 매수 기록이 없으면 빈 행 1줄 생성
            if not today_trades:
                row_item = {
                    "date": date_str,
                    "close": today_close,
                    "mode": active_mode,
                    "change": change_pct,
                    "buyLimitAmt": buy_limit_amt,
                    "targetBuy": target_buy,
                    "targetQty": target_qty,
                    "buyPrice": "",
                    "buyQty": "",
                    "buyAmt": "",
                    "fee": "",
                    "targetSell": "",
                    "moc": False,
                    "mocSellDate": "",
                    "sellDate": "",
                    "sellPrice": "",
                    "sellQty": "",
                    "sellAmt": "",
                    "realized": "-",
                    "realizedNum": today_realized_profit,
                    "accumProfit": "-",
                    "compoundingAmt": compounding_amt_val if is_compounding_day else "",
                    "updatedCompoundingCash": last_compounding_cash if is_compounding_day else ""
                }
                
                if today_realized_profit != 0.0:
                    accum_profit += today_realized_profit
                    row_item["realized"] = today_realized_profit
                    row_item["accumProfit"] = accum_profit
                elif accum_profit != 0.0:
                    row_item["accumProfit"] = accum_profit
                    
                table_rows.append(row_item)
            else:
                # 오늘 매수가 여러 건 발생한 경우 (혹은 분할 매수 등)
                for idx, trade in enumerate(today_trades):
                    # 매도 목표가
                    if trade["buyMode"] == "공세모드":
                        target_sell = trade["buyPrice"] * (1 + (agg_sell_pct / 100))
                        limit_days = 7
                    else:
                        target_sell = trade["buyPrice"] * (1 + (safe_sell_pct / 100))
                        limit_days = 30
                        
                    # 수수료 계산 (매수금액의 0.044%)
                    fee = trade["buyAmt"] * commission_rate
                    
                    # MOC 목표일자 계산 (영업일 기준 limit_days 째 날짜)
                    moc_date_str = ""
                    if i < len(trade_dates_list):
                        moc_idx = min(i + limit_days, len(trade_dates_list) - 1)
                        moc_date_str = trade_dates_list[moc_idx]
                        
                    # MOC 청산 여부
                    is_moc_liquidated = False
                    if trade.get("is_sold") and "MOC" in trade.get("sellDate", ""):
                        is_moc_liquidated = True
                    elif not trade.get("is_sold") and trade.get("cycleDays", 0) >= limit_days:
                        is_moc_liquidated = True
                        
                    row_item = {
                        "date": date_str if idx == 0 else "", # 중복 날짜 방지용 빈칸 처리
                        "close": today_close if idx == 0 else "",
                        "mode": active_mode if idx == 0 else "",
                        "change": change_pct if idx == 0 else "",
                        "buyLimitAmt": buy_limit_amt if idx == 0 else "",
                        "targetBuy": target_buy if idx == 0 else "",
                        "targetQty": target_qty if idx == 0 else "",
                        "buyPrice": trade["buyPrice"],
                        "buyQty": f"{trade['buyQty']}주",
                        "buyAmt": trade["buyAmt"],
                        "fee": fee,
                        "targetSell": target_sell,
                        "moc": is_moc_liquidated,
                        "mocSellDate": moc_date_str,
                        "sellDate": trade["sellDate"],
                        "sellPrice": trade["sellPrice"],
                        "sellQty": trade["sellQty"],
                        "sellAmt": trade["sellAmt"],
                        "realized": "-",
                        "realizedNum": today_realized_profit if idx == 0 else 0.0,
                        "accumProfit": "-",
                        "compoundingAmt": compounding_amt_val if (is_compounding_day and idx == 0) else "",
                        "updatedCompoundingCash": last_compounding_cash if (is_compounding_day and idx == 0) else ""
                    }
                    
                    # 첫 번째 서브행에만 오늘 실현손익 및 누적손익 기입
                    if idx == 0:
                        if today_realized_profit != 0.0:
                            accum_profit += today_realized_profit
                            row_item["realized"] = today_realized_profit
                            row_item["accumProfit"] = accum_profit
                        elif accum_profit != 0.0:
                            row_item["accumProfit"] = accum_profit
                    else:
                        # 서브행들은 누적손익만 유지
                        if accum_profit != 0.0:
                            row_item["accumProfit"] = accum_profit
                            
                    table_rows.append(row_item)
                    
        # 7. 예수금 잔액(cash) 및 총자산 추적 반영 (최종 가공)
        # 엑셀 시트의 J열(예수금), K열(총자산)과 호환되도록 필드를 채워 줍니다
        running_cash = seed_amt
        current_date = None
        current_close = 0.0
        
        for r in table_rows:
            if r.get("date") != "":
                current_date = r["date"]
                current_close = r["close"]
                
            if r.get("buyAmt") != "":
                running_cash -= float(r["buyAmt"])
                if r.get("fee") != "":
                    running_cash -= float(r["fee"])
            if r.get("sellAmt") != "" and r["sellAmt"] != "-":
                running_cash += float(r["sellAmt"])
                
            r["cash"] = running_cash
            
            # 당일 보유 수량 계산 (장마감 기준)
            qty_held = 0
            if current_date:
                for buy_date, trades in matching_trades.items():
                    if buy_date <= current_date:
                        for t in trades:
                            if not t["is_sold"] or t["sellDate"] > current_date:
                                qty_held += t["buyQty"]
                                
            eval_amt = qty_held * current_close
            r["evalAmt"] = eval_amt
            r["totalAsset"] = running_cash + eval_amt
            
        return table_rows

    @classmethod
    def assemble_matching_report(cls, task_config: dict) -> dict:
        rows = cls.assemble_matching_table(task_config)
        if not rows:
            return {
                "summary": {"totalReturn": 0.0, "mdd": 0.0, "cagr": 0.0, "realizedProfitVal": 0.0},
                "detailedTxTable": [],
                "history": []
            }
            
        # history와 summary 추출
        history = []
        seen_dates = set()
        for r in rows:
            d = r.get("date")
            if d and d not in seen_dates:
                seen_dates.add(d)
                history.append({
                    "date": d,
                    "totalAsset": r["totalAsset"],
                    "cash": r["cash"],
                    "evalAmt": r["evalAmt"],
                    "close": r["close"],
                    "mdd": 0.0
                })
                
        # MDD 계산
        seed_amt = float(task_config.get("seed_amt", 10000.0))
        peak = seed_amt
        mdd = 0.0
        for h in history:
            if h["totalAsset"] > peak:
                peak = h["totalAsset"]
            dd = ((h["totalAsset"] - peak) / peak) * 100.0 if peak > 0 else 0.0
            h["mdd"] = float(abs(dd))
            if dd < mdd:
                mdd = dd
                
        final_asset = history[-1]["totalAsset"] if history else seed_amt
        total_return = ((final_asset - seed_amt) / seed_amt) * 100.0 if seed_amt > 0 else 0.0
        realized_profit_val = final_asset - seed_amt
        
        # CAGR 계산
        years = len(history) / 252.0
        cagr = ((final_asset / seed_amt) ** (1.0 / years) - 1.0) * 100.0 if years > 0 and seed_amt > 0 and final_asset > 0 else total_return
        
        # UI에서 기원하는 필드명 매핑을 맞춰줍니다.
        for r in rows:
            r["todayRealized"] = r.get("realizedNum", 0.0)
            if "profitAmt" not in r or r["profitAmt"] == "":
                r["profitAmt"] = "-"
                
        return {
            "ticker": task_config.get("ticker", "SOXL"),
            "startDate": history[0]["date"] if history else "",
            "endDate": history[-1]["date"] if history else "",
            "summary": {
                "totalReturn": float(total_return),
                "mdd": float(abs(mdd)),
                "cagr": float(cagr),
                "realizedProfitVal": float(realized_profit_val)
            },
            "history": history,
            "detailedTxTable": rows
        }
