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
        self.accounts = {}  # {acct_no: {appkey: ..., secretkey: ...}}
        self.mode = "mock"  # "mock" or "real"
        self.tokens = {}    # {acct_no: {"token": ..., "expiry": ...}}

        self.load_config()

    def load_config(self):
        """Load API key and mode configuration from config.json"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                api_settings = config.get("kiwoom_api", {})
                self.mode = api_settings.get("mode", "mock").lower()
                self.accounts = api_settings.get("accounts", {})
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
        
        # Get credentials for this specific account
        acct_keys = self.accounts.get(acct_no)
        if not acct_keys:
            log_error(f"계좌번호 '{acct_no}'에 해당하는 API Key 설정을 config.json에서 찾을 수 없습니다.")
            return ""

        appkey = acct_keys.get("appkey", "")
        secretkey = acct_keys.get("secretkey", "")

        if not appkey or not secretkey:
            log_error(f"계좌번호 '{acct_no}'의 AppKey 또는 SecretKey가 비어 있습니다.")
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

    def send_us_order(self, acct_no, is_buy=True, exchange="ND", symbol="", qty=0, price=0.0, order_type="00"):
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
            "ord_uv": str(price) if order_type not in ["03", "36", "37"] else "", # 시장가는 단가 빈값 처리
            "trde_tp": order_type
        }

        try:
            action_str = "매수" if is_buy else "매도"
            log_info(f"[{acct_no}] 미국주식 {action_str} 주문 요청 ({symbol}, {qty}주, 단가: {price}, 유형: {order_type})")
            response = requests.post(url, headers=headers, json=body, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                log_error(f"[{acct_no}] 주문 집행 실패 (HTTP Status {response.status_code}): {response.text}")
        except Exception as e:
            log_exception(f"[{acct_no}] 주문 집행 중 예외 발생: {e}")
        
        return None
