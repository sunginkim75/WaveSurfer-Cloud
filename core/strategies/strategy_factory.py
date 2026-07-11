import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """
    모든 매매 전략의 기본 인터페이스.
    각 매매법(Surfer, VR 등)은 이 클래스를 상속받아 구현해야 합니다.
    """
    def __init__(self, task_config: dict):
        self.task_config = task_config
        self.task_id = task_config.get("id")
        self.strategy_name = task_config.get("strategy")

    @abstractmethod
    def calculate_orders(self):
        """
        시장 데이터를 바탕으로 매수/매도 주문(목표가, 수량 등)을 산출합니다.
        """
        pass

    @abstractmethod
    def on_trade_contracted(self, contract_data: dict):
        """
        증권사로부터 체결 데이터를 받았을 때 호출되어 DB 및 상태를 업데이트합니다.
        """
        pass


class StrategyFactory:
    """
    task_config의 'strategy' 필드를 기반으로 적절한 전략 객체를 생성하여 반환합니다.
    """
    _strategies = {}

    @classmethod
    def register_strategy(cls, name: str, strategy_class):
        cls._strategies[name] = strategy_class

    @classmethod
    def get_strategy(cls, task_config: dict) -> BaseStrategy:
        strategy_name = task_config.get("strategy")
        strategy_class = cls._strategies.get(strategy_name)
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        return strategy_class(task_config)

# 이 시점에 패키지 초기화를 통해 등록되도록 각 전략 파일에서 자신을 등록하도록 할 수도 있지만,
# 명시적으로 임포트하여 등록하는 방식을 사용할 수도 있습니다.
import core.strategies.surfer_batch
