import logging
import asyncio
import os
import uuid
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

    def sync_task_balance(self, task_id: str):
        """
        특정 태스크의 키움증권 계좌 잔고를 조회하여 로컬 DB(trade_batches)와 정합성을 100% 동기화합니다.
        실전(자동/수동) 모드일 경우에만 실제 API 검증을 타며, 미연결 또는 오류 시 명확한 예외를 던집니다.
        """
        logger.info(f"태스크 {task_id} 잔고 동기화 시작")
        
        # 1. 런타임에 최신 설정 파일 동적 로드 (계좌 번호 변경 즉시 반영)
        self.config = self.db.load_json(self.config_path, default_data={"tasks": []})
        self.kiwoom_api.load_config()

        tasks = self.config.get("tasks", [])
        task = next((t for t in tasks if t.get("id") == task_id), None)
        if not task:
            raise ValueError(f"ID가 {task_id}인 태스크를 찾을 수 없습니다.")
            
        mode = task.get("operation_mode", "MOCK_VIRTUAL")
        ticker = task.get("ticker", "SOXL").upper().strip()
        acct_no = task.get("account_no", "").strip()
        
        # 1.5 퉁치기 정산 및 원본 티어 복원 (WaveSurfer 전략 전용)
        if task.get("strategy") == "SURFER_BATCH" and mode in ["REAL_AUTO", "REAL_MANUAL"]:
            try:
                import glob
                import json
                from collections import defaultdict
                from core.strategies.netting_handler import reconstruct_from_csv_and_json, simulate_hts_executions
                from utils.market_data import MarketDataManager
                
                # 어제 혹은 가장 최신의 정산되지 않은 netted.json 탐색 (최근 5일)
                netted_files = glob.glob(f"config/*_{ticker}_{task_id}_netted.json")
                unsettled_file = None
                target_date_str = None
                
                for fpath in sorted(netted_files, reverse=True):
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            rec = json.load(f)
                            if not rec.get("settled", False):
                                unsettled_file = fpath
                                fname = os.path.basename(fpath)
                                target_date_str = fname.split("_")[0]
                                break
                    except Exception as e:
                        logger.error(f"[정산] netted 파일 검사 오류 {fpath}: {e}")
                        
                if unsettled_file and target_date_str:
                    logger.info(f"[정산] '{target_date_str}' 일자의 미정산 퉁치기 내역 발견. 역산 정산 및 복원 시작...")
                    
                    mdm = MarketDataManager()
                    close_price = mdm.get_latest_close(ticker)
                    if close_price is None or close_price <= 0:
                        logger.error(f"[정산] {ticker}의 당일 종가를 로드하지 못해 정산을 보류합니다.")
                    else:
                        with open(unsettled_file, 'r', encoding='utf-8') as f:
                            rec = json.load(f)
                        
                        original_orders = rec.get("original_orders", [])
                        virtual_netted = rec.get("virtual_netted", [])
                        
                        # 1. HTS로 나갔던 실제 가상 주문 목록 취합
                        hts_dict = defaultdict(int)
                        market_qty = 0
                        for v in virtual_netted:
                            if v.get('is_market'):
                                market_qty += v['qty']
                            else:
                                hts_dict[(v['action'], v['price'])] += v['qty']
                        
                        hts_orders = []
                        for (action, price), qty in hts_dict.items():
                            if qty > 0:
                                hts_orders.append({
                                    'action': "BUY" if action == "매수" else "SELL",
                                    'price': price,
                                    'qty': qty,
                                    'ticker': ticker,
                                    'order_type': "30"
                                })
                        if market_qty > 0:
                            hts_orders.append({
                                'action': 'SELL',
                                'price': 0.0,
                                'qty': market_qty,
                                'ticker': ticker,
                                'order_type': "34"
                            })
                            
                        # 2. 당일 종가 기준 HTS 실제 체결 자가 시뮬레이션
                        csv_executions = simulate_hts_executions(hts_orders, close_price)
                        
                        # 3. 원본 티어 체결 복원 역산
                        orig_executions = reconstruct_from_csv_and_json(
                            ticker, task_id, csv_executions, target_date_str, close_price
                        )
                        
                        # 4. 로컬 DB 파일 로드
                        batches_file = f"config/trade_batches_{task_id}.json"
                        history_file = f"config/trade_history_{task_id}.json"
                        
                        current_batches = self.db.load_json(batches_file, default_data=[])
                        current_history = self.db.load_json(history_file, default_data=[])
                        
                        for exec_item in orig_executions:
                            exec_action = exec_item.get("action")
                            exec_qty = int(exec_item.get("qty", 0))
                            exec_price = float(exec_item.get("price", 0.0))
                            
                            if exec_action == "BUY":
                                new_batch = {
                                    "id": str(uuid.uuid4()),
                                    "buyPrice": exec_price,
                                    "qty": exec_qty,
                                    "cycleDays": 0,
                                    "buyMode": exec_item.get("mode", "안전모드"),
                                    "buyDate": target_date_str
                                }
                                current_batches.append(new_batch)
                                logger.info(f"[정산 복원] 매수 체결 복원 배치 추가: {new_batch}")
                                
                            elif exec_action == "SELL":
                                batch_id = exec_item.get("batch_id")
                                tier = exec_item.get("tier")
                                
                                target_batch = None
                                if batch_id:
                                    target_batch = next((b for b in current_batches if b.get("id") == batch_id), None)
                                if not target_batch and tier and len(current_batches) >= tier:
                                    target_batch = current_batches[tier - 1]
                                if not target_batch and current_batches:
                                    target_batch = current_batches[0]
                                    
                                if target_batch:
                                    buy_cost = target_batch["buyPrice"] * exec_qty
                                    sell_revenue = exec_price * exec_qty
                                    realized_profit = sell_revenue - buy_cost
                                    
                                    current_history.append({
                                        "date": target_date_str,
                                        "type": "SELL",
                                        "buyPrice": target_batch["buyPrice"],
                                        "sellPrice": exec_price,
                                        "qty": exec_qty,
                                        "realized_profit": realized_profit,
                                        "buyDate": target_batch.get("buyDate", ""),
                                        "buyMode": target_batch.get("buyMode", "안전모드")
                                    })
                                    
                                    if target_batch in current_batches:
                                        current_batches.remove(target_batch)
                                    logger.info(f"[정산 복원] 매도 체결 복원 배치 청산 (수익: ${realized_profit:.2f})")
                                    
                        self.db.save_json(batches_file, current_batches)
                        self.db.save_json(history_file, current_history)
                        
                        rec["settled"] = True
                        with open(unsettled_file, 'w', encoding='utf-8') as f:
                            json.dump(rec, f, ensure_ascii=False, indent=2)
                            
                        logger.info(f"[정산] '{target_date_str}' 퉁치기 복원 정산 완료 및 중복방지 마킹 처리 완료.")
            except Exception as e:
                logger.error(f"[정산] 퉁치기 정산 및 복원 처리 중 치명적 오류 발생: {e}")
        
        # 2. 가상 모드(MOCK_VIRTUAL)인 경우 수동 동기화 불가 예외 처리
        if mode == "MOCK_VIRTUAL":
            raise ValueError("[동기화 불가] 가상(MOCK_VIRTUAL) 모드로 구동 중인 태스크는 실제 증권사 계좌와 잔고를 동기화할 수 없습니다. 실전 수동 또는 실전 자동 모드로 설정해 주십시오.")
            
        # 3. 실전 모드(REAL_AUTO, REAL_MANUAL)인 경우 키움 API 연동성 체크 (1~100 엄격 검증)
        if not acct_no:
            raise ValueError("[계좌 연동 실패] 태스크에 계좌번호가 설정되어 있지 않습니다. 태스크 수정을 통해 계좌번호를 기입하십시오.")
            
        # 키움증권 config 내에 등록된 계좌인지 검증 (Key에 계좌번호가 들어가야 함)
        acct_info = self.kiwoom_api.accounts.get(acct_no)
        if not acct_info:
            raise ValueError(f"[계좌 검증 실패] 입력된 계좌번호 '{acct_no}'는 설정 파일의 accounts 목록에 등록되어 있지 않습니다. 설정 탭에서 계좌를 등록해 주십시오.")
            
        app_key = ""
        app_secret = ""
        if isinstance(acct_info, dict):
            app_key = acct_info.get("app_key", "").strip()
            app_secret = acct_info.get("app_secret", "").strip()
        else:
            # 구버전 호환용 글로벌 백업 key
            app_key = self.kiwoom_api.appkey
            app_secret = self.kiwoom_api.secretkey
            
        if not app_key or not app_secret:
            raise ValueError(f"[계좌 연동 실패] 계좌 '{acct_no}'에 바인딩된 키움 OpenAPI App Key 및 App Secret이 없습니다. 설정 탭에서 해당 계좌의 API Key를 기입해 주십시오.")

        # API 토큰 발급/로그인 검증
        token = self.kiwoom_api.get_token(acct_no, force_refresh=True)
        if not token:
            raise ConnectionError("[OAuth 로그인 실패] 키움증권 토큰 발급에 실패했습니다. 키움 App Key / App Secret 설정이 올바른지, 혹은 키움증권 API 서버가 점검 상태인지 확인하십시오.")
            
        # 미국주식 원장잔고조회 API 호출 (종목별 정확한 거래소 코드 자동 조회)
        exchange = self.kiwoom_api.get_exchange_for_symbol(acct_no, ticker)
        balance_res = self.kiwoom_api.get_us_balance(acct_no, exchange=exchange, symbol=ticker)
        if not balance_res:
            raise ConnectionError(f"[잔고 조회 실패] 키움증권 OpenAPI 서버로부터 {ticker} 잔고 조회 응답을 받지 못했습니다. 네트워크 연결 상태를 확인해 주십시오.")
            
        # API 오류 코드 감지
        if balance_res.get("rt_cd") and balance_res.get("rt_cd") != "0":
            err_msg = balance_res.get("msg1", "알 수 없는 API 에러")
            raise ConnectionError(f"[키움 API 에러] {err_msg} (코드: {balance_res.get('rt_cd')})")
            
        # 데이터 파싱 및 정합성 매핑 (신형 result_list 구조 및 구형 output1/output2 구조 하이브리드 지원)
        result_list = balance_res.get("result_list")
        output2 = balance_res.get("output2")
        output1 = balance_res.get("output1", {})
        
        target_stock = None
        
        # 1. 신형 result_list 에서 검색
        if isinstance(result_list, list):
            for item in result_list:
                if item.get("stk_cd", "").upper() == ticker:
                    target_stock = item
                    break
        
        # 2. 구형 output2 에서 검색 (fallback)
        if not target_stock and isinstance(output2, list):
            for item in output2:
                if item.get("stk_cd", "").upper() == ticker:
                    target_stock = item
                    break
                    
        # 3. 최상위 output1 에서 검색 (fallback)
        if not target_stock and output1.get("stk_cd", "").upper() == ticker:
            target_stock = output1
            
        # 잔고 값 갱신
        qty = 0
        pavg = 0.0
        if target_stock:
            # qty 수량 파싱 (실제 보유수량인 poss_qty를 최우선 순위로 획득하여 결제일 오차 방지)
            qty_raw = target_stock.get("poss_qty") or target_stock.get("qty") or target_stock.get("ccld_qty_smamt") or target_stock.get("stk_qty") or 0
            qty = int(qty_raw)
            
            # 평균단가 파싱 (frgn_stk_book_uv (장부단가) 또는 pavg 또는 pavg_num)
            pavg_raw = target_stock.get("frgn_stk_book_uv") or target_stock.get("pavg") or target_stock.get("pavg_num") or 0.0
            pavg = float(pavg_raw)
            
        # 예수금 잔액 (Running Cash)
        # 최상위 루트 필드(frcr_dncl_amt_2 등) 또는 output1 내부에서 획득
        dps_raw = balance_res.get("frcr_dncl_amt_2") or output1.get("frcr_dncl_amt_2") or balance_res.get("dps_amt") or output1.get("dps_amt") or 0.0
        running_cash = float(dps_raw)
        if running_cash <= 0.0:
            running_cash = float(task.get("seed_amt", 10000.0))
            
        # 4. 로컬 DB(trade_batches) 파일 델타 매칭 동기화 갱신 (기존 이력 보존)
        batches_file = f"config/trade_batches_{task_id}.json"
        
        if qty <= 0:
            # 보유 주식 없음 -> batches 비우기
            self.db.save_json(batches_file, [])
            logger.info(f"실계좌 {ticker} 보유량이 0주이므로 보유 배치를 모두 비웠습니다.")
        else:
            import datetime
            import uuid
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            
            # 기존 배치 로드
            current_batches = self.db.load_json(batches_file, default_data=[])
            current_total_qty = sum(int(b.get("qty", 0)) for b in current_batches)
            
            gap = qty - current_total_qty
            
            if gap == 0:
                # 수량이 완벽히 일치하면 기존 배치 히스토리 100% 보존
                logger.info(f"실계좌 {ticker} 수량({qty}주)이 기존 배치 합계와 일치하므로 배치를 그대로 보존합니다.")
                new_batches = current_batches
            elif gap > 0:
                # 실제 잔고가 더 많음 -> 기존 배치들 보존하고, 부족한 차이만큼만 보정 배치 신설 추가
                logger.info(f"실계좌 {ticker} 잔고 수량이 더 많음 ({current_total_qty}주 -> {qty}주). 차이 {gap}주 보정 배치 추가.")
                adjustment_batch = {
                    "id": f"bt_{str(uuid.uuid4())[:8]}",
                    "buyDate": today_str,
                    "buyPrice": pavg,
                    "qty": gap,
                    "buyMode": task.get("last_mode", "안전모드"),
                    "cycleDays": 0
                }
                new_batches = current_batches + [adjustment_batch]
            else:
                # 실제 잔고가 더 적음 -> 최신 배치부터 역순으로 수량을 깎거나 삭제하여 일치시킴
                logger.info(f"실계좌 {ticker} 잔고 수량이 더 적음 ({current_total_qty}주 -> {qty}주). 차이 {abs(gap)}주 차감 조정.")
                new_batches = []
                remaining_to_remove = abs(gap)
                
                # 최신 배치가 뒤에 있으므로 뒤에서부터 차감
                for b in reversed(current_batches):
                    b_qty = int(b.get("qty", 0))
                    if remaining_to_remove <= 0:
                        new_batches.insert(0, b)
                    elif b_qty <= remaining_to_remove:
                        # 배치 통째로 삭제
                        remaining_to_remove -= b_qty
                    else:
                        # 배치 수량 일부 차감
                        b["qty"] = b_qty - remaining_to_remove
                        remaining_to_remove = 0
                        new_batches.insert(0, b)
            
            self.db.save_json(batches_file, new_batches)
            logger.info(f"실계좌 {ticker} 잔고 동기화 완료: {qty}주 @ ${pavg} (배치 수: {len(new_batches)})")
            
        return {
            "status": "success",
            "message": f"계좌 {acct_no} 잔고 동기화 성공! ({ticker} 보유량: {qty}주, 평단가: ${pavg:.2f})"
        }

    async def sync_contracts(self):
        """
        스케줄러 작동용: 전체 활성 태스크들의 실제 계좌 잔고를 자동 동기화합니다.
        """
        logger.info("일일 자동 계좌 잔고 동기화 프로세스 시작")
        tasks = self.config.get("tasks", [])
        
        summary_msg = "🔄 <b>일일 계좌 잔고 동기화 결과</b>\n"
        for task in tasks:
            if not task.get("is_active", True):
                continue
            task_id = task.get("id")
            nickname = task.get("nickname", task_id)
            
            try:
                res = self.sync_task_balance(task_id)
                summary_msg += f"- {nickname}: {res.get('message')}\n"
            except Exception as e:
                logger.error(f"{task_id} 자동 동기화 실패: {e}")
                summary_msg += f"- {nickname}: 동기화 실패 ({str(e)})\n"
                
        await self.telegram.send_message(summary_msg)

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
