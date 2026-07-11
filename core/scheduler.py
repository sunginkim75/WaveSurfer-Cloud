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
        """정기 작업 스케줄 등록 (설정 기반)"""
        from utils.db_handler import DBHandler
        db = DBHandler()
        config = db.load_json(self.core_engine.config_path)
        global_settings = config.get("global_settings", {"order_time": "06:00", "sync_time": "06:10"})
        
        # 설정 시간 파싱
        try:
            o_h, o_m = map(int, global_settings.get("order_time", "06:00").split(":"))
            s_h, s_m = map(int, global_settings.get("sync_time", "06:10").split(":"))
        except:
            o_h, o_m = 6, 0
            s_h, s_m = 6, 10
            
        # 기존 작업 제거
        if self.scheduler.get_job("daily_orders"):
            self.scheduler.remove_job("daily_orders")
        if self.scheduler.get_job("sync_contracts"):
            self.scheduler.remove_job("sync_contracts")
            
        is_active = global_settings.get("scheduler_active", True)
        if not is_active:
            log_info("스케줄러가 비활성화 설정되어 예약 작업을 등록하지 않습니다.")
            return

        # 매일 지정된 시간에 주문 전송
        self.scheduler.add_job(
            self.core_engine.execute_daily_orders,
            trigger=CronTrigger(hour=o_h, minute=o_m),
            id="daily_orders"
        )
        
        # 체결 확인 및 동기화
        self.scheduler.add_job(
            self.core_engine.sync_contracts,
            trigger=CronTrigger(hour=s_h, minute=s_m),
            id="sync_contracts"
        )
        
        log_info(f"스케줄러 작업 등록 완료. (주문: {o_h:02d}:{o_m:02d}, 동기화: {s_h:02d}:{s_m:02d})")
        
    def reload_settings(self):
        """설정 변경 시 스케줄러 재등록"""
        self.setup_jobs()
        
    def start(self):
        self.setup_jobs()
        self.scheduler.start()
        log_info("Trading Scheduler 시작.")
        
    def stop(self):
        self.scheduler.shutdown()
        log_info("Trading Scheduler 종료.")
