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
        - 로컬 백테스트 규칙에 따라 원본 주문들(Original Orders)을 1차 연산한 후,
        - netting_handler.process_and_save_netted_orders를 통해 퉁치기 상쇄 및 헷지 압축 주문을 최종 반환합니다.
        """
        # 최신 데이터 가져오기
        latest_close = self.market_data.get_latest_close(self.ticker)
        weekly_rsi_data = self.market_data.get_weekly_rsi_data(self.rsi_ticker, period=14)
        
        if latest_close is None or weekly_rsi_data is None:
            logger.error("시장 데이터를 불러오지 못해 주문을 계산할 수 없습니다.")
            return []
            
        prev_rsi, latest_rsi, trend = weekly_rsi_data
        
        batches = self.db.load_json(self.batches_file, default_data=[])
        
        # 1. 이전 모드 판별 (설정 파일에 저장된 영구 모드 기준)
        current_mode = self.task_config.get("last_mode", "안전모드")
            
        # 2. 공세/안전 모드 전환 판별 (구글 시트 수식 100% 동일 매핑)
        is_safe_condition = (
            (prev_rsi > 65 and prev_rsi > latest_rsi) or
            (40 < prev_rsi < 50 and prev_rsi > latest_rsi) or
            (latest_rsi < 50 and prev_rsi > 50)
        )
        
        is_aggressive_condition = (
            (prev_rsi < 35 and prev_rsi < latest_rsi) or
            (50 < prev_rsi < 60 and prev_rsi < latest_rsi) or
            (latest_rsi > 50 and prev_rsi < 50)
        )
        
        if is_safe_condition:
            current_mode = "안전모드"
        elif is_aggressive_condition:
            current_mode = "공세모드"
                
        # 변경된 모드를 태스크 설정에 즉시 업데이트하여 파일에 보존
        if self.task_config.get("last_mode") != current_mode:
            self.task_config["last_mode"] = current_mode
            config_path = "config/config.json"
            config_data = self.db.load_json(config_path)
            for t in config_data.get("tasks", []):
                if t.get("id") == self.task_id:
                    t["last_mode"] = current_mode
                    break
            self.db.save_json(config_path, config_data)
                
        original_orders = []
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        
        # 2. 보유 배치 매도 주문 계산 (각 배치마다 독립적, 순번을 tier로 지정)
        for idx, batch in enumerate(batches):
            buy_price = batch.get("buyPrice", 0)
            qty = batch.get("qty", 0)
            cycle_days = batch.get("cycleDays", 0)
            batch_mode = batch.get("buyMode", "안전모드")
            buy_date = batch.get("buyDate", "")
            
            # 당일 매수한 배치(경과일수가 0 이하이거나 오늘 날짜인 경우)는 매도 주문 전송 제외
            if cycle_days <= 0 or buy_date == today_str:
                continue
                
            # MOC 청산 기한 설정 (공세 7일, 안전 30일)
            limit_days = 7 if batch_mode == "공세모드" else 30
            
            # 조건 B: MOC 청산 (만기일 경과)
            if cycle_days >= limit_days:
                original_orders.append({
                    "action": "SELL",
                    "order_type": "MOC",
                    "qty": qty,
                    "price": 0.01, # MOC 가상 가격
                    "batch_id": batch.get("id"),
                    "reason": "MOC 청산 (만기 경과)",
                    "tier": idx + 1
                })
                continue
                
            # 조건 A: LOC 매도 (타겟가 도달)
            if batch_mode == "공세모드":
                target_sell = buy_price * (1 + (self.agg_sell_pct / 100))
            else:
                target_sell = buy_price * (1 + (self.safe_sell_pct / 100))
            
            original_orders.append({
                "action": "SELL",
                "order_type": "LOC",
                "qty": qty,
                "price": round(target_sell, 2),
                "batch_id": batch.get("id"),
                "reason": f"LOC 매도 대기 (목표가 {target_sell:.2f})",
                "tier": idx + 1
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
            original_orders.append({
                "action": "BUY",
                "order_type": "LOC",
                "qty": buy_qty,
                "price": round(target_buy, 2),
                "reason": f"LOC 신규 매수 ({current_mode})",
                "mode": current_mode,
                "tier": 0
            })
            
        # ── 4. 수동 퉁치기 엔진을 통한 주문 상쇄 및 헷지 압축 ──
        from core.strategies.netting_handler import process_and_save_netted_orders
        try:
            hts_orders = process_and_save_netted_orders(self.ticker, self.task_id, original_orders, today_str)
            return hts_orders
        except Exception as e:
            logger.error(f"퉁치기 연동 실패, 안전을 위해 원본 주문 전송: {e}")
            # fallback: 퉁치기 실패 시 키움 API용 호환 필드로 리턴
            fallback_orders = []
            for o in original_orders:
                fallback_orders.append({
                    "action": o["action"],
                    "order_type": "34" if o["order_type"] == "MOC" else "30",
                    "qty": o["qty"],
                    "price": o["price"],
                    "reason": o.get("reason", "")
                })
            return fallback_orders

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
