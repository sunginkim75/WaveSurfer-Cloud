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
    def get_market_workday_after(cls, start_date_str: str, limit_days: int) -> str:
        """
        주말 및 미국 주식 시장 공휴일을 제외한 실제 영업일 기준으로 limit_days 뒤의 날짜를 계산합니다.
        """
        # 2025~2026년 고정 공휴일 및 대체휴일 목록
        holidays = {
            # 2025년
            "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
            "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
            # 2026년
            "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
            "2026-06-19", "2026-07-03", # 7/4 독립기념일 대체휴일
            "2026-09-07", "2026-11-26", "2026-12-25"
        }
        
        try:
            current_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            return start_date_str
            
        days_added = 0
        while days_added < limit_days:
            current_date += datetime.timedelta(days=1)
            date_str = current_date.strftime("%Y-%m-%d")
            # 주말 제외
            if current_date.weekday() >= 5:
                continue
            # 공휴일 제외
            if date_str in holidays:
                continue
            days_added += 1
            
        return current_date.strftime("%Y-%m-%d")

    @classmethod
    def get_market_workday_before(cls, start_date_str: str, limit_days: int) -> str:
        """
        주말 및 미국 주식 시장 공휴일을 제외한 실제 영업일 기준으로 limit_days 전의 날짜를 계산합니다.
        """
        holidays = {
            "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
            "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
            "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
            "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25"
        }
        try:
            current_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            return start_date_str
            
        days_subtracted = 0
        while days_subtracted < limit_days:
            current_date -= datetime.timedelta(days=1)
            date_str = current_date.strftime("%Y-%m-%d")
            if current_date.weekday() >= 5:
                continue
            if date_str in holidays:
                continue
            days_subtracted += 1
            
        return current_date.strftime("%Y-%m-%d")

    @classmethod
    def get_next_order_date(cls) -> str:
        """
        미국 동부시간(America/New_York) 기준:
        - 아직 정규장 마감(16:00 EDT) 전이면 당일 미국 영업일 날짜(예: 2026-07-21)를 반환.
        - 이미 정규장이 마감되었거나 주말/공휴일인 경우 다음 미국 영업일 날짜(예: 2026-07-22)를 반환합니다.
        """
        try:
            from zoneinfo import ZoneInfo
            ny_tz = ZoneInfo("America/New_York")
            now_ny = datetime.datetime.now(ny_tz)
            today_ny_str = now_ny.strftime("%Y-%m-%d")
            
            holidays = {
                "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
                "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
                "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
                "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25"
            }
            
            is_holiday_or_weekend = (now_ny.weekday() >= 5) or (today_ny_str in holidays)
            is_after_market_close = now_ny.hour >= 16
            
            if is_holiday_or_weekend or is_after_market_close:
                return cls.get_market_workday_after(today_ny_str, 1)
            return today_ny_str
        except Exception:
            now = datetime.datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            if now.weekday() >= 5 or now.hour >= 18:
                return cls.get_market_workday_after(today_str, 1)
            return today_str

    @classmethod
    def assemble_matching_table(cls, task_config: dict) -> List[Dict[str, Any]]:
        db = DBHandler()
        task_id = task_config.get("id")
        
        # 1. 실제 체결 데이터 로드
        batches_file = f"config/trade_batches_{task_id}.json"
        history_file = f"config/trade_history_{task_id}.json"
        
        batches = db.load_json(batches_file, default_data=[])
        history = db.load_json(history_file, default_data=[])
        
        # 2. 시작일 설정 (배치, 히스토리, 생성일 중 가장 과거 날짜 기준)
        all_dates = []
        created_at_str = task_config.get("created_at")
        if created_at_str:
            all_dates.append(created_at_str)
            
        for b in batches:
            if b.get("buyDate"): all_dates.append(b["buyDate"])
        for h in history:
            if h.get("buyDate"): all_dates.append(h["buyDate"])
            if h.get("date"): all_dates.append(h["date"])
            
        if all_dates:
            parsed_dates = []
            for dt in all_dates:
                try:
                    parsed_dates.append(datetime.datetime.strptime(dt.split(" ")[0].strip(), "%Y-%m-%d"))
                except:
                    pass
            if parsed_dates:
                # 첫 거래일 5일 전부터 시작하여 표의 마진 확보
                start_date = min(parsed_dates) - datetime.timedelta(days=5)
                start_date_str = start_date.strftime("%Y-%m-%d")
            else:
                start_date_str = datetime.date.today().strftime("%Y-%m-%d")
        else:
            start_date_str = datetime.date.today().strftime("%Y-%m-%d")
            
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
            # 해당 일봉 날짜 d가 속한 주의 월요일 구하기
            d_monday = d - datetime.timedelta(days=d.weekday())
            # 월요일 이전인 가장 최근의 QQQ 주간 RSI 행 매핑
            prev_qqq_rows = df_qqq[df_qqq.index < d_monday]
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
            
        # 미국 동부시간(NY) 기준 아직 장 마감(16:00 EDT) 전이면 오늘 장중 행은 과거 마감 일봉 목록에서 제거
        try:
            from zoneinfo import ZoneInfo
            ny_tz = ZoneInfo("America/New_York")
            now_ny = datetime.datetime.now(ny_tz)
            today_ny_str = now_ny.strftime("%Y-%m-%d")
            if sim_dates_data and sim_dates_data[-1]["date"] == today_ny_str and now_ny.hour < 16:
                sim_dates_data.pop()
        except Exception:
            pass

        # 5. 매수/매도 매칭을 위한 맵 구조화
        # buy_date별 실제 매수 및 매도 체결 데이터 결합
        # key: buy_date (매수일자) -> list of matching trades
        matching_trades = {}
        
        # A. 완료된 역사적 체결 (history) 매핑
        for h in history:
            if h.get("type") == "BUY":
                continue
            b_date = h.get("buyDate")
            if not b_date:
                # 만약 과거 데이터에 buyDate가 없으면 매도 날짜 당일로 임시 세팅
                b_date = h.get("date")
            if not b_date:
                continue
                
            if b_date not in matching_trades:
                matching_trades[b_date] = []
                
            h_realized = h.get("realized", h.get("realized_profit"))
            h_realized_val = float(h_realized) if h_realized is not None else 0.0
            h_buy_price = float(h.get("buyPrice") or 0.0)
            h_sell_price = float(h.get("sellPrice") or 0.0)
            # buyQty 우선 사용, 구버전 qty 폴백
            h_qty = int(h.get("buyQty", h.get("qty", 0)) or 0)
            h_sell_qty = int(h.get("sellQty", h_qty) or h_qty)
            h_sell_date = h.get("sellDate", h.get("date", ""))

            matching_trades[b_date].append({
                "is_sold": True,
                "buyPrice": h_buy_price,
                "buyQty": h_qty,
                "buyAmt": h_buy_price * h_qty,
                "buyMode": h.get("buyMode", "공세모드" if h_realized_val > 0.0 else "안전모드"),
                "sellDate": h_sell_date,
                "sellPrice": h_sell_price,
                "sellQty": f"{h_sell_qty}주",
                "sellAmt": h_sell_price * h_sell_qty,
                "realized_profit": h_realized_val
            })
            
        # B. 미실현 보유 중 배치 (batches) 매핑 (이미 history에 완료 기록이 있다면 중복 방지 필터링)
        for b in batches:
            b_date = b.get("buyDate")
            if not b_date:
                continue
                
            # 이미 history에 동일한 매수일자, 매수가, 매수수량을 갖는 완료 거래가 있다면 중복 제거
            is_already_sold = False
            if b_date in matching_trades:
                for t in matching_trades[b_date]:
                    if t.get("is_sold") and abs(t.get("buyPrice", 0.0) - b.get("buyPrice", 0.0)) < 0.01 and t.get("buyQty") == b.get("buyQty", b.get("qty", 0)):
                        is_already_sold = True
                        break
            
            if is_already_sold:
                continue
                
            if b_date not in matching_trades:
                matching_trades[b_date] = []
                
            # buyQty 필드를 우선 사용, 구버전 qty 필드도 폴백 지원
            b_qty = b.get("buyQty", b.get("qty", 0))
            matching_trades[b_date].append({
                "is_sold": False,
                "buyPrice": b.get("buyPrice", 0.0),
                "buyQty": b_qty,
                "buyAmt": b.get("buyPrice", 0.0) * b_qty,
                "buyMode": b.get("buyMode", "공세모드" if not b.get("isSafe", True) else "안전모드"),
                "cycleDays": b.get("cycleDays", 0),
                "sellDate": "보유중",
                "sellPrice": "-",
                "sellQty": "-",
                "sellAmt": "-",
                "realized_profit": 0.0
            })

        # C. 만약 실제 계좌 체결 기록이 전혀 없는 태스크(신규 생성 태스크 등)일 경우,
        # created_at (생성일) 이후의 날짜들에 대해 퀀트 가상 체결 시뮬레이션을 돌려 matching_trades를 채움
        seed_amt_init = float(task_config.get("seed_amt", 10000.0))
        split_cnt = int(task_config.get("split_count", 7))
        safe_buy = float(task_config.get("safe_buy_pct", 3.0))
        safe_sell = float(task_config.get("safe_sell_pct", 0.2))
        agg_buy = float(task_config.get("agg_buy_pct", 5.0))
        agg_sell = float(task_config.get("agg_sell_pct", 2.5))
        created_at_val = task_config.get("created_at")

        today_ny_str = datetime.date.today().strftime("%Y-%m-%d")
        try:
            from zoneinfo import ZoneInfo
            today_ny_str = datetime.datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        except Exception:
            pass

        has_past_trades = any(len(v) > 0 for dt, v in matching_trades.items() if dt < today_ny_str)
        if not has_past_trades:
            sim_cash = seed_amt_init
            sim_batches = []
            sim_mode = "안전모드"
            
            for i, today in enumerate(sim_dates_data):
                d_str = today["date"]
                c_price = today["close"]
                prev_item = sim_dates_data[i - 1] if i > 0 else None
                
                # 모드 판정
                l_rsi = today["rsi"]
                p_rsi = today["prev_rsi"]
                if (p_rsi > 65 and p_rsi > l_rsi) or (40 < p_rsi < 50 and p_rsi > l_rsi) or (l_rsi < 50 and p_rsi > 50):
                    sim_mode = "안전모드"
                elif (p_rsi < 35 and p_rsi < l_rsi) or (50 < p_rsi < 60 and p_rsi < l_rsi) or (l_rsi > 50 and p_rsi < 50):
                    sim_mode = "공세모드"
                    
                if created_at_val and d_str < created_at_val:
                    continue
                    
                # 1) 가상 매도 체크
                sells_to_remove = []
                for b_idx, sb in enumerate(sim_batches):
                    sb["cycleDays"] += 1
                    t_sell_target = sb["buyPrice"] * (1 + (agg_sell/100 if sb["buyMode"] == "공세모드" else safe_sell/100))
                    lim_days = 7 if sb["buyMode"] == "공세모드" else 30
                    
                    if sb["cycleDays"] >= 1 and c_price >= t_sell_target:
                        sells_to_remove.append((b_idx, c_price, "LOC 매도"))
                    elif sb["cycleDays"] >= lim_days:
                        sells_to_remove.append((b_idx, c_price, "MOC 청산"))
                        
                for b_idx, s_price, s_type in reversed(sells_to_remove):
                    sb = sim_batches.pop(b_idx)
                    b_d = sb["buyDate"]
                    if b_d not in matching_trades:
                        matching_trades[b_d] = []
                        
                    # 기존 보유중 데이터 제거 후 체결 완료로 교체
                    matching_trades[b_d] = [t for t in matching_trades[b_d] if t.get("buyPrice") != sb["buyPrice"]]
                    realized_p = (s_price - sb["buyPrice"]) * sb["qty"]
                    matching_trades[b_d].append({
                        "is_sold": True,
                        "buyPrice": sb["buyPrice"],
                        "buyQty": sb["qty"],
                        "buyAmt": sb["buyPrice"] * sb["qty"],
                        "buyMode": sb["buyMode"],
                        "sellDate": d_str,
                        "sellPrice": s_price,
                        "sellQty": f"{sb['qty']}주",
                        "sellAmt": s_price * sb["qty"],
                        "realized_profit": realized_p
                    })
                    
                # 2) 가상 매수 체크
                base_p = prev_item["close"] if prev_item else c_price
                t_buy = base_p * (1 + (agg_buy/100 if sim_mode == "공세모드" else safe_buy/100))
                b_limit_amt = sim_cash / split_cnt
                b_qty = int(b_limit_amt // t_buy) if t_buy > 0 else 0
                
                if b_qty > 0 and c_price <= t_buy:
                    # LOC 체결가는 매수목표한도가 아니라 당일 실제 체결 종가(c_price)
                    actual_buy_price = c_price
                    new_sb = {
                        "buyPrice": actual_buy_price,
                        "qty": b_qty,
                        "cycleDays": 0,
                        "buyMode": sim_mode,
                        "buyDate": d_str
                    }
                    sim_batches.append(new_sb)
                    
                    if d_str not in matching_trades:
                        matching_trades[d_str] = []
                    matching_trades[d_str].append({
                        "is_sold": False,
                        "buyPrice": actual_buy_price,
                        "buyQty": b_qty,
                        "buyAmt": actual_buy_price * b_qty,
                        "buyMode": sim_mode,
                        "cycleDays": 0,
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
        # 매도 완료된 거래들을 매도일 순서로 정렬하여 시간 순서에 따른 누적 실현손익 연산
        completed_trades = []
        for buy_date, trades in matching_trades.items():
            for t in trades:
                if t.get("is_sold") and t.get("sellDate"):
                    completed_trades.append(t)
        
        completed_trades.sort(key=lambda x: x["sellDate"])
        running_accum_profit = 0.0
        for t in completed_trades:
            running_accum_profit += t["realized_profit"]
            t["accumProfitVal"] = running_accum_profit
            
        # 수수료 상수 (구글 시트 대조용으로 0.0 설정)
        commission_rate = 0.0
        sec_fee_rate = 0.0
        
        table_rows = []
        accum_profit = 0.0
        
        # 보유 배치들 추적용 (MOC 매도일 계산용)
        # 매 영업일 인덱스를 구하기 위해 날짜 목록 추출
        trade_dates_list = [d["date"] for d in sim_dates_data]
        
        # 봇의 모드 전환 룰 적용을 위한 전역 변수
        active_mode = "안전모드"
        
        # 실제 거래 일수 (복리 주기 10영업일 카운팅용)
        active_trade_day_count = 0
        created_at_str = task_config.get("created_at")
        
        for i, today in enumerate(sim_dates_data):
            date_str = today["date"]
            today_close = today["close"]
            prev = sim_dates_data[i - 1] if i > 0 else None
            
            # (0) 시드 증액 발생 시 복리 기준 자금액에도 가산 처리
            day_seed_add = 0.0
            for h in history:
                if h.get("date") == date_str and h.get("type") == "SEED_ADD":
                    day_seed_add += float(h.get("amount") or 0.0)
            if day_seed_add > 0.0:
                last_compounding_cash += day_seed_add
                
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
                    
            latest_rsi = today["rsi"]        # 1주 전 주봉 RSI
            prev_rsi = today["prev_rsi"]      # 2주 전 주봉 RSI
            
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
                active_mode = "안전모드"
            elif is_aggressive_condition:
                active_mode = "공세모드"
            # 조건 불만족 시 이전 active_mode 유지 (OFFSET 상속)
                
            # (3) 당일 실현손익 합산 및 누적
            today_realized_profit = 0.0
            # 오늘 날짜로 매도 완료된 모든 거래 찾기
            today_sells = []
            for dt, trades in matching_trades.items():
                for t in trades:
                    if t.get("is_sold") and t.get("sellDate") == date_str:
                        today_sells.append(t)
                        today_realized_profit += t.get("realized_profit", 0.0)
            
            accum_profit += today_realized_profit
                        
            # (5) 매수예정액 계산 (복리 반영 전의 자금 기준으로 당일 매수예정액 연산)
            buy_limit_amt = last_compounding_cash / split_count
            
            # (4) 10거래일 단위 복리 주기 반영 (실제 실현손익 흐름에 맞춰 복리 가산은 매수예정액 연산 뒤에 수행)
            compounding_amt_val = 0.0
            is_compounding_day = False
            
            # 실제 거래일수가 10/28(최초 생성일) 이상인 날부터 카운팅 누적
            if created_at_str and date_str >= created_at_str:
                active_trade_day_count += 1
                
            # 이전 10일간의 당일실현손익 계산 (인덱스 i가 아닌 active_trade_day_count 기준)
            if active_trade_day_count > 0 and active_trade_day_count % update_period == 0:
                # 오늘(date_str) 기준으로 지난 10영업일 동안 실제로 매도 완료 정산된 거래들만 손익 합산
                start_window_date = cls.get_market_workday_before(date_str, update_period)
                bfs = 0.0
                for t in completed_trades:
                    if start_window_date < t["sellDate"] <= date_str:
                        bfs += t["realized_profit"]
                
                if bfs < 0:
                    compounding_amt_val = bfs * (compounding_loss_rate / 100)
                else:
                    compounding_amt_val = bfs * (compounding_profit_rate / 100)
                    
                last_compounding_cash += compounding_amt_val
                last_compounding_cash = max(1000.0, last_compounding_cash)
                is_compounding_day = True
            
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
                    "sellFee": "",
                    "realized": "-",
                    "realizedNum": 0.0,
                    "profitRate": "",
                    "accumProfit": accum_profit if accum_profit != 0.0 else "-",
                    "isCompounding": "TRUE" if is_compounding_day else "FALSE",
                    "compoundingAmt": compounding_amt_val if is_compounding_day else "",
                    "updatedCompoundingCash": last_compounding_cash if is_compounding_day else ""
                }
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
                    moc_date_str = cls.get_market_workday_after(date_str, limit_days)
                        
                    # MOC 청산 여부
                    is_moc_liquidated = False
                    if trade.get("is_sold") and "MOC" in trade.get("sellDate", ""):
                        is_moc_liquidated = True
                    elif not trade.get("is_sold") and trade.get("cycleDays", 0) >= limit_days:
                        is_moc_liquidated = True
                        
                    # 해당 매수 배치가 매도 완료되었다면, 이 매수일 행의 실현손익에 기입
                    trade_realized_profit = trade["realized_profit"] if trade.get("is_sold") else 0.0
                    trade_realized_str = trade["realized_profit"] if trade.get("is_sold") else "-"
                    
                    # 매도 수수료 및 손익률 계산
                    s_amt = trade.get("sellAmt", "-")
                    try:
                        s_amt_val = float(s_amt) if s_amt != "-" and s_amt != "" else 0.0
                    except:
                        s_amt_val = 0.0
                    sell_fee = s_amt_val * (commission_rate + sec_fee_rate) if s_amt_val > 0.0 else ""
                    
                    p_rate = (trade_realized_profit / trade["buyAmt"]) * 100.0 if trade["buyAmt"] > 0.0 and trade.get("is_sold") else ""
                    
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
                        "sellFee": sell_fee,
                        "realized": trade_realized_str,
                        "realizedNum": trade_realized_profit,
                        "profitRate": p_rate,
                        "accumProfit": accum_profit if accum_profit != 0.0 else "-",
                        "isCompounding": "TRUE" if (is_compounding_day and idx == 0) else "FALSE",
                        "compoundingAmt": compounding_amt_val if (is_compounding_day and idx == 0) else "",
                        "updatedCompoundingCash": last_compounding_cash if (is_compounding_day and idx == 0) else ""
                    }
                    table_rows.append(row_item)
                    
        # 7. 예수금 잔액(cash) 및 총자산 추적 반영 (최종 가공)
        # 매 영업일 장마감 기준으로 실제 정산이 끝난 예수금 및 총자산 계산
        # 초기 예수금은 last_compounding_cash 또는 seed_amt 기준
        init_cash = float(task_config.get("last_compounding_cash", seed_amt))
        running_cash = init_cash
        current_date = None
        current_close = 0.0
        peak_asset = init_cash
        
        # 날짜별로 매입/매도가 발생할 때의 정산 현금 갱신
        for r in table_rows:
            if r.get("date") != "":
                current_date = r["date"]
                current_close = r["close"]
            
            # 매 영업일(current_date) 기준으로 실제 예수금 계산
            # current_date까지 일어난 매수/매도를 누적
            day_cash = init_cash
            if current_date:
                for buy_date, trades in matching_trades.items():
                    for t in trades:
                        # 매수일이 오늘 이하이면 매수대금 및 수수료 차감
                        if buy_date <= current_date:
                            day_cash -= t["buyAmt"]
                            fee = t["buyAmt"] * commission_rate
                            day_cash -= fee
                        # 매도일이 오늘 이하이면 매도대금 가산 및 수수료 차감
                        if t.get("is_sold") and t["sellDate"] <= current_date:
                            day_cash += t["sellAmt"]
                            sell_fee = t["sellAmt"] * (commission_rate + sec_fee_rate)
                            day_cash -= sell_fee
                            
                # 시드증액 및 입출금 히스토리 레코드 누적 가산
                for h in history:
                    h_type = h.get("type")
                    h_date = h.get("date")
                    if h_date and h_date <= current_date:
                        if h_type in ("SEED_ADD", "DEPOSIT_WITHDRAW"):
                            day_cash += float(h.get("amount") or 0.0)
            
            r["cash"] = day_cash
            
            # 당일 보유 수량 계산 (장마감 기준)
            qty_held = 0
            if current_date:
                for buy_date, trades in matching_trades.items():
                    if buy_date <= current_date:
                        for t in trades:
                            if not t["is_sold"] or t["sellDate"] > current_date:
                                qty_held += t["buyQty"]
            
            # 누적손익 매핑 (해당 행에 매수 거래가 존재한다면 그 거래의 누적 실현손익을 표기)
            # 매수 거래가 복수 개일 수도 있으므로 최신 완료 건 기준
            has_trade_row = False
            for buy_date, trades in matching_trades.items():
                if buy_date == r.get("date"):
                    sold_trades = [t for t in trades if t.get("is_sold")]
                    if sold_trades:
                        # 매도일 기준으로 정렬하여 가장 최신 누적손익 기입
                        sold_trades.sort(key=lambda x: x["sellDate"])
                        r["accumProfit"] = sold_trades[-1]["accumProfitVal"]
                        has_trade_row = True
                        break
            
            if not has_trade_row:
                # 거래가 없는 행은 오늘 이전의 가장 최신 누적 실현손익으로 표기
                past_realized = []
                for t in completed_trades:
                    if t["sellDate"] <= current_date:
                        past_realized.append(t)
                if past_realized:
                    r["accumProfit"] = past_realized[-1]["accumProfitVal"]
                else:
                    r["accumProfit"] = 0.0

            eval_amt = qty_held * current_close
            total_asset = day_cash + eval_amt
            
            r["heldQty"] = qty_held
            r["evalAmt"] = eval_amt
            r["totalAsset"] = total_asset
            
            # 수익률 계산 (시작 자금 init_cash 대비 총자산 변동률)
            r["totalProfitRate"] = ((total_asset - init_cash) / init_cash) * 100.0 if init_cash > 0 else 0.0
            
            # DD 계산
            peak_asset = max(peak_asset, total_asset)
            r["drawdown"] = ((total_asset - peak_asset) / peak_asset) * 100.0 if peak_asset > 0 else 0.0
            
            # 구글 시트 추가 컬럼들 기본값 및 실제 이벤트 매핑
            day_seed_add = 0.0
            day_dep_with = 0.0
            for h in history:
                if h.get("date") == current_date:
                    if h.get("type") == "SEED_ADD":
                        day_seed_add += float(h.get("amount") or 0.0)
                    elif h.get("type") == "DEPOSIT_WITHDRAW":
                        day_dep_with += float(h.get("amount") or 0.0)
            
            r["seedAdd"] = day_seed_add if day_seed_add > 0.0 else ""
            r["depositWithdraw"] = day_dep_with if day_dep_with != 0.0 else ""
            r["expectedCommission"] = ""
            r["actualCommission"] = ""
            r["savedCommission"] = ""
            
        # 8. 다음 영업일의 예약 주문(예측) 행 추가
        next_date_str = cls.get_next_order_date()
        existing_dates = {r.get("date") for r in table_rows if r.get("date")}
        if next_date_str not in existing_dates:
            try:
                from core.strategies.strategy_factory import StrategyFactory
                strat = StrategyFactory.get_strategy(task_config)
                next_orders = strat.calculate_orders()
            except Exception as e:
                logger.error(f"다음 영업일 주문 계산 실패: {e}")
                next_orders = []
                
            next_buy_limit_amt = last_compounding_cash / split_count
            
            # 신규 매수 예정 주문(BUY) 찾기 (구버전 type 및 신버전 action 모두 호환)
            buy_order = next((o for o in next_orders if o.get("action") == "BUY" or o.get("type") == "BUY"), None)
            target_buy_val = buy_order.get("price", "") if buy_order else ""
            target_qty_val = buy_order.get("qty", "") if buy_order else ""
            
            row_item = {
                "date": next_date_str,
                "close": "",
                "mode": active_mode,
                "change": "",
                "buyLimitAmt": next_buy_limit_amt,
                "targetBuy": target_buy_val,
                "targetQty": target_qty_val,
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
                "sellFee": "",
                "realized": "-",
                "realizedNum": 0.0,
                "profitRate": "",
                "accumProfit": accum_profit if accum_profit != 0.0 else "-",
                "isCompounding": "FALSE",
                "compoundingAmt": "",
                "updatedCompoundingCash": "",
                "seedAdd": "",
                "depositWithdraw": "",
                "cash": "",
                "heldQty": "",
                "evalAmt": "",
                "totalAsset": "",
                "totalProfitRate": "",
                "drawdown": "",
                "expectedCommission": "",
                "actualCommission": "",
                "savedCommission": ""
            }
            
            if buy_order:
                row_item["targetBuy"] = float(buy_order.get("price", 0.0))
                row_item["targetQty"] = int(buy_order.get("qty", 0))
                row_item["mode"] = buy_order.get("mode", active_mode)
                
            table_rows.append(row_item)
            
        # 9. 실제 거래 시작일(created_at) 이전의 마진용 행들은 화면 대조표 노출에서 제외
        if created_at_str:
            # yfinance 상의 마진(5일전)으로 트렌드는 정확히 계산되었으므로, 노출용만 필터링합니다.
            return [r for r in table_rows if r.get("date") and r["date"] >= created_at_str]
            
        return table_rows

    @classmethod
    def assemble_matching_report_ib(cls, task_config: dict) -> dict:
        """
        무한매수(INFINITE_BUY) 전용 매매 대조 보고서 조립 (영업일 기준 일일 타임라인 누적 원장)
        """
        db = DBHandler()
        task_id = task_config.get("id")
        seed_amt = float(task_config.get("seed_amt", 10000.0))
        created_at_str = task_config.get("created_at") or "2026-07-11"
        
        batches_file = f"config/trade_batches_{task_id}.json"
        history_file = f"config/trade_history_{task_id}.json"
        
        batches = db.load_json(batches_file, default_data=[])
        history = db.load_json(history_file, default_data=[])
        
        # 1. 시작일 설정 (생성일의 10일 전으로 설정하여 충분한 백테스트 마진 확보)
        try:
            start_dt = datetime.datetime.strptime(created_at_str, "%Y-%m-%d")
            start_date_str = (start_dt - datetime.timedelta(days=10)).strftime("%Y-%m-%d")
        except:
            start_date_str = "2026-07-01"
            
        end_date_str = datetime.date.today().strftime("%Y-%m-%d")
        ticker = task_config.get("ticker", "TQQQ")
        
        # 2. yfinance 데이터 로드
        try:
            df_target, _ = Backtester.get_market_data(ticker, start_date_str, end_date_str)
        except Exception as e:
            logger.error(f"무한매수 시장 데이터 다운로드 실패: {e}")
            return {
                "summary": {"totalReturn": 0.0, "mdd": 0.0, "cagr": 0.0, "realizedProfitVal": 0.0, "totalAsset": seed_amt},
                "detailedTxTable": [],
                "history": []
            }
            
        # 3. 체결 데이터 병합 및 날짜별 인덱싱
        tx_by_date = {}
        
        # (A) 역사적 체결 내역
        for h in history:
            d = h.get("date", "").split(" ")[0].strip()
            if not d:
                continue
            tx_type = h.get("type", "SELL")
            price = float(h.get("sellPrice", 0.0)) if tx_type == "SELL" else float(h.get("buyPrice", 0.0))
            qty = int(h.get("qty", 0))
            realized = float(h.get("realized_profit", 0.0))
            
            tx_by_date.setdefault(d, []).append({
                "type": tx_type,
                "price": price,
                "qty": qty,
                "realized": realized
            })
            
        # (B) 현재 진행중인 활성 보유 배치 (매수)
        for b in batches:
            d = b.get("buyDate", "").split(" ")[0].strip()
            if not d:
                continue
            price = float(b.get("buyPrice", 0.0))
            qty = int(b.get("qty", 0))
            
            tx_by_date.setdefault(d, []).append({
                "type": "BUY",
                "price": price,
                "qty": qty,
                "realized": 0.0
            })
            
        # 4. 영업일별 순차 누적 연산
        running_cash = seed_amt
        running_qty = 0
        total_cost = 0.0
        buy_unit = seed_amt / float(task_config.get("split_count", 40))
        
        detailed_table = []
        chart_history = []
        
        # yfinance 영업일 목록 루프
        for d in df_target.index:
            date_str = d.strftime("%Y-%m-%d")
            close_price = float(df_target.loc[d, 'Close'])
            
            day_txs = tx_by_date.get(date_str, [])
            
            # 당일 체결 기록이 있다면 먼저 잔고 반영
            day_type = "-"
            day_price = "-"
            day_qty = "-"
            day_amount = "-"
            day_realized = 0.0
            
            if day_txs:
                buy_amount = 0.0
                sell_amount = 0.0
                total_realized = 0.0
                
                for tx in day_txs:
                    tx_type = tx["type"]
                    price = tx["price"]
                    qty = tx["qty"]
                    amount = price * qty
                    
                    if tx_type == "BUY":
                        running_cash -= amount
                        running_qty += qty
                        total_cost += amount
                        buy_amount += amount
                        day_type = "BUY"
                        day_price = price
                        day_qty = qty
                    else:  # SELL
                        running_cash += amount
                        running_qty -= qty
                        if running_qty < 0:
                            running_qty = 0
                        total_cost = max(0.0, total_cost - amount)
                        total_realized += tx["realized"]
                        day_type = "SELL"
                        day_price = price
                        day_qty = qty
                        
                day_amount = buy_amount if day_type == "BUY" else (sell_amount if sell_amount > 0 else (day_price * day_qty if isinstance(day_qty, int) else "-"))
                day_realized = total_realized
                
            # 실시간 상태 계산
            t_val = round(total_cost / buy_unit, 2) if buy_unit > 0 else 0.0
            eval_amt = running_qty * close_price
            total_asset = running_cash + eval_amt
            
            # 생성일(created_at) 이후 영업일인 경우에만 결과에 적재
            if date_str >= created_at_str:
                row = {
                    "date": date_str,
                    "type": day_type,
                    "price": day_price,
                    "qty": day_qty,
                    "amount": day_amount,
                    "total_cost": total_cost,
                    "t_value": t_val,
                    "realized_profit": day_realized,
                    "cash": running_cash,
                    "eval_amt": eval_amt,
                    "totalAsset": total_asset
                }
                detailed_table.append(row)
                
                chart_history.append({
                    "date": date_str,
                    "totalAsset": total_asset,
                    "cash": running_cash,
                    "evalAmt": eval_amt,
                    "close": close_price,
                    "mdd": 0.0
                })
                
        # 5. 예약 주문(주문 예정) 미래 영업일 행 추가
        if chart_history:
            last_date_str = chart_history[-1]["date"]
            next_date_str = cls.get_market_workday_after(last_date_str, 1)
            t_value_current = round(total_cost / buy_unit, 2) if buy_unit > 0 else 0.0
            
            row_next = {
                "date": next_date_str,
                "type": "-",
                "price": "-",
                "qty": "-",
                "amount": "-",
                "total_cost": total_cost,
                "t_value": t_value_current,
                "totalAsset": running_cash + (running_qty * float(df_target.iloc[-1]['Close']) if not df_target.empty else 0.0)
            }
            detailed_table.append(row_next)
        else:
            # 주말 생성 등으로 영업일 데이터가 아예 누적되지 않은 경우 초기 예약 대기 행 추가
            next_date_str = cls.get_market_workday_after(created_at_str, 0)
            t_value_current = round(total_cost / buy_unit, 2) if buy_unit > 0 else 0.0
            
            row_next = {
                "date": next_date_str,
                "type": "-",
                "price": "-",
                "qty": "-",
                "amount": "-",
                "total_cost": total_cost,
                "t_value": t_value_current,
                "realized_profit": 0.0,
                "cash": running_cash,
                "eval_amt": running_qty * float(df_target.iloc[-1]['Close']) if not df_target.empty else 0.0,
                "totalAsset": running_cash + (running_qty * float(df_target.iloc[-1]['Close']) if not df_target.empty else 0.0)
            }
            detailed_table.append(row_next)
            
        # 6. MDD 및 수익률 요약 산출
        # 누적 실현손익 및 누적 실현수익률 산출 (0.91% 등)
        realized_profit_val = sum(tx.get("realized", 0.0) for day_tx in tx_by_date.values() for tx in day_tx)
        realized_profit_rate = (realized_profit_val / seed_amt) * 100.0 if seed_amt > 0 else 0.0

        peak = seed_amt
        mdd = 0.0
        for h in chart_history:
            if h["totalAsset"] > peak:
                peak = h["totalAsset"]
            dd = ((h["totalAsset"] - peak) / peak) * 100.0 if peak > 0 else 0.0
            h["mdd"] = float(abs(dd))
            if dd < mdd:
                mdd = dd
                
        final_asset = chart_history[-1]["totalAsset"] if chart_history else seed_amt
        total_return = ((final_asset - seed_amt) / seed_amt) * 100.0 if seed_amt > 0 else 0.0
        realized_profit_val = sum(tx["realized_profit"] for tx in raw_txs if tx["type"] == "SELL") if 'raw_txs' in locals() else 0.0
        
        return {
            "ticker": ticker,
            "startDate": chart_history[0]["date"] if chart_history else "",
            "endDate": chart_history[-1]["date"] if chart_history else "",
            "summary": {
                "totalReturn": float(total_return),
                "mdd": float(abs(mdd)),
                "cagr": float(total_return),
                "realizedProfitVal": float(realized_profit_val),
                "totalAsset": float(final_asset)
            },
            "history": chart_history,
            "detailedTxTable": detailed_table
        }

    @classmethod
    def assemble_matching_report(cls, task_config: dict) -> dict:
        strategy = task_config.get("strategy")
        if strategy == "INFINITE_BUY":
            return cls.assemble_matching_report_ib(task_config)
            
        rows = cls.assemble_matching_table(task_config)
        if not rows:
            return {
                "summary": {"totalReturn": 0.0, "mdd": 0.0, "cagr": 0.0, "realizedProfitVal": 0.0, "totalAsset": 0.0},
                "detailedTxTable": [],
                "history": []
            }
            
        # history와 summary 추출 (close 및 totalAsset이 존재하는 마감 영업일만 history에 포함)
        history = []
        seen_dates = set()
        for r in rows:
            d = r.get("date")
            if d and d not in seen_dates and r.get("close") != "" and r.get("totalAsset") != "":
                seen_dates.add(d)
                history.append({
                    "date": d,
                    "totalAsset": float(r["totalAsset"]),
                    "cash": float(r["cash"]) if r.get("cash") != "" else 0.0,
                    "evalAmt": float(r["evalAmt"]) if r.get("evalAmt") != "" else 0.0,
                    "close": float(r["close"]),
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
        # 누적 실현손익 및 누적 실현수익률 산출 (0.91% 등)
        last_closed_row = next((r for r in reversed(rows) if r.get("close") != ""), rows[-1])
        try:
            realized_profit_val = float(last_closed_row.get("accumProfit", 0.0))
        except (ValueError, TypeError):
            realized_profit_val = 0.0
            
        realized_profit_rate = (realized_profit_val / seed_amt) * 100.0 if seed_amt > 0 else 0.0

        final_asset = history[-1]["totalAsset"] if history else seed_amt
        total_return = ((final_asset - seed_amt) / seed_amt) * 100.0 if seed_amt > 0 else 0.0
        
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
                "realizedProfitVal": float(realized_profit_val),
                "realizedProfitRate": float(realized_profit_rate),
                "totalAsset": float(final_asset)
            },
            "history": history,
            "detailedTxTable": rows
        }

    @classmethod
    def edit_transaction(cls, task_config: dict, edit_data: dict) -> bool:
        """
        수동 모드용 실제 거래 기록(batches/history) 직접 편집 및 저장
        """
        import uuid
        db = DBHandler()
        task_id = task_config.get("id")
        batches_file = f"config/trade_batches_{task_id}.json"
        history_file = f"config/trade_history_{task_id}.json"
        
        batches = db.load_json(batches_file, default_data=[])
        history = db.load_json(history_file, default_data=[])
        
        target_date = edit_data.get("date") # 매수일자 기준
        if not target_date:
            return False
            
        buy_price_raw = edit_data.get("buyPrice")
        buy_qty_raw = edit_data.get("buyQty")
        sell_price_raw = edit_data.get("sellPrice")
        sell_qty_raw = edit_data.get("sellQty")
        sell_date = edit_data.get("sellDate")
        mode = edit_data.get("mode", "안전모드")
        
        # 숫자 변환 유틸리티
        def to_float(val):
            if val is None or val == "" or val == "-": return 0.0
            try: return float(val)
            except: return 0.0
            
        def to_int(val):
            if val is None or val == "" or val == "-": return 0
            try: return int(float(val))
            except: return 0
            
        b_price = to_float(buy_price_raw)
        b_qty = to_int(buy_qty_raw)
        s_price = to_float(sell_price_raw)
        s_qty = to_int(sell_qty_raw)
        
        # 1. 삭제 모드 (매수 수량이나 단가가 0 이하인 경우 해당 날짜 거래 삭제)
        if b_price <= 0.0 or b_qty <= 0:
            batches = [b for b in batches if b.get("buyDate") != target_date]
            history = [h for h in history if h.get("buyDate") != target_date and h.get("date") != target_date]
            db.save_json(batches_file, batches)
            db.save_json(history_file, history)
            return True
            
        # 2. 매도 체결 모드 (매도단가와 매도수량이 존재하는 경우)
        if s_price > 0.0 and s_qty > 0:
            # batches에서 삭제
            batches = [b for b in batches if b.get("buyDate") != target_date]
            
            # history에서 갱신/추가
            existing_tx = next((h for h in history if h.get("buyDate") == target_date or (h.get("date") == target_date and h.get("type") == "SELL")), None)
            realized = (s_price - b_price) * s_qty
            
            if existing_tx:
                existing_tx["buyPrice"] = b_price
                existing_tx["qty"] = s_qty
                existing_tx["sellPrice"] = s_price
                existing_tx["date"] = sell_date or target_date
                existing_tx["buyMode"] = mode
                existing_tx["realized_profit"] = realized
            else:
                history.append({
                    "id": f"tx_{str(uuid.uuid4())[:8]}",
                    "date": sell_date or target_date,
                    "type": "SELL",
                    "buyDate": target_date,
                    "buyPrice": b_price,
                    "sellPrice": s_price,
                    "qty": s_qty,
                    "buyMode": mode,
                    "realized_profit": realized
                })
        else:
            # 3. 매수 보유 모드 (매수만 일어난 경우)
            # history에 혹시라도 남아있던 매도완료 내역이 있으면 삭제
            history = [h for h in history if h.get("buyDate") != target_date]
            
            # batches에서 갱신/추가
            existing_batch = next((b for b in batches if b.get("buyDate") == target_date), None)
            if existing_batch:
                existing_batch["buyPrice"] = b_price
                existing_batch["qty"] = b_qty
                existing_batch["buyMode"] = mode
            else:
                batches.append({
                    "id": f"bt_{str(uuid.uuid4())[:8]}",
                    "buyDate": target_date,
                    "buyPrice": b_price,
                    "qty": b_qty,
                    "buyMode": mode,
                    "cycleDays": 0
                })
                
        db.save_json(batches_file, batches)
        db.save_json(history_file, history)
        return True

