# -*- coding: utf-8 -*-
"""
APScheduler 기반 정기 주문 및 장마감 체결 상태 확인 스케줄러.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from utils.logger import log_info, log_error

class TradingScheduler:
    def __init__(self, core_engine):
        self.scheduler = BackgroundScheduler()
        self.core_engine = core_engine
        
    def setup_jobs(self):
        """정기 작업 스케줄 등록"""
        # 매일 장 종료 1시간 전 주문 전송 (예: 한국시간 새벽 4시)
        self.scheduler.add_job(
            self.core_engine.execute_daily_orders,
            trigger=CronTrigger(hour=4, minute=0),
            id="daily_orders"
        )
        
        # 매일 한국시간 오전 6시에 체결 확인 및 동기화
        self.scheduler.add_job(
            self.core_engine.sync_contracts,
            trigger=CronTrigger(hour=6, minute=0),
            id="sync_contracts"
        )
        
        log_info("스케줄러 작업 등록 완료.")
        
    def start(self):
        self.setup_jobs()
        self.scheduler.start()
        log_info("Trading Scheduler 시작.")
        
    def stop(self):
        self.scheduler.shutdown()
        log_info("Trading Scheduler 종료.")
