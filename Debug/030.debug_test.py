# -*- coding: utf-8 -*-
"""
테스트 목적: 
실전 수동 모드(REAL_MANUAL)의 신규 API인 /matching/edit POST 요청을 테스트합니다.
가상의 수동 체결 데이터를 쏘았을 때 trade_batches 및 trade_history JSON 파일에 정상 업데이트되는지,
이후 /matching API를 통해 38개 컬럼 데이터가 깨짐 없이 조립되는지 최종 검증합니다.
"""
import sys
import os
import json
import uuid

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.backtest_assembler import BacktestAssembler
from utils.db_handler import DBHandler

def run_test():
    print("=== 실전 수동 모드 체결 수정 API 테스트 시작 ===")
    
    # 1. 태스크 설정 모킹
    task_config = {
        "id": "task_009a82ba",  # SITW 태스크 ID
        "ticker": "SOXL",
        "seed_amt": 10000.0,
        "operation_mode": "REAL_MANUAL"
    }
    
    # 임시 거래 데이터
    edit_data_buy = {
        "date": "2026-07-10",
        "buyPrice": "192.26",
        "buyQty": "5",
        "sellPrice": "",
        "sellQty": "",
        "sellDate": "",
        "mode": "안전모드"
    }
    
    print("\n[1] 매수 보유 거래 기입 테스트 진행...")
    success_buy = BacktestAssembler.edit_transaction(task_config, edit_data_buy)
    print(f"매수 기입 API 호출 결과: {success_buy}")
    
    # 2. 파일 저장 상태 검증
    db = DBHandler()
    batches_file = f"config/trade_batches_{task_config['id']}.json"
    batches_data = db.load_json(batches_file)
    print(f"Batches JSON 파일 로드 확인 (수량: {len(batches_data)}):")
    print(json.dumps(batches_data, indent=4, ensure_ascii=False))
    
    # 3. 매도 체결 데이터 기입 테스트
    edit_data_sell = {
        "date": "2026-07-10",
        "buyPrice": "192.26",
        "buyQty": "5",
        "sellPrice": "205.50",
        "sellQty": "5",
        "sellDate": "2026-07-12",
        "mode": "안전모드"
    }
    
    print("\n[2] 매도 완료 거래 기입 테스트 진행...")
    success_sell = BacktestAssembler.edit_transaction(task_config, edit_data_sell)
    print(f"매도 기입 API 호출 결과: {success_sell}")
    
    # 4. 파일 저장 상태 검증 (history 및 batches)
    history_file = f"config/trade_history_{task_config['id']}.json"
    history_data = db.load_json(history_file)
    batches_data_after = db.load_json(batches_file)
    
    print(f"Batches JSON 파일 (매도 후 잔여 수량: {len(batches_data_after)}):")
    print(json.dumps(batches_data_after, indent=4, ensure_ascii=False))
    print(f"History JSON 파일 (매도 완료 내역 수량: {len(history_data)}):")
    print(json.dumps(history_data, indent=4, ensure_ascii=False))
    
    # 5. 매칭 테이블 조립 검증
    print("\n[3] 38개 컬럼 대조표 매칭 테이블 조립 검증...")
    report = BacktestAssembler.assemble_matching_report(task_config)
    tx_table = report.get("detailedTxTable", [])
    print(f"조립된 거래 행 수: {len(tx_table)}")
    if len(tx_table) > 0:
        # 최근 2개의 거래 행 출력
        for row in tx_table[-2:]:
            print(f"날짜: {row.get('date')} | 종가: {row.get('close')} | 매매모드: {row.get('mode')} | "
                  f"매수가: {row.get('buyPrice')} | 매수량: {row.get('buyQty')} | "
                  f"매도일: {row.get('sellDate')} | 매도가: {row.get('sellPrice')} | 매도량: {row.get('sellQty')} | "
                  f"실현손익: {row.get('todayRealized')} | 총자산: {row.get('totalAsset')}")

    # 테스트 후 원래 상태로 롤백 (테스트 데이터 삭제)
    print("\n[4] 테스트 데이터 롤백(삭제) 진행...")
    rollback_data = {
        "date": "2026-07-10",
        "buyPrice": "",
        "buyQty": ""
    }
    BacktestAssembler.edit_transaction(task_config, rollback_data)
    print("롤백 완료.")

if __name__ == "__main__":
    run_test()
