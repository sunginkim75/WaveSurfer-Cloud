import os
import uvicorn
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel
import logging

from core.engine import CoreEngine
from utils.db_handler import DBHandler
from core.backtester import Backtester


# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="WaveSurfer-Cloud API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

# 핵심 엔진 인스턴스
engine = CoreEngine()
db = DBHandler()

# 프론트엔드 정적 파일 서빙 (웹 대시보드)
app.mount("/dashboard", StaticFiles(directory="web", html=True), name="web")

@app.on_event("startup")
async def startup_event():
    logger.info("서버 시작: CoreEngine 구동")
    engine.start()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "WaveSurfer-Cloud API is running."}

@app.get("/api/v1/tasks")
def get_tasks():
    """현재 등록된 태스크(계좌/전략) 목록을 반환"""
    config = db.load_json(engine.config_path)
    return {"tasks": config.get("tasks", [])}

class GlobalSettingsModel(BaseModel):
    order_time: str
    sync_time: str
    scheduler_active: bool = True

@app.get("/api/v1/settings")
def get_settings():
    """글로벌 설정 반환"""
    config = db.load_json(engine.config_path)
    # 기본값 설정
    settings = config.get("global_settings", {"order_time": "06:00", "sync_time": "06:10", "scheduler_active": True})
    return settings

@app.put("/api/v1/settings")
def update_settings(settings: GlobalSettingsModel):
    """글로벌 설정 업데이트 및 스케줄러 재시작"""
    config = db.load_json(engine.config_path)
    config["global_settings"] = {
        "order_time": settings.order_time,
        "sync_time": settings.sync_time,
        "scheduler_active": settings.scheduler_active
    }
    db.save_json(engine.config_path, config)
    
    # 스케줄러에 설정 즉시 반영
    engine.scheduler.reload_settings()
    return {"status": "success", "settings": config["global_settings"]}

@app.get("/api/v1/logs")
def get_logs():
    """시스템 로그 최근 100줄 반환"""
    from utils.path_handler import get_app_data_path
    log_file = get_app_data_path("logs/app.log")
    if not os.path.exists(log_file):
        return {"logs": ["No logs found."]}
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return {"logs": lines[-100:]}
    except Exception as e:
        return {"logs": [f"Error reading logs: {str(e)}"]}

class TaskCreateModel(BaseModel):
    account_no: str
    nickname: str
    strategy: str
    ticker: str
    seed_amt: int = 10000
    safe_buy_pct: float = 3.0
    safe_sell_pct: float = 0.2
    agg_buy_pct: float = 5.0
    agg_sell_pct: float = 2.5
    split_count: int = 7
    update_period: int = 10
    compounding_profit_rate: int = 80
    compounding_loss_rate: int = 30

class TaskUpdateModel(TaskCreateModel):
    account_no: Optional[str] = None
    is_active: Optional[bool] = None
    nickname: Optional[str] = None
    strategy: Optional[str] = None
    ticker: Optional[str] = None
    seed_amt: Optional[int] = None
    safe_buy_pct: Optional[float] = None
    safe_sell_pct: Optional[float] = None
    agg_buy_pct: Optional[float] = None
    agg_sell_pct: Optional[float] = None
    split_count: Optional[int] = None
    update_period: Optional[int] = None
    compounding_profit_rate: Optional[int] = None
    compounding_loss_rate: Optional[int] = None

@app.patch("/api/v1/tasks/{task_id}")
@app.put("/api/v1/tasks/{task_id}")
def update_task(task_id: str, data: TaskUpdateModel):
    """테스크의 상태/설정 업데이트"""
    config = db.load_json(engine.config_path)
    tasks = config.get("tasks", [])
    for t in tasks:
        if t.get("id") == task_id:
            if data.is_active is not None:
                t["is_active"] = data.is_active
            
            if data.account_no is not None: t["account_no"] = data.account_no
            if data.nickname is not None: t["nickname"] = data.nickname
            if data.ticker is not None: t["ticker"] = data.ticker
            if data.seed_amt is not None: t["seed_amt"] = data.seed_amt
            if data.safe_buy_pct is not None: t["safe_buy_pct"] = data.safe_buy_pct
            if data.safe_sell_pct is not None: t["safe_sell_pct"] = data.safe_sell_pct
            if data.agg_buy_pct is not None: t["agg_buy_pct"] = data.agg_buy_pct
            if data.agg_sell_pct is not None: t["agg_sell_pct"] = data.agg_sell_pct
            if data.split_count is not None: t["split_count"] = data.split_count
            if data.update_period is not None: t["update_period"] = data.update_period
            if data.compounding_profit_rate is not None: t["compounding_profit_rate"] = data.compounding_profit_rate
            if data.compounding_loss_rate is not None: t["compounding_loss_rate"] = data.compounding_loss_rate
            
            if data.strategy is not None:
                t["strategy"] = data.strategy

            db.save_json(engine.config_path, config)
            return {"status": "success", "task_id": task_id, "updated": True}
    return JSONResponse(status_code=404, content={"message": "Task not found"})

@app.post("/api/v1/tasks")
def create_task(data: TaskCreateModel):
    """새로운 매매 태스크(전략) 등록"""
    import uuid
    config = db.load_json(engine.config_path)
    tasks = config.get("tasks", [])
    
    new_task = {
        "id": f"task_{str(uuid.uuid4())[:8]}",
        "account_no": data.account_no,
        "nickname": data.nickname,
        "strategy": data.strategy,
        "ticker": data.ticker,
        "rsi_ticker": "QQQ",
        "seed_amt": data.seed_amt,
        "safe_buy_pct": data.safe_buy_pct,
        "safe_sell_pct": data.safe_sell_pct,
        "agg_buy_pct": data.agg_buy_pct,
        "agg_sell_pct": data.agg_sell_pct,
        "split_count": data.split_count,
        "update_period": data.update_period,
        "compounding_profit_rate": data.compounding_profit_rate,
        "compounding_loss_rate": data.compounding_loss_rate,
        "is_active": True
    }
    
    tasks.append(new_task)
    config["tasks"] = tasks
    db.save_json(engine.config_path, config)
    return {"status": "success", "task": new_task}

@app.delete("/api/v1/tasks/{task_id}")
def delete_task(task_id: str):
    """태스크 삭제"""
    config = db.load_json(engine.config_path)
    tasks = config.get("tasks", [])
    initial_len = len(tasks)
    tasks = [t for t in tasks if t.get("id") != task_id]
    
    if len(tasks) == initial_len:
        return JSONResponse(status_code=404, content={"message": "Task not found"})
        
    config["tasks"] = tasks
    db.save_json(engine.config_path, config)
    return {"status": "success", "deleted_task_id": task_id}

@app.get("/api/v1/tasks/{task_id}/batches")
def get_batches(task_id: str):
    """특정 태스크의 현재 보유 배치 목록 반환"""
    batches_file = f"config/trade_batches_{task_id}.json"
    batches = db.load_json(batches_file, default_data=[])
    return {"task_id": task_id, "batches": batches}

@app.get("/api/v1/tasks/{task_id}/history")
def get_history(task_id: str):
    """특정 태스크의 체결/수익 히스토리 반환"""
    history_file = f"config/trade_history_{task_id}.json"
    history = db.load_json(history_file, default_data=[])
    return {"task_id": task_id, "history": history}

@app.get("/api/v1/tasks/{task_id}/orders/preview")
def preview_orders(task_id: str):
    """태스크의 오늘자 예상 LOC/MOC 주문표 반환 (Dry-run)"""
    from core.strategies.strategy_factory import StrategyFactory
    # 전략 모듈 임포트 강제화 (Factory 등록용)
    import core.strategies.surfer_batch 
    
    config = db.load_json(engine.config_path)
    tasks = config.get("tasks", [])
    task_config = next((t for t in tasks if t.get("id") == task_id), None)
    
    if not task_config:
        return JSONResponse(status_code=404, content={"message": "Task not found"})
        
    try:
        strategy_instance = StrategyFactory.get_strategy(task_config)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"message": str(e)})
        
    orders = strategy_instance.calculate_orders()
    
    return {"task_id": task_id, "orders": orders}

@app.post("/api/v1/engine/execute")
async def trigger_execute():
    """수동으로 일일 주문 실행 로직 강제 트리거"""
    import asyncio
    asyncio.create_task(engine.execute_daily_orders())
    return {"status": "queued", "message": "일일 주문 실행이 백그라운드에 등록되었습니다."}

@app.post("/api/v1/tasks/{task_id}/execute")
async def trigger_task_execute(task_id: str):
    """개별 태스크 수동 주문 실행 (동기 응답 - 결과 반환)"""
    config = db.load_json(engine.config_path)
    tasks = config.get("tasks", [])
    task_config = next((t for t in tasks if t.get("id") == task_id), None)
    
    if not task_config:
        return JSONResponse(status_code=404, content={"status": "error", "message": "태스크를 찾을 수 없습니다."})
    
    results = []
    try:
        from core.strategies.strategy_factory import StrategyFactory
        strategy = StrategyFactory.get_strategy(task_config)
        orders = strategy.calculate_orders()
        
        if not orders:
            return {"status": "ok", "task_id": task_id, "message": "주문 내역 없음", "results": []}
        
        for order in orders:
            is_buy = order.get("type", "BUY") == "BUY"
            order_type_str = order.get("order_type", "LOC")
            api_order_type = "30" if order_type_str == "LOC" else "34" if order_type_str == "MOC" else "00"
            
            result_item = {
                "type": order.get("type"),
                "order_type": order.get("order_type"),
                "ticker": task_config.get("ticker"),
                "qty": order.get("qty", 0),
                "price": order.get("price", 0.0),
                "status": "pending"
            }
            
            try:
                resp = engine.kiwoom_api.send_us_order(
                    acct_no=task_config.get("account_no", ""),
                    is_buy=is_buy,
                    symbol=task_config.get("ticker", ""),
                    qty=order.get("qty", 0),
                    price=order.get("price", 0.0),
                    order_type=api_order_type
                )
                if resp and resp.get("return_code") == 0:
                    result_item["status"] = "success"
                    result_item["message"] = resp.get("return_msg", "주문 전송 성공")
                else:
                    result_item["status"] = "fail"
                    result_item["message"] = resp.get("return_msg", "주문 전송 실패") if resp else "응답 없음"
            except Exception as order_err:
                result_item["status"] = "fail"
                result_item["message"] = str(order_err)
            
            results.append(result_item)
        
        return {"status": "ok", "task_id": task_id, "results": results}
    except Exception as e:
        logger.error(f"Task {task_id} 수동 실행 에러: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/api/v1/engine/sync")
async def trigger_sync():
    """수동으로 체결 내역 동기화 강제 트리거"""
    import asyncio
    asyncio.create_task(engine.sync_contracts())
    return {"status": "queued", "message": "체결 내역 동기화가 백그라운드에 등록되었습니다."}

class BacktestRequestModel(BaseModel):
    ticker: str
    start_date: str = "2018-07-27"
    end_date: Optional[str] = None
    seed_amt: float = 10000.0
    safe_buy_pct: float = 3.0
    safe_sell_pct: float = 0.2
    agg_buy_pct: float = 5.0
    agg_sell_pct: float = 2.5
    split_count: int = 7
    update_period: int = 10
    compounding_profit_rate: float = 80.0
    compounding_loss_rate: float = 30.0

@app.post("/api/v1/backtest")
def run_backtest(data: BacktestRequestModel):
    """
    야후 파이낸스 데이터를 다운로드하여 백테스트를 수행합니다.
    """
    try:
        result = Backtester.run_backtest(
            ticker=data.ticker,
            start_date_str=data.start_date,
            end_date_str=data.end_date,
            seed_amt=data.seed_amt,
            safe_buy_pct=data.safe_buy_pct,
            safe_sell_pct=data.safe_sell_pct,
            agg_buy_pct=data.agg_buy_pct,
            agg_sell_pct=data.agg_sell_pct,
            split_count=data.split_count,
            update_period=data.update_period,
            compounding_profit_rate=data.compounding_profit_rate,
            compounding_loss_rate=data.compounding_loss_rate
        )
        return result
    except Exception as e:
        logger.error(f"백테스트 실행 실패: {e}")
        return JSONResponse(status_code=500, content={"message": str(e)})


@app.get("/api/v1/tasks/{task_id}/matching")
def get_matching_table(task_id: str):
    """
    실제 운영 중인 Task의 체결 내역과 시장 데이터를 결합한 매매 대조표 보고서를 반환합니다.
    """
    config = db.load_json(engine.config_path)
    tasks = config.get("tasks", [])
    task_config = next((t for t in tasks if t.get("id") == task_id), None)
    if not task_config:
        return JSONResponse(status_code=404, content={"message": "Task not found"})
        
    try:
        from core.backtest_assembler import BacktestAssembler
        result = BacktestAssembler.assemble_matching_report(task_config)
        return result
    except Exception as e:
        logger.error(f"매칭 테이블 조립 실패: {e}")
        return JSONResponse(status_code=500, content={"message": str(e)})


def main():
    logger.info("Starting Uvicorn Server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
