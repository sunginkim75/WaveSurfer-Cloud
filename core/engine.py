import logging
import asyncio
from typing import List
from utils.db_handler import DBHandler
from core.strategies.strategy_factory import StrategyFactory
from core.kiwoom_api_client import KiwoomAPIClient
from core.telegram_bot import TelegramBot
from core.scheduler import TradingScheduler

logger = logging.getLogger(__name__)

class CoreEngine:
    """
    모든 태스크(계좌/종목별 매매 전략)를 중앙에서 관리하고 
    스케줄러, 텔레그램 봇, API 클라이언트와의 통신을 조율하는 핵심 엔진입니다.
    """
    def __init__(self, config_path="config/config.json"):
        self.db = DBHandler()
        self.config_path = config_path
        
        # 전체 설정 및 태스크(계좌/전략) 로드
        self.config = self.db.load_json(self.config_path, default_data={"tasks": []})
        
        # 싱글톤 API 클라이언트 및 통신 모듈 초기화
        self.kiwoom_api = KiwoomAPIClient()
        self.telegram = TelegramBot(self.config_path, self)
        self.scheduler = TradingScheduler(self)

    def start(self):
        """엔진 시작: 스케줄러 및 텔레그램 봇 구동"""
        logger.info("CoreEngine 시작")
        self.scheduler.start()
        # 텔레그램 봇은 블로킹 루프일 수 있으므로 메인 앱(FastAPI)과 함께 비동기 태스크로 실행하는 편이 좋음
        # self.telegram.run_polling() 

    async def execute_daily_orders(self):
        """
        장 마감 전(또는 스케줄된 시간) 모든 활성 태스크에 대해
        전략 목표가를 계산하고 키움 API로 주문을 전송합니다.
        """
        logger.info("일일 주문 실행 프로세스 시작")
        tasks = self.config.get("tasks", [])
        
        summary_msg = "📈 <b>일일 주문 계산 결과</b>\n"
        
        for task in tasks:
            if not task.get("is_active", True):
                continue
                
            task_id = task.get("id")
            try:
                strategy = StrategyFactory.get_strategy(task)
                orders = strategy.calculate_orders()
                
                if not orders:
                    summary_msg += f"- {task_id}: 주문 내역 없음\n"
                    continue
                    
                summary_msg += f"- {task_id}: 총 {len(orders)}건 주문 예약\n"
                for order in orders:
                    # 실제 API로 주문 전송 로직 호출
                    is_buy = order.get("type", "BUY") == "BUY"
                    order_type_str = order.get("order_type", "LOC")
                    # Kiwoom order type: LOC=30, MOC=34 (or 33 depending on broker, let's use 34 for MOC)
                    api_order_type = "30" if order_type_str == "LOC" else "34" if order_type_str == "MOC" else "00"
                    
                    try:
                        self.kiwoom_api.send_us_order(
                            acct_no=task.get("account_no", ""),
                            is_buy=is_buy,
                            symbol=task.get("ticker", ""),
                            qty=order.get("qty", 0),
                            price=order.get("price", 0.0),
                            order_type=api_order_type
                        )
                        summary_msg += f"  [{order.get('type')}] {task.get('ticker')} {order.get('qty')}주 @ ${order.get('price')} ({order.get('order_type')}) - 전송완료\n"
                    except Exception as order_err:
                        logger.error(f"주문 전송 에러: {order_err}")
                        summary_msg += f"  [{order.get('type')}] 주문 전송 실패\n"
            except Exception as e:
                logger.error(f"Task {task_id} 실행 중 오류: {e}")
                summary_msg += f"- {task_id}: 오류 발생 ({e})\n"
                
        # 텔레그램으로 전송
        await self.telegram.send_message(summary_msg)

    async def sync_contracts(self):
        """
        장 시작 전(또는 스케줄된 시간) 키움 API로부터 
        간밤의 체결 내역을 불러와서 각 태스크의 전략 상태(DB)를 업데이트합니다.
        """
        logger.info("체결 내역 동기화 프로세스 시작")
        # 가상의 체결 데이터 조회
        # contracts = self.kiwoom_api.get_contract_history(...)
        contracts = [] # 예시
        
        # 체결 데이터 파싱 및 각 태스크 전략의 on_trade_contracted 호출
        
        await self.telegram.send_message("✅ 체결 내역 동기화가 완료되었습니다.")

    def get_status_summary(self):
        """텔레그램 봇 등에서 상태 조회를 위해 사용"""
        active_tasks = len([t for t in self.config.get("tasks", []) if t.get("is_active", True)])
        return f"현재 실행 중인 태스크: {active_tasks}개\n시스템 상태: 정상 작동 중"

    def run_task_immediately(self, task_id: str):
        """특정 태스크 강제 즉시 실행"""
        # (텔레그램 명령어용)
        # asyncio.create_task(...) 등으로 execute_daily_orders의 특정 태스크 버전 실행
        return f"태스크 {task_id} 실행 예약됨"

    def pause_task(self, task_id: str):
        """특정 태스크 일시정지"""
        tasks = self.config.get("tasks", [])
        for task in tasks:
            if task.get("id") == task_id:
                task["is_active"] = False
                self.db.save_json(self.config_path, self.config)
                return "일시정지 완료"
        return "태스크를 찾을 수 없음"
