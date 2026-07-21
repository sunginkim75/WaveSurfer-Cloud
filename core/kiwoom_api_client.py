# -*- coding: utf-8 -*-
"""
Kiwoom REST API Client for US Stock Trading and Account Balance Sync (Multi-Account Support).
"""
import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta

# 로거 모듈이 없을 경우를 대비한 콘솔 출력 대체제 (Headless CLI 최적화)
try:
    from utils.path_handler import get_resource_path, get_app_data_path
    from utils.logger import log_info, log_error, log_exception
except ImportError:
    def log_info(msg): print(f"[INFO] {msg}")
    def log_error(msg): print(f"[ERROR] {msg}")
    def log_exception(msg): print(f"[EXCEPTION] {msg}")

class KiwoomAPIClient:
    def __init__(self, config_path=None):
        if config_path is None:
            # 1. PyInstaller 빌드 환경인 경우 실행 파일(.exe) 위치 기준
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            # 2. 일반 개발 환경(VS Code 등)인 경우 현재 파일 위치 기준
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            config_path = os.path.join(base_dir, "config", "config.json")
        
        self.config_path = config_path
        self.accounts = {}  # {acct_no: account_name}
        self.mode = "mock"  # "mock" or "real"
        self.appkey = ""
        self.secretkey = ""
        self.tokens = {}    # {acct_no: {"token": ..., "expiry": ...}}
        self._exchange_cache = {}  # {symbol: stex_tp} - 종목별 거래소 캐시

        self.load_config()

    def load_config(self):
        """Load API key and mode configuration from config.json"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                self.mode = config.get("server", {}).get("mode", "mock").lower()
                # 하위 호환용 글로벌 백업 key
                self.appkey = config.get("kiwoom", {}).get("app_key", "")
                self.secretkey = config.get("kiwoom", {}).get("app_secret", "")
                
                # accounts는 이제 {acct_no: {"nickname": "...", "app_key": "...", "app_secret": "..."}} 형태 또는 구버전 {acc_1: "계좌번호"} 형태일 수 있음
                self.accounts = config.get("accounts", {})
                log_info(f"Kiwoom API Client 설정 로드 완료 (모드: {self.mode}, 등록 계좌 수: {len(self.accounts)})")
            else:
                log_error(f"설정 파일({self.config_path})을 찾을 수 없습니다.")
        except Exception as e:
            log_exception(f"설정 로드 중 예외 발생: {e}")

    @property
    def base_url(self):
        """Return target domain based on mode setting"""
        if self.mode == "real":
            return "https://api.kiwoom.com"
        else:
            return "https://mockapi.kiwoom.com"

    def get_token(self, acct_no, force_refresh=False):
        """Fetch OAuth2 token for a specific account. Reuses cached token if valid."""
        acct_no = str(acct_no).strip()
        
        # Check cache
        acct_token_info = self.tokens.get(acct_no, {})
        cached_token = acct_token_info.get("token")
        cached_expiry = acct_token_info.get("expiry")

        if not force_refresh and cached_token and cached_expiry and datetime.now() < cached_expiry - timedelta(seconds=60):
            return cached_token

        log_info(f"[{acct_no}] 계좌 접근 토큰 발급/갱신 요청 시도...")
        
        # 계좌 개별 정보 획득
        acct_info = self.accounts.get(acct_no)
        
        appkey = ""
        secretkey = ""
        
        if isinstance(acct_info, dict):
            appkey = acct_info.get("app_key", "").strip()
            secretkey = acct_info.get("app_secret", "").strip()
        else:
            # Fallback for old schema
            appkey = self.appkey
            secretkey = self.secretkey

        if not appkey or not secretkey:
            log_error(f"[{acct_no}] 계좌별 Kiwoom AppKey 또는 SecretKey가 설정되지 않았습니다.")
            return ""

        url = f"{self.base_url}/oauth2/token"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "api-id": "au10001"
        }
        body = {
            "grant_type": "client_credentials",
            "appkey": appkey,
            "secretkey": secretkey
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            if response.status_code == 200:
                res_data = response.json()
                token = res_data.get("token", "")
                expires_dt_str = res_data.get("expires_dt", "")
                
                if token and expires_dt_str:
                    try:
                        expiry = datetime.strptime(expires_dt_str, "%Y%m%d%H%M%S")
                        log_info(f"[{acct_no}] 토큰 발급 성공. 만료 예정일시: {expiry}")
                    except ValueError:
                        expiry = datetime.now() + timedelta(hours=1)
                        log_info(f"[{acct_no}] 토큰 만료시간 파싱 실패로 임시 만료시간(1시간) 설정.")
                    
                    # Cache the token
                    self.tokens[acct_no] = {
                        "token": token,
                        "expiry": expiry
                    }
                    return token
                else:
                    log_error(f"[{acct_no}] 응답 데이터 형식 오류: {res_data}")
            else:
                log_error(f"[{acct_no}] 토큰 발급 실패 (HTTP Status {response.status_code}): {response.text}")
        except Exception as e:
            log_exception(f"[{acct_no}] 토큰 발급 중 예외 발생: {e}")
        
        return ""

    def get_us_balance(self, acct_no, exchange="ND", symbol=""):
        """
        미국주식 원장잔고확인 (ust21070)
        - acct_no: 10자리 계좌번호
        - exchange (stex_tp): ND(나스닥), NY(뉴욕), NA(아멕스)
        - symbol (stk_cd): 종목코드 (TQQQ 등)
        """
        acct_no = str(acct_no).strip()
        token = self.get_token(acct_no)
        if not token:
            log_error(f"[{acct_no}] 유효한 토큰이 없어 잔고 조회를 수행할 수 없습니다.")
            return None

        url = f"{self.base_url}/api/us/acnt"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "api-id": "ust21070",
            "authorization": f"Bearer {token}"
        }
        body = {
            "stex_tp": exchange,
            "stk_cd": symbol.upper().strip()
        }

        try:
            log_info(f"[{acct_no}] 원장잔고조회 요청: {exchange} / {symbol}")
            response = requests.post(url, headers=headers, json=body, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                log_error(f"[{acct_no}] 원장잔고조회 실패 (HTTP Status {response.status_code}): {response.text}")
        except Exception as e:
            log_exception(f"[{acct_no}] 원장잔고조회 중 예외 발생: {e}")
        
        return None

    def get_exchange_for_symbol(self, acct_no, symbol):
        """
        종목코드에 맞는 거래소 구분(stex_tp)을 반환.
        - 알려진 종목은 하드코딩 테이블에서 즉시 반환 (API 호출 없음)
        - 그 외 종목은 키움 API(USA10099)로 자동 조회 후 캐시
        - 조회 실패 시 'NY' 기본값 반환
        """
        symbol = symbol.upper().strip()

        # ── 하드코딩 테이블 (자주 쓰는 종목) ──────────────────────────
        KNOWN_EXCHANGE = {
            # NYSE Arca (NY) ETF
            "SOXL": "NY", "SOXS": "NY",
            "TQQQ": "NY", "SQQQ": "NY",
            "SPXL": "NY", "SPXS": "NY",
            "LABU": "NY", "LABD": "NY",
            "FNGU": "NY", "FNGD": "NY",
            "TECL": "NY", "TECS": "NY",
            "UPRO": "NY", "SPXU": "NY",
            "TNA":  "NY", "TZA":  "NY",
            "UDOW": "NY", "SDOW": "NY",
            "FAS":  "NY", "FAZ":  "NY",
            "CURE": "NY", "ERX":  "NY",
            "SPY":  "NY", "QQQ":  "ND",
            "IWM":  "NY", "DIA":  "NY",
            "GLD":  "NY", "SLV":  "NY",
            # NASDAQ (ND)
            "AAPL": "ND", "MSFT": "ND", "NVDA": "ND",
            "AMZN": "ND", "META": "ND", "GOOG": "ND",
            "TSLA": "ND", "AVGO": "ND",
            # NYSE (NY)
            "BRK.B": "NY", "JPM": "NY", "V": "NY",
        }

        if symbol in KNOWN_EXCHANGE:
            log_info(f"[{symbol}] 거래소 하드코딩 테이블 사용: {KNOWN_EXCHANGE[symbol]}")
            return KNOWN_EXCHANGE[symbol]

        # ── 캐시 확인 ──────────────────────────────────────────────────
        if symbol in self._exchange_cache:
            return self._exchange_cache[symbol]

        # ── API 자동 조회 (USA10099) ────────────────────────────────────
        acct_no = str(acct_no).strip()
        token = self.get_token(acct_no)
        if not token:
            log_error(f"거래소 조회용 토큰 없음. 기본값 NY 사용.")
            return "NY"

        for exch in ["ND", "NY", "NA"]:
            url = f"{self.base_url}/api/us/stk"
            headers = {
                "Content-Type": "application/json;charset=UTF-8",
                "api-id": "USA10099",
                "authorization": f"Bearer {token}"
            }
            body = {"stex_tp": exch, "stk_cd": symbol}
            try:
                resp = requests.post(url, headers=headers, json=body, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("return_code") == 0 and data.get("stk_cd"):
                        log_info(f"[{symbol}] 거래소 API 조회 성공: {exch}")
                        self._exchange_cache[symbol] = exch
                        return exch
            except Exception as e:
                log_exception(f"거래소 조회 중 예외: {e}")

        log_error(f"[{symbol}] 거래소 API 조회 실패. 기본값 NY 사용.")
        self._exchange_cache[symbol] = "NY"
        return "NY"


    def send_us_order(self, acct_no, is_buy=True, exchange=None, symbol="", qty=0, price=0.0, order_type="00"):
        """
        미국주식 주문 집행 (ust20000: 매수, ust20001: 매도)
        - acct_no: 10자리 계좌번호
        - is_buy: True 이면 매수(ust20000), False 이면 매도(ust20001)
        - exchange (stex_tp): ND, NY, NA
        - symbol (stk_cd): 종목명 (TQQQ 등)
        - qty (ord_qty): 주문 수량
        - price (ord_uv): 주문 단가
        - order_type (trde_tp): 00(지정가), 03(시장가), 30(LOC) 등
        """
        acct_no = str(acct_no).strip()
        token = self.get_token(acct_no)
        if not token:
            log_error(f"[{acct_no}] 유효한 토큰이 없어 주문을 집행할 수 없습니다.")
            return None

        # exchange가 지정되지 않은 경우 자동 조회 (하드코딩 테이블 우선, 없으면 API)
        if not exchange:
            exchange = self.get_exchange_for_symbol(acct_no, symbol)

        # ── mock 모드에서는 LOC(30)/MOC(34) → 지정가(00)로 자동 변환 ──
        # 모의투자는 LOC/MOC 주문이 장마감 직전 특정 시간대에만 접수되므로
        # 테스트 편의를 위해 지정가로 대체
        effective_order_type = order_type
        if self.mode == "mock" and order_type in ["30", "34"]:
            effective_order_type = "00"
            log_info(f"[mock] 주문유형 {order_type}(LOC/MOC) → 00(지정가)로 자동 변환")

        api_id = "ust20000" if is_buy else "ust20001"
        url = f"{self.base_url}/api/us/ordr"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "api-id": api_id,
            "authorization": f"Bearer {token}"
        }
        
        body = {
            "stex_tp": exchange,
            "stk_cd": symbol.upper().strip(),
            "ord_qty": str(qty),
            "ord_uv": str(price) if effective_order_type not in ["03", "36", "37"] else "",
            "trde_tp": effective_order_type
        }

        try:
            action_str = "매수" if is_buy else "매도"
            log_info(f"[{acct_no}] 미국주식 {action_str} 주문 요청 ({symbol}, {qty}주, 단가: {price}, 유형: {effective_order_type}, 거래소: {exchange})")
            response = requests.post(url, headers=headers, json=body, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                log_error(f"[{acct_no}] 주문 집행 실패 (HTTP Status {response.status_code}): {response.text}")
        except Exception as e:
            log_exception(f"[{acct_no}] 주문 집행 중 예외 발생: {e}")
        
        return None
