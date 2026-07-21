# -*- coding: utf-8 -*-
"""
무한매수법 V2.2 전략 모듈 (Infinite Buy) — 라오어 원작 규칙 기반
공식 가이드: https://quantstack.app/infinite/v2-2/
공식 카페: https://cafe.naver.com/infinitebuying

핵심 공식:
1. T값 = 누적매수액 / 1회 매수시도액 (소수점 셋째 자리에서 반올림)
2. 별% = 10 - (T/2) * (40 / a)  (a: 분할수, 기본 40)
3. 매도 규칙: 
   - 1/4 수량: 별% LOC 매도
   - 3/4 수량: +10% 지정가 매도
4. 매수 규칙:
   - T = 0: 최초 1회치 종가 LOC 매수
   - 전반전 (T < a/2): 0.5회치 평단 LOC 매수 + 0.5회치 (별% - 0.01달러) LOC 매수
   - 후반전 (T >= a/2): 1회치 (별% - 0.01달러) LOC 매수
5. 쿼터손절 모드:
   - 1/4 수량: MOC 매도
   - 1회 매수시도액을 남은 예수금 기반 10분할로 재설정 (기존 1회 매수액 이하)
   - 매수: -10% LOC 매수
   - 매도: 1/4 수량 -10% LOC 매도 + 3/4 수량 +10% 지정가 매도
"""
import logging
import math
import datetime
import uuid
from core.strategies.strategy_factory import BaseStrategy, StrategyFactory
from utils.db_handler import DBHandler
from utils.market_data import MarketDataManager

logger = logging.getLogger(__name__)


class InfiniteBuyStrategy(BaseStrategy):
    """
    라오어 무한매수법 V2.2 자동매매 전략
    """

    def __init__(self, task_config: dict):
        super().__init__(task_config)
        self.db = DBHandler()
        self.market_data = MarketDataManager()

        # 파일 경로 (태스크별 독립)
        self.batches_file = f"config/trade_batches_{self.task_id}.json"
        self.history_file = f"config/trade_history_{self.task_id}.json"

        # 기본 파라미터
        self.ticker = self.task_config.get("ticker", "TQQQ")
        self.seed_amt = self.task_config.get("seed_amt", 10000)
        self.additional_seed = self.task_config.get("additional_seed", 0)
        self.split_count = self.task_config.get("split_count", 40)
        
        # 쿼터손절 모드는 직접 설정하거나 T값이 임계치에 도달할 때 자동 활성화 가능
        self.losscut_mode = self.task_config.get("losscut_mode", False)

        # 무한매수 V2.2 기본값 설정
        self.loc_sell_pct = self.task_config.get("ib_loc_sell_pct", 5.0)     # 사용자가 오버라이드한 경우를 위함
        self.limit_sell_pct = self.task_config.get("ib_limit_sell_pct", 10.0) # 지정가 매도 기준
        self.losscut_pct = self.task_config.get("ib_losscut_pct", -10.0)     # 쿼터손절 기준

        # 총 투자 원금
        self.total_seed = self.seed_amt + self.additional_seed

        # 1회 매수 시도액 (기본값)
        self.buy_unit = self.total_seed / self.split_count

    def _get_avg_buy_price(self, batches: list) -> float:
        """보유 배치의 가중 평균 매입가"""
        total_cost = sum(b.get("buyPrice", 0) * b.get("qty", 0) for b in batches)
        total_qty = sum(b.get("qty", 0) for b in batches)
        return total_cost / total_qty if total_qty > 0 else 0.0

    def _get_total_qty(self, batches: list) -> int:
        """전체 보유 수량"""
        return sum(b.get("qty", 0) for b in batches)

    def _get_total_cost(self, batches: list) -> float:
        """누적 매입 금액"""
        return sum(b.get("buyPrice", 0) * b.get("qty", 0) for b in batches)

    def _calc_t_value(self, batches: list) -> float:
        """
        T값 정의: 누적매수액 / 1회 매수액
        소수점 셋째 자리에서 반올림 (둘째 자리까지 표시)
        """
        total_cost = self._get_total_cost(batches)
        if self.buy_unit <= 0:
            return 0.0
        return round(total_cost / self.buy_unit, 2)

    def _calc_star_pct(self, t_value: float) -> float:
        """
        별% 공식: 10 - (T/2) * (40 / a)
        """
        return 10.0 - (t_value / 2.0) * (40.0 / self.split_count)

    def _is_first_half(self, t_value: float) -> bool:
        """전반전 여부: T < 분할수 / 2"""
        return t_value < (self.split_count / 2.0)

    def calculate_orders(self) -> list:
        """
        오늘 장마감 전 전송해야 할 LOC/MOC/LIMIT 주문 목록 반환
        """
        latest_close = self.market_data.get_latest_close(self.ticker)
        if latest_close is None:
            logger.error(f"[{self.task_id}] 시장 데이터를 불러오지 못해 무한매수 주문을 계산할 수 없습니다.")
            return []

        batches = self.db.load_json(self.batches_file, default_data=[])
        t_value = self._calc_t_value(batches)
        avg_price = self._get_avg_buy_price(batches)
        total_qty = self._get_total_qty(batches)
        first_half = self._is_first_half(t_value)
        star_pct = self._calc_star_pct(t_value)

        # 쿼터손절 자동 감지: 자금이 거의 소진되었을 때 (T >= split_count - 1)
        # 또는 사용자가 직접 쿼터손절 모드를 토글했을 때
        # 단, 보유 물량이 없거나 평단이 0이면 평단 기준 계산이 불가능하므로 쿼터손절 진입을 유예하고 일반 모드로 1회차를 시작합니다.
        active_losscut = (self.losscut_mode or (t_value >= self.split_count - 1.0)) and (total_qty > 0 and avg_price > 0)

        orders = []

        logger.info(
            f"[{self.task_id}] 무한매수 V2.2 주문 계산 시작 - "
            f"T값: {t_value:.2f}, 평균매입가: ${avg_price:.2f}, 보유량: {total_qty}주, "
            f"별%: {star_pct:.2f}%, 최종쿼터손절판단: {active_losscut}"
        )

        # ═══════════════════════════════════════════
        # 1. 매도 주문 생성 (보유 물량이 있을 때만)
        # ═══════════════════════════════════════════
        if total_qty > 0 and avg_price > 0:
            if active_losscut:
                # ── 쿼터손절 모드 매도 ──
                # 1) MOC 매도로 1/4 무조건 매도
                qty_1_4 = math.floor(total_qty / 4.0)
                qty_3_4 = total_qty - qty_1_4
                
                if qty_1_4 > 0:
                    orders.append({
                        "type": "SELL",
                        "order_type": "MOC",
                        "qty": qty_1_4,
                        "price": 0,
                        "reason": f"쿼터손절 무조건 MOC 매도 (1/4 수량: {qty_1_4}주)"
                    })
                
                # 2) 나머지 3/4: +10% 지정가 매도
                if qty_3_4 > 0:
                    limit_sell_price = round(avg_price * (1.0 + self.limit_sell_pct / 100.0), 2)
                    orders.append({
                        "type": "SELL",
                        "order_type": "LIMIT",
                        "qty": qty_3_4,
                        "price": limit_sell_price,
                        "reason": f"지정가 매도 (3/4 수량, +{self.limit_sell_pct}%, ${limit_sell_price})"
                    })
                
                # 3) 1/4 수량: -10% LOC 매도 (쿼터손절용)
                if qty_1_4 > 0:
                    losscut_sell_price = round(avg_price * (1.0 + self.losscut_pct / 100.0), 2)
                    orders.append({
                        "type": "SELL",
                        "order_type": "LOC",
                        "qty": qty_1_4,
                        "price": losscut_sell_price,
                        "reason": f"쿼터손절 LOC 매도 ({self.losscut_pct}%, ${losscut_sell_price})"
                    })
            else:
                # ── 일반 모드 매도 ──
                qty_1_4 = math.floor(total_qty / 4.0)
                qty_3_4 = total_qty - qty_1_4

                # 1/4 수량: 별% LOC 매도
                if qty_1_4 > 0:
                    star_sell_price = round(avg_price * (1.0 + star_pct / 100.0), 2)
                    orders.append({
                        "type": "SELL",
                        "order_type": "LOC",
                        "qty": qty_1_4,
                        "price": star_sell_price,
                        "reason": f"별% LOC 매도 (1/4 수량, {star_pct:+.2f}%, ${star_sell_price})"
                    })

                # 3/4 수량: +10% 지정가 매도
                if qty_3_4 > 0:
                    limit_sell_price = round(avg_price * (1.0 + self.limit_sell_pct / 100.0), 2)
                    orders.append({
                        "type": "SELL",
                        "order_type": "LIMIT",
                        "qty": qty_3_4,
                        "price": limit_sell_price,
                        "reason": f"지정가 매도 (3/4 수량, +{self.limit_sell_pct}%, ${limit_sell_price})"
                    })

        # ═══════════════════════════════════════════
        # 2. 매수 주문 생성
        # ═══════════════════════════════════════════
        if active_losscut:
            # ── 쿼터손절 모드 매수 ──
            target_buy_price = round(avg_price * (1.0 + self.losscut_pct / 100.0), 2)
            buy_qty = max(1, int(self.buy_unit // target_buy_price)) if target_buy_price > 0 else 0
            if buy_qty > 0:
                orders.append({
                    "type": "BUY",
                    "order_type": "LOC",
                    "qty": buy_qty,
                    "price": target_buy_price,
                    "reason": f"쿼터손절 -10% LOC 매수 (${target_buy_price})",
                    "mode": "쿼터손절"
                })
        else:
            # ── 일반 모드 매수 ──
            if t_value == 0.0:
                # 최초 1회차: 평단가가 없으므로 종가 기준으로 1회치 LOC 매수 (최소 1주 보장)
                buy_qty = max(1, int(self.buy_unit // latest_close)) if latest_close > 0 else 0
                if buy_qty > 0:
                    orders.append({
                        "type": "BUY",
                        "order_type": "LOC",
                        "qty": buy_qty,
                        "price": round(latest_close, 2),
                        "reason": f"1회차 최초 LOC 매수 (종가 ${latest_close:.2f})",
                        "mode": "1회시작"
                    })
            elif first_half:
                # 전반전 매수 (0.5회치 평단 LOC + 0.5회치 별% LOC)
                half_unit = self.buy_unit / 2.0

                # 1) 0.5회치: 평단 LOC 매수 (최소 1주 보장)
                buy_qty_1 = max(1, int(half_unit // avg_price)) if avg_price > 0 else 0
                if buy_qty_1 > 0:
                    orders.append({
                        "type": "BUY",
                        "order_type": "LOC",
                        "qty": buy_qty_1,
                        "price": round(avg_price, 2),
                        "reason": f"전반전 평단가 LOC 매수 (0.5회치, ${avg_price:.2f})",
                        "mode": "전반전"
                    })

                # 2) 0.5회치: 별% LOC 매수 (매도와 겹치지 않게 별지점 - 0.01달러, 최소 1주 보장)
                star_buy_price = round(avg_price * (1.0 + star_pct / 100.0), 2) - 0.01
                buy_qty_2 = max(1, int(half_unit // star_buy_price)) if star_buy_price > 0 else 0
                if buy_qty_2 > 0:
                    orders.append({
                        "type": "BUY",
                        "order_type": "LOC",
                        "qty": buy_qty_2,
                        "price": round(star_buy_price, 2),
                        "reason": f"전반전 별% LOC 매수 (0.5회치, {star_pct:+.2f}%, ${star_buy_price:.2f})",
                        "mode": "전반전"
                    })
            else:
                # 후반전 매수 (1회치 별% LOC - 0.01달러, 최소 1주 보장)
                star_buy_price = round(avg_price * (1.0 + star_pct / 100.0), 2) - 0.01
                buy_qty = max(1, int(self.buy_unit // star_buy_price)) if star_buy_price > 0 else 0
                if buy_qty > 0:
                    orders.append({
                        "type": "BUY",
                        "order_type": "LOC",
                        "qty": buy_qty,
                        "price": round(star_buy_price, 2),
                        "reason": f"후반전 별% LOC 매수 (1.0회치, {star_pct:+.2f}%, ${star_buy_price:.2f})",
                        "mode": "후반전"
                    })

        return orders

    def on_trade_contracted(self, contract_data: dict):
        """
        체결 내역을 바탕으로 배치 상태 업데이트
        매도 체결 시 전량 청산 처리 → 다음날 1회차 리셋
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
                "buyMode": contract_data.get("mode", "전반전"),
                "buyDate": date_str
            }
            batches.append(new_batch)
            new_t = self._calc_t_value(batches)
            logger.info(f"[{self.task_id}] 무한매수 V2.2 매수 체결: {qty}주 @ ${price}, 신규 T값: {new_t:.2f}")

        elif trade_type == "SELL":
            # 매도 시 보유하고 있던 배치들의 평단 및 총 비용 계산하여 이익 기록
            avg_buy = self._get_avg_buy_price(batches)
            total_cost = self._get_total_cost(batches)
            sell_revenue = price * qty
            realized_profit = sell_revenue - total_cost

            history.append({
                "date": date_str,
                "type": "SELL",
                "buyPrice": avg_buy,
                "sellPrice": price,
                "qty": qty,
                "realized_profit": realized_profit,
                "t_value": self._calc_t_value(batches),
                "buyMode": "무한매수"
            })

            # 무한매수 핵심: 매도 발생 시 모든 배치를 초기화하여 1회차부터 재시작하도록 비움
            batches.clear()
            logger.info(
                f"[{self.task_id}] 무한매수 V2.2 매도 체결 (전량 청산). "
                f"매도가: ${price}, 실현손익: ${realized_profit:.2f} → 다음 사이클 리셋 완료"
            )

        self.db.save_json(self.batches_file, batches)
        self.db.save_json(self.history_file, history)


# 팩토리에 전략 등록
StrategyFactory.register_strategy("INFINITE_BUY", InfiniteBuyStrategy)
