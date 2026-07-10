# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def calculate_orders(self, task_config, market_data, account_balance):
        """당일 계산할 주문 목록 리스트 반환 (LOC/MOC 여부 포함)"""
        pass

    @abstractmethod
    def on_trade_contracted(self, task_config, contract_data):
        """체결 결과에 따른 로컬 데이터베이스 및 배치 갱신 작업"""
        pass
