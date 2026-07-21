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

class AuthRequestModel(BaseModel):
    passcode: str

@app.post("/api/v1/auth/verify")
def verify_auth(data: AuthRequestModel):
    config = db.load_json(engine.config_path)
    server_config = config.get("server", {})
    expected_passcode = server_config.get("passcode", "admin1234")
    
    if data.passcode == expected_passcode:
        return {"status": "success", "message": "Authenticated"}
    else:
        return JSONResponse(status_code=401, content={"status": "fail", "message": "Incorrect passcode"})

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

class KiwoomAccountsConfigModel(BaseModel):
    accounts: dict

@app.get("/api/v1/kiwoom/config")
def get_kiwoom_config():
    """키움 계좌별 API 설정 목록 반환 (마스킹 포함)"""
    config = db.load_json(engine.config_path)
    accounts = config.get("accounts", {})
    masked_accounts = {}
    for acct, info in accounts.items():
        if isinstance(info, dict):
            masked_accounts[acct] = {
                "nickname": info.get("nickname", ""),
                "app_key": info.get("app_key", ""),
                "app_secret": "******" if info.get("app_secret") else ""
            }
        else:
            # 구버전 호환
            masked_accounts[acct] = {
                "nickname": f"구버전 계좌",
                "app_key": "",
                "app_secret": ""
            }
    return {"accounts": masked_accounts}

@app.put("/api/v1/kiwoom/config")
def update_kiwoom_config(data: KiwoomAccountsConfigModel):
    """키움 계좌별 API 설정 업데이트 (마스킹 보존 처리)"""
    config = db.load_json(engine.config_path)
    old_accounts = config.get("accounts", {})
    new_accounts = {}
    for acct, info in data.accounts.items():
        acct = str(acct).strip()
        if not acct:
            continue
        nickname = info.get("nickname", "").strip()
        app_key = info.get("app_key", "").strip()
        app_secret = info.get("app_secret", "").strip()
        if app_secret == "******":
            old_info = old_accounts.get(acct, {})
            if isinstance(old_info, dict):
                app_secret = old_info.get("app_secret", "")
            else:
                app_secret = ""
        new_accounts[acct] = {
            "nickname": nickname,
            "app_key": app_key,
            "app_secret": app_secret
        }
    config["accounts"] = new_accounts
    db.save_json(engine.config_path, config)
    engine.kiwoom_api.load_config()
    return {"status": "success", "message": "Kiwoom per-account configurations updated"}

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
    losscut_mode: bool = False
    ib_loc_sell_pct: float = 5.45
    ib_limit_sell_pct: float = 10.0
    ib_loc_buy_pct: float = 0.0
    ib_losscut_pct: float = -10.0
    operation_mode: str = "MOCK_VIRTUAL"

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
    losscut_mode: Optional[bool] = None
    ib_loc_sell_pct: Optional[float] = None
    ib_limit_sell_pct: Optional[float] = None
    ib_loc_buy_pct: Optional[float] = None
    ib_losscut_pct: Optional[float] = None
    operation_mode: Optional[str] = None

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
            if data.seed_amt is not None:
                old_seed = float(t.get("seed_amt", 0.0))
                new_seed = float(data.seed_amt)
                diff = new_seed - old_seed
                t["seed_amt"] = data.seed_amt
                if "last_compounding_cash" in t:
                    t["last_compounding_cash"] = float(t["last_compounding_cash"]) + diff
                else:
                    t["last_compounding_cash"] = new_seed
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
            if data.losscut_mode is not None:
                t["losscut_mode"] = data.losscut_mode
            if data.ib_loc_sell_pct is not None:
                t["ib_loc_sell_pct"] = data.ib_loc_sell_pct
            if data.ib_limit_sell_pct is not None:
                t["ib_limit_sell_pct"] = data.ib_limit_sell_pct
            if data.ib_loc_buy_pct is not None:
                t["ib_loc_buy_pct"] = data.ib_loc_buy_pct
            if data.ib_losscut_pct is not None:
                t["ib_losscut_pct"] = data.ib_losscut_pct
            if data.operation_mode is not None:
                t["operation_mode"] = data.operation_mode

            db.save_json(engine.config_path, config)
            return {"status": "success", "task_id": task_id, "updated": True}
    return JSONResponse(status_code=404, content={"message": "Task not found"})

@app.post("/api/v1/tasks")
def create_task(data: TaskCreateModel):
    """새로운 매매 태스크(전략) 등록"""
    import uuid
    import datetime
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
        "losscut_mode": data.losscut_mode,
        "ib_loc_sell_pct": data.ib_loc_sell_pct,
        "ib_limit_sell_pct": data.ib_limit_sell_pct,
        "ib_loc_buy_pct": data.ib_loc_buy_pct,
        "ib_losscut_pct": data.ib_losscut_pct,
        "is_active": True,
        "status": "ACTIVE",
        "operation_mode": data.operation_mode,
        "created_at": datetime.date.today().strftime("%Y-%m-%d")
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

    # 관련 배치 파일 및 히스토리 파일 삭제 추가
    import os
    batches_file = f"config/trade_batches_{task_id}.json"
    history_file = f"config/trade_history_{task_id}.json"
    try:
        if os.path.exists(batches_file):
            os.remove(batches_file)
            logger.info(f"Deleted batches file: {batches_file}")
        if os.path.exists(history_file):
            os.remove(history_file)
            logger.info(f"Deleted history file: {history_file}")
    except Exception as e:
        logger.error(f"Failed to delete task files for {task_id}: {e}")

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
    import core.strategies.infinite_buy
    
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
    ticker = task_config.get("ticker", "SOXL").upper().strip()
    try:
        from utils.market_data import MarketDataManager
        latest_close = MarketDataManager().get_latest_close(ticker) or 0.0
    except Exception:
        latest_close = 0.0
    
    return {"task_id": task_id, "orders": orders, "latest_close": latest_close}

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
            action = str(order.get("action") or order.get("type") or "BUY").upper()
            is_buy = (action == "BUY")
            ot = str(order.get("order_type", "30")).upper()
            if ot in ["30", "LOC"]:
                api_order_type = "30"
            elif ot in ["34", "MOC"]:
                api_order_type = "34"
            elif ot in ["00", "LIMIT", "지정가"]:
                api_order_type = "00"
            elif ot in ["03", "MARKET", "시장가"]:
                api_order_type = "03"
            else:
                api_order_type = ot
            
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


class MatchingEditModel(BaseModel):
    date: str
    buyPrice: Optional[str] = None
    buyQty: Optional[str] = None
    sellPrice: Optional[str] = None
    sellQty: Optional[str] = None
    sellDate: Optional[str] = None
    mode: Optional[str] = "안전모드"


@app.post("/api/v1/tasks/{task_id}/matching/edit")
def edit_matching_transaction(task_id: str, data: MatchingEditModel):
    """
    수동 모드 사용자가 대시보드에서 기입한 체결 기록을 로컬 DB에 수동 덮어쓰기합니다.
    """
    config = db.load_json(engine.config_path)
    tasks = config.get("tasks", [])
    task_config = next((t for t in tasks if t.get("id") == task_id), None)
    if not task_config:
        return JSONResponse(status_code=404, content={"message": "Task not found"})
        
    try:
        from core.backtest_assembler import BacktestAssembler
        success = BacktestAssembler.edit_transaction(task_config, data.dict())
        if success:
            return {"status": "success", "message": "Transaction updated successfully"}
        else:
            return JSONResponse(status_code=400, content={"message": "Update failed"})
    except Exception as e:
        logger.error(f"체결 기록 수동 수정 실패: {e}")
        return JSONResponse(status_code=500, content={"message": str(e)})


@app.post("/api/v1/tasks/{task_id}/sync")
def sync_task_contracts(task_id: str):
    """
    수동 모드용: 특정 태스크의 실제 키움 잔고를 강제 1회성 동기화합니다.
    """
    try:
        result = engine.sync_task_balance(task_id)
        return result
    except ValueError as val_err:
        logger.error(f"잔고 동기화 파라미터 에러: {val_err}")
        return JSONResponse(status_code=400, content={"message": str(val_err)})
    except ConnectionError as conn_err:
        logger.error(f"키움 API 접속 실패: {conn_err}")
        return JSONResponse(status_code=502, content={"message": str(conn_err)})
    except Exception as e:
        logger.error(f"계좌 동기화 실행 중 알 수 없는 예외 발생: {e}")
        return JSONResponse(status_code=500, content={"message": f"시스템 오류: {str(e)}"})


@app.post("/api/v1/tasks/{task_id}/run")
def run_task_immediately(task_id: str):
    """
    수동 모드용: 특정 태스크를 즉시 강제 1회 실행(주문표 재연산 및 발송)합니다.
    """
    try:
        msg = engine.run_task_immediately(task_id)
        return {"status": "success", "message": msg}
    except Exception as e:
        logger.error(f"태스크 즉시 실행 실패: {e}")
        return JSONResponse(status_code=500, content={"message": str(e)})


def main():
    import sys
    logger.info("Starting Uvicorn Server...")
    is_dev = "--dev" in sys.argv or "--reload" in sys.argv
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=is_dev,
        reload_dirs=["core", "utils", "web"] if is_dev else None,
        reload_excludes=["*.log", "*.json", "logs/*", "config/*", "Debug/*"] if is_dev else None
    )

if __name__ == "__main__":
    main()
