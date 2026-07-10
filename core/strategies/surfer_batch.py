# -*- coding: utf-8 -*-
from core.strategies.base_strategy import BaseStrategy
from utils.logger import log_info, log_error

class SurferBatchStrategy(BaseStrategy):
    def calculate_orders(self, task_config, market_data, account_balance):
        """
        SURFER 복리 분할매매 전략 주문 계산.
        안전/공세 모드를 판단하고, 각 배치의 제한 일수를 체크하여 MOC/LOC 주문을 생성.
        """
        orders = []
        log_info(f"SURFER 복리 매매 전략 연산 시작 - Task: {task_config.get('id')}")
        # TODO: 상세한 RSI 기반 안전/공세 모드 판단 및 LOC 매수/매도 로직 구현
        # 현재는 Mock-up 구조
        orders.append({
            "type": "buy",
            "order_type": "30", # LOC
            "qty": 5,
            "price": 220.0,
            "reason": "안전모드 LOC 매수 추천가"
        })
        return orders

    def on_trade_contracted(self, task_config, contract_data):
        """
        실제 체결된 데이터를 바탕으로 trade_batches.json의 배치 상태 갱신.
        """
        log_info(f"SURFER 체결 반영 및 배치 갱신 - {contract_data}")
        # TODO: JSON 파일 갱신 및 복리(BFS) 연산 로직 구현
        pass
