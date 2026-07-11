import logging
import datetime
import uuid
from core.strategies.strategy_factory import BaseStrategy, StrategyFactory
from utils.db_handler import DBHandler
from utils.market_data import MarketDataManager

logger = logging.getLogger(__name__)

class SurferBatchStrategy(BaseStrategy):
    """
    WaveSurfer-Cloud의 핵심 복리 퀀트 매매법 (Surfer Batch)
    - 독립적인 매수 배치 관리
    - LOC 목표가 매수/매도 및 MOC 강제 청산
    - 10일 주기 복리 시스템
    """
    def __init__(self, task_config: dict):
        super().__init__(task_config)
        self.db = DBHandler()
        self.market_data = MarketDataManager()
        
        # 파일 경로 설정 (계좌/태스크별 독립 관리)
        self.batches_file = f"config/trade_batches_{self.task_id}.json"
        self.history_file = f"config/trade_history_{self.task_id}.json"
        
        # 기본 파라미터 로드
        self.safe_buy_pct = self.task_config.get("safe_buy_pct", 2.5)
        self.safe_sell_pct = self.task_config.get("safe_sell_pct", 0.5)
        self.agg_buy_pct = self.task_config.get("agg_buy_pct", 4.0)
        self.agg_sell_pct = self.task_config.get("agg_sell_pct", 2.0)
        
        self.split_count = self.task_config.get("split_count", 7)
        self.compounding_profit_rate = self.task_config.get("compounding_profit_rate", 80)
        self.compounding_loss_rate = self.task_config.get("compounding_loss_rate", 30)
        
        self.base_seed = self.task_config.get("seed_amt", 10000)
        self.last_compounding_cash = self.task_config.get("last_compounding_cash", self.base_seed)
        self.ticker = self.task_config.get("ticker", "SOXL")
        self.rsi_ticker = self.task_config.get("rsi_ticker", "QQQ")
        
    def calculate_orders(self) -> list:
        """
        오늘 장마감 전 전송해야 할 LOC/MOC 주문 목록 반환
        """
        # 최신 데이터 가져오기
        latest_close = self.market_data.get_latest_close(self.ticker)
        weekly_rsi_data = self.market_data.get_weekly_rsi_data(self.rsi_ticker, period=14)
        
        if latest_close is None or weekly_rsi_data is None:
            logger.error("시장 데이터를 불러오지 못해 주문을 계산할 수 없습니다.")
            return []
            
        prev_rsi, latest_rsi, trend = weekly_rsi_data
        
        batches = self.db.load_json(self.batches_file, default_data=[])
        
        # 1. 이전 모드 판별 (가장 최근 배치의 모드 기준, 없으면 안전모드)
        current_mode = "안전모드"
        if batches:
            current_mode = batches[-1].get("buyMode", "안전모드")
            
        # 2. 공세/안전 모드 전환 판별 (제공된 표 기준)
        if trend == "하락":
            if latest_rsi > 65:
                current_mode = "안전모드"
            elif 40 < latest_rsi < 50:
                current_mode = "안전모드"
            elif prev_rsi >= 50 > latest_rsi:  # RSI가 50 밑으로 하락
                current_mode = "안전모드"
        elif trend == "상승":
            if prev_rsi <= 50 < latest_rsi:  # RSI가 50 위로 상승
                current_mode = "공세모드"
            elif 50 < latest_rsi < 60:
                current_mode = "공세모드"
            elif latest_rsi < 35:
                current_mode = "공세모드"
                
        orders = []
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        
        # 2. 보유 배치 매도 주문 계산 (각 배치마다 독립적)
        for batch in batches:
            buy_price = batch.get("buyPrice", 0)
            qty = batch.get("qty", 0)
            cycle_days = batch.get("cycleDays", 0)
            batch_mode = batch.get("buyMode", "안전모드")
            buy_date = batch.get("buyDate", "")
            
            # 당일 매수한 배치는 매도 주문 전송 제외
            if buy_date == today_str:
                continue
                
            # MOC 청산 기한 설정 (공세 7일, 안전 30일)
            limit_days = 7 if batch_mode == "공세모드" else 30
            
            # 조건 B: MOC 청산 (만기일 경과)
            if cycle_days >= limit_days:
                orders.append({
                    "type": "SELL",
                    "order_type": "MOC",
                    "qty": qty,
                    "price": 0, # MOC는 지정가 불필요
                    "batch_id": batch.get("id"),
                    "reason": "MOC 청산 (만기 경과)"
                })
                continue
                
            # 조건 A: LOC 매도 (타겟가 도달)
            if batch_mode == "공세모드":
                target_sell = buy_price * (1 + (self.agg_sell_pct / 100))
            else:
                target_sell = buy_price * (1 + (self.safe_sell_pct / 100))
            
            # 지정된 target_sell 가격으로 LOC 매도 주문 예약
            orders.append({
                "type": "SELL",
                "order_type": "LOC",
                "qty": qty,
                "price": round(target_sell, 2),
                "batch_id": batch.get("id"),
                "reason": f"LOC 매도 대기 (목표가 {target_sell:.2f})"
            })
            
        # 3. LOC 신규 매수 주문 계산
        if current_mode == "공세모드":
            target_buy = latest_close * (1 + (self.agg_buy_pct / 100))
        else:
            target_buy = latest_close * (1 + (self.safe_buy_pct / 100))
            
        # 1회 분할 매수 수량 계산
        buy_limit_amt = self.last_compounding_cash / self.split_count
        buy_qty = int(buy_limit_amt // target_buy)
        
        if buy_qty > 0:
            orders.append({
                "type": "BUY",
                "order_type": "LOC",
                "qty": buy_qty,
                "price": round(target_buy, 2),
                "reason": f"LOC 신규 매수 ({current_mode})",
                "mode": current_mode
            })
            
        return orders

    def on_trade_contracted(self, contract_data: dict):
        """
        체결 내역을 바탕으로 Batch 추가/삭제 및 히스토리 업데이트
        """
        batches = self.db.load_json(self.batches_file, default_data=[])
        history = self.db.load_json(self.history_file, default_data=[])
        
        trade_type = contract_data.get("type")
        qty = contract_data.get("qty", 0)
        price = contract_data.get("price", 0.0)
        date_str = contract_data.get("date", datetime.date.today().strftime("%Y-%m-%d"))
        
        if trade_type == "BUY":
            new_batch = {
                "id": str(uuid.uuid4()),
                "buyPrice": price,
                "qty": qty,
                "cycleDays": 0,
                "buyMode": contract_data.get("mode", "안전모드"),
                "buyDate": date_str
            }
            batches.append(new_batch)
            logger.info(f"신규 배치 추가: {new_batch}")
            
        elif trade_type == "SELL":
            batch_id = contract_data.get("batch_id")
            # 해당 배치 찾아서 삭제 및 실현 손익 기록
            batch_to_remove = next((b for b in batches if b.get("id") == batch_id), None)
            if batch_to_remove:
                buy_cost = batch_to_remove["buyPrice"] * batch_to_remove["qty"]
                sell_revenue = price * qty
                realized_profit = sell_revenue - buy_cost
                
                history.append({
                    "date": date_str,
                    "type": "SELL",
                    "buyPrice": batch_to_remove["buyPrice"],
                    "sellPrice": price,
                    "qty": qty,
                    "realized_profit": realized_profit,
                    "buyDate": batch_to_remove.get("buyDate", ""),
                    "buyMode": batch_to_remove.get("buyMode", "안전모드")
                })
                batches.remove(batch_to_remove)
                logger.info(f"배치 청산 완료. 실현손익: {realized_profit:.2f}")

        self.db.save_json(self.batches_file, batches)
        self.db.save_json(self.history_file, history)

# 팩토리에 전략 등록
StrategyFactory.register_strategy("SURFER_BATCH", SurferBatchStrategy)
