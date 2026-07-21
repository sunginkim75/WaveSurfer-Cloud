# -*- coding: utf-8 -*-
"""
수동 퉁치기 및 원본 티어 복원 핸들러 (netting_handler.py)
- 사용자 구글 시트(Apps Script)의 퉁치기 및 복원 연산 공식을 파이썬 백엔드 코어 모듈로 1:1 완벽 포팅 완료.
- 구글 시트와 100% 무관하게, 로컬 파일 시스템 상에서 단독으로 퉁치기 가상 대조표를 생성 및 역산 정산합니다.
"""
import os
import json
import uuid
import datetime
from collections import defaultdict
from utils.logger import log_info, log_error, log_exception

def process_and_save_netted_orders(ticker: str, task_id: str, original_orders: list, date_str: str) -> list:
    """
    오늘 발생시킬 원본 주문 목록(original_orders)을 상호 상쇄(퉁치기)하여
    실제 HTS(증권사 API)로 전송할 압축 주문 목록(hts_orders)을 리턴하고,
    가상 퉁치기 대조표를 json 파일로 저장합니다.
    """
    buys = []
    sells = []

    # 1. 주문 데이터 복사 및 초기화
    for i, o in enumerate(original_orders):
        # o에는 'action', 'price', 'qty', 'tier' 등이 들어있음
        o_copy = o.copy()
        o_copy['id'] = f"orig_{ticker}_{task_id}_{i}_{str(uuid.uuid4())[:4]}"
        
        # 원래 dict에도 식별용 id 바인딩
        o['id'] = o_copy['id']

        price_val = o_copy.get('price', 0.0)
        # 시장가 판별
        if price_val == '시장가' or price_val == 0.01 or o_copy.get('order_type') == '34' or o_copy.get('order_type') == '03':
            o_copy['price'] = 0.01
            o_copy['is_market'] = True
        else:
            o_copy['price'] = float(price_val)
            o_copy['is_market'] = False

        o_copy['working_qty'] = int(o_copy['qty'])
        o_copy['action'] = "매수" if o_copy['action'] in ["BUY", "매수"] else "매도"

        if o_copy['action'] == '매수':
            buys.append(o_copy)
        else:
            sells.append(o_copy)

    # 매수는 비싼 가격부터, 매도는 싼 가격부터 매칭
    buys.sort(key=lambda x: x['price'], reverse=True)
    sells.sort(key=lambda x: x['price'])

    virtual_netted = []
    v_idx = 1

    # 가상 주문표 내 동일 조건 주문 통합 헬퍼 함수
    def add_virtual_order(action, price, qty, orig_id, map_type, is_market):
        nonlocal v_idx
        for v in virtual_netted:
            if (v['action'] == action and 
                abs(v['price'] - price) < 0.0001 and 
                v['orig_id'] == orig_id and 
                v['map_type'] == map_type and 
                v['is_market'] == is_market):
                v['qty'] += qty  # 단가와 조건이 같으면 수량만 누적
                return
        
        virtual_netted.append({
            'id': f"v{v_idx}",
            'action': action,
            'price': price,
            'qty': qty,
            'orig_id': orig_id,
            'map_type': map_type,
            'is_market': is_market
        })
        v_idx += 1

    # 2. 교차 매칭 (퉁치기 알고리즘)
    b_idx, s_idx = 0, 0
    while b_idx < len(buys) and s_idx < len(sells):
        b = buys[b_idx]
        s = sells[s_idx]

        # 가격 조건 확인: 매수 가격이 매도 가격보다 낮으면 퉁치기 필요 없음 (종료)
        if b['price'] < s['price']:
            break 

        if b['working_qty'] <= 0:
            b_idx += 1
            continue
        if s['working_qty'] <= 0:
            s_idx += 1
            continue

        match_qty = min(b['working_qty'], s['working_qty'])

        # 원래 매수가 못 샀을 때를 대비한 헷지 매도 주문 (inverse)
        ns_price = round(b['price'] + 0.01, 2)
        add_virtual_order('매도', ns_price, match_qty, b['id'], 'inverse', False)

        # 원래 매도가 못 팔았을 때를 대비한 헷지 매수 주문 (inverse, 시장가는 생성 X)
        nb_price = round(s['price'] - 0.01, 2)
        if nb_price > 0 and not s['is_market']:
            add_virtual_order('매수', nb_price, match_qty, s['id'], 'inverse', False)

        b['working_qty'] -= match_qty
        s['working_qty'] -= match_qty

    # 3. 퉁치고 남은 주문 처리 (direct)
    for b in buys:
        if b['working_qty'] > 0:
            add_virtual_order('매수', b['price'], b['working_qty'], b['id'], 'direct', False)

    for s in sells:
        if s['working_qty'] > 0:
            add_virtual_order('매도', s['price'], s['working_qty'], s['id'], 'direct', s['is_market'])

    # 4. HTS용 동일 가격 주문 통합
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
                'order_type': "30" # LOC 기본
            })

    if market_qty > 0:
        hts_orders.append({
            'action': 'SELL', 
            'price': 0.0, 
            'qty': market_qty, 
            'ticker': ticker,
            'order_type': "34" # MOC
        })

    # 주문 정렬 (매도 비싼것부터, 매수 싼것부터)
    hts_buys = [o for o in hts_orders if o['action'] == 'BUY']
    hts_sells = [o for o in hts_orders if o['action'] == 'SELL']
    
    hts_sells.sort(key=lambda x: float('-inf') if x['order_type'] == '34' else x['price'], reverse=True)
    hts_buys.sort(key=lambda x: x['price'])
    hts_orders = hts_sells + hts_buys

    # JSON 저장
    record = {'original_orders': original_orders, 'virtual_netted': virtual_netted}
    os.makedirs("config", exist_ok=True)
    json_path = f"config/{date_str}_{ticker}_{task_id}_netted.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    log_info(f"[{ticker}] 수동 퉁치기 연산 완료: 원본 {len(original_orders)}건 ➔ HTS {len(hts_orders)}건 압축됨.")
    return hts_orders


def reconstruct_from_csv_and_json(ticker: str, task_id: str, csv_executions: list, date_str: str, close_price: float = 0.0) -> list:
    """
    실제 체결된 결과(csv_executions)와 어제 저장한 퉁치기 대조표를 비교 분석하여,
    원래 취소/상쇄되었던 원본 티어별 주문들의 실질 체결(Effective execution) 결과를 역산 복원합니다.
    """
    json_path = f"config/{date_str}_{ticker}_{task_id}_netted.json"
    if not os.path.exists(json_path):
        log_info(f"[{ticker}] 퉁치기 백업본을 찾을 수 없어 원본 체결 내역을 그대로 차용합니다.")
        return [e for e in csv_executions if e.get('ticker') == ticker]

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            record = json.load(f)
    except Exception as e:
        log_error(f"[{ticker}] 퉁치기 파일 로드 중 오류: {e}")
        return [e for e in csv_executions if e.get('ticker') == ticker]

    original_orders = record.get('original_orders', [])
    virtual_netted  = record.get('virtual_netted', [])

    # HTS 총 체결량 집계
    ticker_execs = [e for e in csv_executions if e.get('ticker') == ticker]
    
    # csv_executions 내부 액션 표준화
    for e in ticker_execs:
        e['action'] = "매도" if e.get('action') in ["SELL", "매도"] else "매수"
        e['qty'] = int(e.get('qty', 0))
        e['price'] = float(e.get('price', 0.0))

    total_sell = sum(e['qty'] for e in ticker_execs if e['action'] == '매도')
    total_buy  = sum(e['qty'] for e in ticker_execs if e['action'] == '매수')

    sell_execs = [e for e in ticker_execs if e['action'] == '매도']
    buy_execs  = [e for e in ticker_execs if e['action'] == '매수']
    csv_sell_price = (sum(e['qty'] * e['price'] for e in sell_execs) / total_sell) if total_sell > 0 else 0.0
    csv_buy_price  = (sum(e['qty'] * e['price'] for e in buy_execs)  / total_buy)  if total_buy  > 0 else 0.0

    # 가상 주문 체결 배분
    v_sells = sorted([v for v in virtual_netted if v['action'] == '매도'], key=lambda x: x['price'])
    v_buys  = sorted([v for v in virtual_netted if v['action'] == '매수'], key=lambda x: x['price'], reverse=True)

    remaining_sell = total_sell
    for v in v_sells:
        fill = min(remaining_sell, v['qty'])
        v['exec_qty']   = fill
        v['unexec_qty'] = v['qty'] - fill
        remaining_sell -= fill

    remaining_buy = total_buy
    for v in v_buys:
        fill = min(remaining_buy, v['qty'])
        v['exec_qty']   = fill
        v['unexec_qty'] = v['qty'] - fill
        remaining_buy -= fill

    # [1단계] 각 주문별 실질 체결량(effective) 및 롤오버(Rollover) 판단
    total_rollover_qty = 0
    sell_results = {}
    buy_results = {}

    for o in original_orders:
        o_id = o['id']
        mapped_vs = [v for v in virtual_netted if v['orig_id'] == o_id]
        o_action = "매도" if o.get('action') in ["SELL", "매도"] else "매수"
        
        if o_action == '매도':
            # 매도의 실질 체결량 = (헷지 매수가 안 사짐 = 내부 퉁치기 성공) + (직구 매도가 팔림 = 외부 성공)
            internal_sold = sum(v.get('unexec_qty', 0) for v in mapped_vs if v['map_type'] == 'inverse')
            external_sold = sum(v.get('exec_qty', 0) for v in mapped_vs if v['map_type'] == 'direct')
            
            effective_sold = internal_sold + external_sold
            is_market = o.get('price') == '시장가' or o.get('price') == 0.01 or o.get('order_type') in ['34', '03']
            
            if effective_sold > 0 or is_market:
                orig_exec = int(o['qty'])
                leftover = int(o['qty']) - (effective_sold if not is_market else int(o['qty']))
                total_rollover_qty += max(0, leftover)
            else:
                orig_exec = 0
                
            sell_results[o_id] = {'orig_exec': orig_exec}
            
        elif o_action == '매수':
            # 매수의 실질 체결량 = (헷지 매도가 안 팔림 = 내부 퉁치기 성공) + (직구 매수가 사짐 = 외부 성공)
            internal_bought = sum(v.get('unexec_qty', 0) for v in mapped_vs if v['map_type'] == 'inverse')
            external_bought = sum(v.get('exec_qty', 0) for v in mapped_vs if v['map_type'] == 'direct')
            
            effective_bought = internal_bought + external_bought
            
            buy_results[o_id] = {
                'internal_bought': internal_bought,
                'external_bought': external_bought,
                'effective_bought': effective_bought
            }

    # [2단계] 역산 결과 생성 (롤오버 합산 및 평단가 계산)
    orig_executions = []
    residual_assigned = False

    def get_realized_price(action, target_price, b_price, s_price, c_price):
        if action == '매수':
            if b_price > 0: return b_price
            if s_price > 0: return s_price
            if c_price > 0: return c_price
            return target_price
        elif action == '매도':
            if s_price > 0: return s_price
            if b_price > 0: return b_price
            if c_price > 0: return c_price
            return target_price

    for o in original_orders:
        o_id = o['id']
        raw_price = o.get('price', 0)
        o_action = "매도" if o.get('action') in ["SELL", "매도"] else "매수"
        
        if str(raw_price) == '시장가':
            orig_target_price = 0.0
        else:
            orig_target_price = float(raw_price)

        if o_action == '매도':
            orig_exec = sell_results[o_id]['orig_exec']
            if orig_exec > 0:
                use_price = get_realized_price('매도', orig_target_price, csv_buy_price, csv_sell_price, close_price)
                orig_executions.append({
                    'ticker': ticker,
                    'action': 'SELL',
                    'qty': orig_exec,
                    'price': round(use_price, 4),
                    'tier': o.get('tier'),
                    'batch_id': o.get('batch_id')
                })

        elif o_action == '매수':
            res = buy_results[o_id]
            assigned_residual = 0
            if not residual_assigned and total_rollover_qty > 0:
                assigned_residual = total_rollover_qty
                residual_assigned = True
                
            total_qty = res['effective_bought'] + assigned_residual
            
            if total_qty > 0:
                p_buy = get_realized_price('매수', orig_target_price, csv_buy_price, csv_sell_price, close_price)
                orig_executions.append({
                    'ticker': ticker,
                    'action': 'BUY',
                    'qty': total_qty,
                    'price': round(p_buy, 4),
                    'tier': o.get('tier'),
                    'mode': o.get('mode', '안전모드')
                })

    # 예외 상황 방어 및 HTS 오차 보정
    if not residual_assigned and total_rollover_qty > 0:
        p_buy = get_realized_price('매수', 0, csv_buy_price, csv_sell_price, close_price)
        if p_buy > 0:
            orig_executions.append({
                'ticker': ticker,
                'action': 'BUY',
                'qty': total_rollover_qty,
                'price': round(p_buy, 4),
                'partial': True
            })

    if remaining_buy > 0:
        p_buy = get_realized_price('매수', 0, csv_buy_price, csv_sell_price, close_price)
        if p_buy > 0:
            orig_executions.append({
                'ticker': ticker,
                'action': 'BUY',
                'qty': remaining_buy,
                'price': round(p_buy, 4),
                'partial': True
            })

    log_info(f"[{ticker}] 퉁치기 체결 역산 복원 완료: HTS 실제 체결 매수 {total_buy} / 매도 {total_sell} ➔ 원본 복원 {len(orig_executions)}건")
    return orig_executions

def simulate_hts_executions(hts_orders: list, close_price: float) -> list:
    """
    HTS 전송 주문 목록(hts_orders)과 당일 종가(close_price)를 비교하여,
    HTS 상에서 실제로 체결되었을 체결 내역 목록(csv_executions)을 자가 생성합니다.
    """
    csv_executions = []
    for o in hts_orders:
        action = o.get("action") # BUY / SELL
        order_type = o.get("order_type") # 30: LOC, 34: MOC, 00: 지정가, 03: 시장가
        qty = int(o.get("qty", 0))
        price = float(o.get("price", 0.0))
        ticker = o.get("ticker", "SOXL")

        executed = False
        if order_type == "34" or order_type == "03": # MOC / 시장가
            executed = True
        elif action == "BUY": # 매수 (LOC / 지정가)
            # 종가가 주문가 이하일 때 체결
            if close_price <= price:
                executed = True
        elif action == "SELL": # 매도 (LOC / 지정가)
            # 종가가 주문가 이상일 때 체결
            if close_price >= price:
                executed = True

        if executed:
            csv_executions.append({
                "ticker": ticker,
                "action": "SELL" if action == "SELL" else "BUY",
                "qty": qty,
                "price": close_price # 실제 체결가는 당일 종가 기준 적용
            })

    return csv_executions
