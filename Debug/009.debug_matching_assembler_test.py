# -*- coding: utf-8 -*-
# 테스트 목적: 거래 데이터가 없어 빈 매칭 테이블이 조립될 때,
# BacktestAssembler.assemble_matching_report가 totalAsset이 누락되지 않고
# 올바른 요약 정보(summary)를 반환하는지 유닛 테스트 수행.

import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.backtest_assembler import BacktestAssembler

def test_matching_report_with_empty_data():
    print("=== [009.debug_matching_assembler_test] 시작 ===")
    
    # 1. assemble_matching_table 모킹 (빈 리스트 반환하도록 강제 설정)
    original_func = BacktestAssembler.assemble_matching_table
    BacktestAssembler.assemble_matching_table = classmethod(lambda cls, task_config: [])
    
    # 가상의 빈 태스크 설정 준비
    dummy_task_config = {
        "id": "task_test_empty",
        "account_no": "999999",
        "nickname": "임시 테스트 봇",
        "ticker": "SOXL",
        "seed_amt": 10000.0
    }
    
    try:
        # 2. assemble_matching_report 실행
        print("빈 거래 내역에 대해 assemble_matching_report 호출 중 (모킹 적용)...")
        result = BacktestAssembler.assemble_matching_report(dummy_task_config)
        
        # 3. 반환값 검증
        summary = result.get("summary", {})
        print("반환된 summary 객체:", summary)
        
        # 필수 필드 확인
        required_fields = ["totalReturn", "mdd", "cagr", "realizedProfitVal", "totalAsset"]
        missing_fields = [field for field in required_fields if field not in summary]
        
        if missing_fields:
            print(f"[FAIL] 실패: 누락된 필드가 존재합니다 -> {missing_fields}")
            sys.exit(1)
            
        # totalAsset 값 검증
        assert summary["totalAsset"] == 0.0, f"Expected totalAsset to be 0.0, but got {summary['totalAsset']}"
        
        print("[SUCCESS] 성공: 빈 거래 데이터 시 totalAsset 필드가 누락 없이 0.0으로 반환됨.")
        print("=== 테스트 통과 ===")
        
    finally:
        # 모킹 복원
        BacktestAssembler.assemble_matching_table = original_func

if __name__ == "__main__":
    test_matching_report_with_empty_data()
