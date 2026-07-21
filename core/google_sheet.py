import gspread
import json
import os
import time
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from utils.logger import log_info, log_error, log_exception, log_debug
from utils.path_handler import get_app_data_path

class GoogleSheetManager:
    def __init__(self, key_path=None, config_path=None):
        self.key_path = key_path or get_app_data_path('config/google_key.json')
        self.config_path = config_path or get_app_data_path('config/config.json')
        self.client = None
        self.doc = None
        
        # 설정 파일에서 시트 ID 로드
        self.sheet_id = ""
        self.load_config()

    def load_config(self):
        # config.json 찾기 (현재 경로 -> 상위 경로 순서)
        path = self.config_path
        if not os.path.exists(path):
            parent_path = os.path.join("..", self.config_path)
            if os.path.exists(parent_path):
                path = parent_path
        
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sheet_id = data.get('sheet_id', '')
            except Exception as e:
                log_error(f"[Sheet] 설정 로드 오류: {e}")

    def connect(self, max_retries=3):
        """구글 시트 API 연결 (지수 백오프 적용)"""
        for attempt in range(max_retries):
            try:
                # [Scope 최신화]
                scope = [
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
                
                key_file = self.key_path
                if not os.path.exists(key_file):
                     parent_key = os.path.join("..", self.key_path)
                     if os.path.exists(parent_key):
                         key_file = parent_key
                
                if attempt == 0:
                    log_debug(f"[Sheet] Key File Path: {os.path.abspath(key_file)}")

                creds = ServiceAccountCredentials.from_json_keyfile_name(key_file, scope)
                self.client = gspread.authorize(creds)
                
                if self.sheet_id:
                    self.doc = self.client.open_by_key(self.sheet_id)
                    log_info(f"[Sheet] 구글 시트 연결 성공. (시도: {attempt + 1}/{max_retries})")
                    return True
                else:
                    log_error("[Sheet] 설정에 시트 ID가 없습니다.")
                    return False
            except Exception as e:
                # 지수 백오프 대기 시간 계산 (1초, 2초, 4초...)
                wait_time = 2 ** attempt 
                log_error(f"[Sheet] 연결 시도 {attempt + 1}/{max_retries} 실패: {e} (재시도 대기: {wait_time}초)")
                
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                else:
                    import traceback
                    log_error(f"[Sheet] 최종 연결 오류: {e}")
                    log_error(traceback.format_exc())
        return False

    def get_sheet_by_index(self, index, retry=True):
        if not self.doc:
            if not self.connect():
                return None
        try:
            return self.doc.get_worksheet(index)
        except Exception as e:
            log_error(f"[Sheet] Get Worksheet Index({index}) Error: {e}")
            if retry:
                log_info(f"[Sheet] 연결 세션 만료 의심 -> 재연결 후 즉시 재시도 (Index: {index})")
                self.doc = None # 재연결 유도
                return self.get_sheet_by_index(index, retry=False)
            return None

    def get_sheet_by_name(self, name, retry=True):
        if not self.doc:
            if not self.connect():
                return None
        try:
            return self.doc.worksheet(name)
        except Exception as e:
            log_error(f"[Sheet] 시트 '{name}'을(를) 찾을 수 없습니다: {e}")
            
            # 통신 오류나 세션 만료인 경우 재시도
            if retry:
                log_info(f"[Sheet] 연결 세션 만료 또는 통신 오류 감지 -> 재연결 후 즉시 재시도 (Name: {name})")
                self.doc = None  # 재연결 유도
                return self.get_sheet_by_name(name, retry=False)
                
            if self.doc:
                try:
                    available = [w.title for w in self.doc.worksheets()]
                    log_info(f"[Sheet] 사용 가능한 시트 목록: {available}")
                except:
                    log_error("[Sheet] 시트 목록 로드 실패 (연결 세션 완전 만료)")
                    self.doc = None
            return None

    # ------------------------------------------------------------------
    # [시트 1] 동파 주문 (인덱스 0)
    # 로직: I열(인덱스 8)이 'TRUE'인지 확인 -> J~O열 읽기
    # ------------------------------------------------------------------
    def read_dongpa_orders(self, sheet_name=None):
        if sheet_name:
            sheet = self.get_sheet_by_name(sheet_name)
        else:
            sheet = self.get_sheet_by_index(0)
            
        if not sheet: return []

        orders = []
        try:
            # 셀 단위보다 전체 값을 가져오는 것이 빠름
            all_values = sheet.get_all_values()
            
            # 헤더 제외하고 반복 (실제 데이터 위치에 따라 조정 필요, 일단 3행 이후로 가정)
            for idx, row in enumerate(all_values):
                if idx < 3: continue 
                
                # 행 길이 안전 검사
                if len(row) < 15: continue 
                
                trigger = row[8].strip().upper() # I열
                if trigger == 'TRUE':
                    # 주문 정보 파싱 (J~O -> 인덱스 9~14)
                    order_info = {
                        'row_idx': idx + 1, # 업데이트용 1-based 인덱스
                        'code': row[9],     # J (종목코드)
                        'type': row[10],    # K (매수/매도)
                        'method': row[11],  # L (거래방법)
                        'price': row[12],   # M (주문가)
                        'qty': row[13],     # N (주문량)
                        'account': row[6]   # G (계좌번호 - 가정)
                    }
                    orders.append(order_info)
        except Exception as e:
            print(f"[Dongpa] 읽기 오류: {e}")
        
        return orders

    # ------------------------------------------------------------------
    # [시트 2] 무한 매수 (인덱스 1)
    # 로직: O열(인덱스 14)이 'TRUE'인지 확인 -> P~U열 읽기
    # 선행: 영웅문 상태로 K열(인덱스 10) 업데이트
    # ------------------------------------------------------------------
    def get_infinite_account(self):
        """무한 매수 시트(인덱스 1)의 G2(2행 7열)에서 계좌번호를 가져옴"""
        sheet = self.get_sheet_by_index(1)
        if not sheet: return ""
        try:
            # G2 셀 (2행 7열)
            return sheet.cell(2, 7).value.strip()
        except Exception as e:
            print(f"[Infinite] 계좌번호 읽기 오류: {e}")
            return ""

    def update_infinite_status(self, row_idx, data):
        """
        data = [매입금액, 평균단가, 보유수량, 수익률]
        K, L, M, N 열 (인덱스 10, 11, 12, 13) 업데이트
        """
        sheet = self.get_sheet_by_index(1)
        if not sheet: return
        
        # update_cell 사용 (row_idx는 1부터 시작)
        try:
            # 데이터 순서: K, L, M, N
            for i, val in enumerate(data):
                sheet.update_cell(row_idx, 11 + i, val)
        except Exception as e:
            print(f"[Infinite] 업데이트 오류: {e}")

    def read_infinite_orders(self, sheet_name=None):
        """
        무한매수 시트에서 O~U열 정보를 읽어옴
        O(14): 실행여부, P(15): 매수/매도, Q(16): 거래방법, S(18): 단가, U(20): 수량
        """
        if sheet_name:
            sheet = self.get_sheet_by_name(sheet_name)
        else:
            sheet = self.get_sheet_by_index(1)
            
        if not sheet: return []

        orders = []
        try:
            # E6(계좌 인덱스)와 E11(종목코드)는 공통으로 사용
            acc_idx = sheet.cell(6, 5).value or "1"
            stock_code = (sheet.cell(11, 5).value or "").strip().upper()
            
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values):
                if idx < 4: continue # 데이터는 보통 5행(idx 4)부터 시작하거나 그 이후
                if len(row) < 21: continue
                
                trigger = row[14].strip().upper() # O열 (인덱스 14)
                if trigger == 'TRUE':
                    order_info = {
                        'row_idx': idx + 1,
                        'account_idx': acc_idx, # E6 공통 계좌
                        'code': stock_code,     # E11 공통 종목
                        'type': "BUY" if "매수" in row[15] else "SELL", # P열
                        'method': row[16].strip() or "LOC",              # Q열
                        'price': row[18].replace(',', '').strip(),       # S열
                        'qty': row[20].replace(',', '').strip(),         # U열
                    }
                    if order_info['code'] and order_info['qty'] != "0":
                        orders.append(order_info)
                        print(f"[Infinite] 주문 로드: 행 {idx+1} ({order_info['type']}, {order_info['qty']}주)")
            
            print(f"[Infinite] 총 {len(orders)}건의 주문 요청 감지 ({sheet_name}, O~U열)")
        except Exception as e:
            print(f"[Infinite] 주문 목록 읽기 오류: {e}")
            
        return orders

    def get_account_from_sheet(self, sheet_name):
        """지정한 시트의 G2(2행 7열)에서 계좌번호를 가져옴"""
        sheet = self.get_sheet_by_name(sheet_name)
        if not sheet: return ""
        try:
            return sheet.cell(2, 7).value.strip()
        except:
            return ""
    
    # ------------------------------------------------------------------
    # [시트 주문] 관련 (사용자 커스텀 워크플로우)
    # ------------------------------------------------------------------
    def get_balance_request(self, sheet_name="시트 주문"):
        """E7 체크박스 확인 후 S4(계좌), T4(종목) 반환"""
        sheet = self.get_sheet_by_name(sheet_name)
        if not sheet: return None
        try:
            # E7 (7행 5열)
            v = sheet.cell(7, 5).value
            trigger = v.strip().upper() if v else ""
            if trigger == 'TRUE':
                # S4 (4행 19열), T4 (4행 20열)
                v_acc = sheet.cell(4, 19).value
                v_code = sheet.cell(4, 20).value
                account_no = v_acc.strip() if v_acc else ""
                stock_code = v_code.strip() if v_code else ""
                log_info(f"[Sheet] 잔고 조회 요청 감지: 계좌={account_no}, 종목={stock_code}")
                return account_no, stock_code
            return None
        except Exception as e:
            log_error(f"[Sheet] 잔고 요청 확인 중 오류: {e}")
            return None

    def get_vr_reservation_dates(self, sheet_name="시트 주문"):
        """E9(예약시작일), E11(예약종료일) 파싱 반환 (값 없으면 None, None 반환)"""
        sheet = self.get_sheet_by_name(sheet_name)
        if not sheet: return None, None
        try:
            # E9 (9행 5열), E11 (11행 5열)
            v_start = sheet.cell(9, 5).value
            v_end = sheet.cell(11, 5).value
            
            start_date = v_start.strip() if v_start else ""
            end_date = v_end.strip() if v_end else ""
            
            # 입력 데이터가 없으면 None 반환
            if not start_date or not end_date:
                return None, None
                
            # [날짜 8자리 YYYYMMDD 정규화 패치]
            # 구글 시트가 "2026. 2. 27" 이나 "2026-2-27" 같이 한자리 숫자로 뱉을 경우 
            # 앞자리에 '0'을 채워 반드시 8자리가 되도록 파싱합니다.
            import re
            
            def parse_to_8digits(date_str):
                # 숫자만 모두 추출 (예: '2026', '2', '27')
                nums = re.findall(r'\d+', str(date_str))
                if len(nums) >= 3:
                    y = nums[0]
                    m = nums[1].zfill(2) # '2' -> '02'
                    d = nums[2].zfill(2) # '7' -> '07'
                    return f"{y}{m}{d}"
                return "".join(nums) # 예외적인 붙은 문자열인 경우 그대로 반환

            start_date_clean = parse_to_8digits(start_date)
            end_date_clean = parse_to_8digits(end_date)
            
            log_info(f"[Sheet] VR 예약 기간 세팅: 시작일={start_date_clean}, 종료일={end_date_clean}")
            return start_date_clean, end_date_clean
        except Exception as e:
            log_error(f"[Sheet] 예약 기간 데이터 파싱 오류: {e}")
            return None, None

    def read_sheet_orders(self, sheet_name="시트 주문"):
        """I~O열을 읽어 I열이 TRUE인 행들을 주문 목록으로 반환 (4행부터 데이터 시작)"""
        sheet = self.get_sheet_by_name(sheet_name)
        if not sheet: 
            log_error(f"[Sheet] 시트 '{sheet_name}'을 찾을 수 없어 주문을 읽지 못했습니다.")
            return []
        
        orders = []
        try:
            all_values = sheet.get_all_values()
            
            # 4행부터 데이터 시작 (0-based idx 3)
            for idx, row in enumerate(all_values):
                if idx < 3: continue 
                if len(row) < 15: continue # O열까지 있어야 함 (idx 14)
                
                # I열 (인덱스 8) 확인: 체크박스가 'TRUE'인 경우만 로드
                v_trigger = row[8].strip().upper() if len(row) > 8 else ""
                if v_trigger == 'TRUE':
                    order_info = {
                        'row_idx': idx + 1,
                        'account_idx': row[9].strip() if len(row) > 9 else "1", # J (계좌 순번, 기본값 1)
                        'code': row[10].strip() if len(row) > 10 else "",       # K (종목코드)
                        'type': "BUY" if len(row) > 11 and "매수" in row[11] else "SELL", # L (구분)
                        'method': row[12].strip() if len(row) > 12 else "지정가",     # M (거래방법)
                        'price': row[13].replace(',', '').strip() if len(row) > 13 else "0",    # N (주문가)
                        'qty': row[14].replace(',', '').strip() if len(row) > 14 else "0",      # O (주문량)
                    }
                    # 유효한 종목코드가 있는 경우만 추가
                    if order_info['code']:
                        orders.append(order_info)
                        log_debug(f"[Sheet] 주문 로드 완료: 행 {order_info['row_idx']} ({order_info['code']}, {order_info['type']})")
            
            if orders:
                log_info(f"[Sheet] 총 {len(orders)}건의 주문 요청 감지 ({sheet_name}, I~O열)")
            return orders
        except Exception as e:
            log_exception(f"[Sheet] 주문 목록 읽기 오류 ({sheet_name}): {e}")
            return []

    def get_telegram_config(self, sheet_name="시트 주문"):
        """[시트 주문] 전용: E20(ID), E22(Token), E24(Message) 반환 (일괄 조회)"""
        sheet = self.get_sheet_by_name(sheet_name)
        if not sheet: return None, None, None
        try:
            # E20:E24 영역을 한 번에 읽음 (5행 x 1열)
            # 리스트 형식: [['ID'], [''], ['Token'], [''], ['Message']]
            rows = sheet.get_values('E20:E24')
            
            chat_id = rows[0][0].strip() if len(rows) > 0 and len(rows[0]) > 0 else ""
            token = rows[2][0].strip() if len(rows) > 2 and len(rows[2]) > 0 else ""
            message = rows[4][0].strip() if len(rows) > 4 and len(rows[4]) > 0 else ""
            
            log_debug(f"[Sheet] 텔레그램 설정 일괄 로드 완료 ({sheet_name})")
            return chat_id, token, message
        except Exception as e:
            log_error(f"[Sheet] 텔레그램 설정 일괄 조회 오류 ({sheet_name}): {e}")
            return None, None, None

    def get_infinite_telegram_config(self, sheet_name):
        """[무한 매수] 전용: E26(ID), E28(Token), E30(Message) 반환 (일괄 조회)"""
        sheet = self.get_sheet_by_name(sheet_name)
        if not sheet: return None, None, None
        try:
            # E26:E30 영역 일괄 조회
            rows = sheet.get_values('E26:E30')
            
            chat_id = rows[0][0].strip() if len(rows) > 0 and len(rows[0]) > 0 else ""
            token = rows[2][0].strip() if len(rows) > 2 and len(rows[2]) > 0 else ""
            message = rows[4][0].strip() if len(rows) > 4 and len(rows[4]) > 0 else ""
            
            log_debug(f"[Sheet] 무한매수 텔레그램 설정 일괄 로드 완료 ({sheet_name})")
            return chat_id, token, message
        except Exception as e:
            log_error(f"[Sheet] 무한매수 텔레그램 일괄 조회 오류 ({sheet_name}): {e}")
            return None, None, None

    def clear_order_triggers(self, row_indices, sheet_name="시트 주문"):
        """주문 완료된 행들의 I열 체크박스 해제"""
        sheet = self.get_sheet_by_name(sheet_name)
        if not sheet: return
        try:
            for row_idx in row_indices:
                sheet.update_cell(row_idx, 9, "FALSE") # I열 (9열)
            print(f"[Sheet] {len(row_indices)}건의 주문 트리거 해제 완료 ({sheet_name})")
        except Exception as e:
            print(f"[Sheet] 주문 트리거 해제 오류: {e}")

    def clear_infinite_order_triggers(self, row_indices, sheet_name):
        """무한매수 주문 완료된 행들의 O열 체크박스 해제"""
        sheet = self.get_sheet_by_name(sheet_name)
        if not sheet: return
        try:
            for row_idx in row_indices:
                sheet.update_cell(row_idx, 15, "FALSE") # O열 (15열)
            print(f"[Sheet] {len(row_indices)}건의 무한매수 트리거 해제 완료 ({sheet_name})")
        except Exception as e:
            print(f"[Sheet] 무한매수 트리거 해제 오류: {e}")

    def get_order_request(self, sheet_name="시트 주문"):
        """(기존 E11 방식 - 호환성 위해 유지하거나 제거 가능)"""
        # 현재는 I~O열 방식(read_sheet_orders)을 주로 사용하므로 로그만 남김
        return None

    def clear_order_request(self, sheet_name="시트 주문"):
        """주문 실행 후 E11 체크박스 해제"""
        sheet = self.get_sheet_by_name(sheet_name)
        if not sheet: return
        try:
            sheet.update_cell(11, 5, "FALSE")
            print("[Sheet] 주문 요청 체크박스 해제 (E11)")
        except: pass

    def clear_balance_request(self, sheet_name="시트 주문"):
        """잔고 조회 후 E7 체크박스 해제 (사용자 요청에 따라 해제하지 않음)"""
        sheet = self.get_sheet_by_name(sheet_name)
        if not sheet: return
        try:
            # sheet.update_cell(7, 5, "FALSE")
            print("[Sheet] 잔고 조회 요청 체크박스 해제 건너뜐 (사용자 설정)")
        except: pass

    def update_balance_result(self, data, sheet_name="시트 주문"):
        """
        U4-Y4 영역 업데이트
        U: 최근조회, V: 잔고변동일, W: 보유량, X: 현재가, Y: 매입가
        """
        sheet = self.get_sheet_by_name(sheet_name)
        if not sheet: return False
        try:
            # [사용자 요청 포맷] '2026-01-13 18:13' (YYYY-MM-DD HH:MM)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # 1. 날짜 업데이트 (U, V)
            # 주의: 데이터가 너무 빈번하게 갱신되면 Sheets API Quota에 걸릴 수 있음
            sheet.update_cell(4, 21, now_str) # U (21열) - 최근 조회
            sheet.update_cell(4, 22, now_str) # V (22열) - 잔고 변동일
            
            # 2. 데이터 업데이트 (W, X, Y)
            # data 순서: [보유량, 현재가, 매입가]
            for i, val in enumerate(data):
                if i < 3:
                    sheet.update_cell(4, 23 + i, val) # W(23), X(24), Y(25)
            
            print(f"[Sheet] 잔고 조회 결과 시트 업데이트 완료 ({now_str})")
            return True
        except Exception as e:
            print(f"[Sheet] 시트 결과 업데이트 오류: {e}")
            return False

    def update_infinite_buy_result(self, data, sheet_name):
        """
        K6, K12, K14 영역 업데이트 (무한매수 전용)
        K6: 총 매입금액, K12: 평균 단가, K14: 보유 수량
        """
        sheet = self.get_sheet_by_name(sheet_name)
        if not sheet: return False
        try:
            # data = {"K6": val, "K12": val, "K14": val}
            sheet.update_acell('K6', data.get("K6", "0"))
            sheet.update_acell('K12', data.get("K12", "0"))
            sheet.update_acell('K14', data.get("K14", "0"))
            sheet.update_acell('K16', data.get("K16", "0"))
            print(f"[Sheet] 무한매수 잔고 업데이트 완료 ({sheet_name})")
            return True
        except Exception as e:
            print(f"[Sheet] 무한매수 결과 업데이트 오류: {e}")
            return False

    # ------------------------------------------------------------------
    # [시트 3] 로그 (인덱스 2)
    # ------------------------------------------------------------------
    def add_log(self, message):
        sheet = self.get_sheet_by_index(2)
        if not sheet: return
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, message])
        except Exception as e:
            print(f"[Sheet Log] 오류: {e}")
