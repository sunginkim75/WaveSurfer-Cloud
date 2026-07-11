# -*- coding: utf-8 -*-
"""
테스트 목적: core.backtester.Backtester 모듈의 yfinance 데이터 다운로드 및 백테스트 알고리즘 동작 유효성 검증
"""
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.backtester import Backtester

def main():
    print("백테스트 시뮬레이션 테스트 시작...")
    try:
        result = Backtester.run_backtest(
            ticker="SOXL",
            start_date_str="2025-01-01",
            end_date_str="2025-06-01",
            seed_amt=10000.0,
            safe_buy_pct=3.0,
            safe_sell_pct=0.2,
            agg_buy_pct=5.0,
            agg_sell_pct=2.5,
            split_count=7,
            update_period=10,
            compounding_profit_rate=80.0,
            compounding_loss_rate=30.0
        )
        print("백테스트 완료!")
        print(f"티커: {result['ticker']}")
        print(f"시작일: {result['startDate']}")
        print(f"종료일: {result['endDate']}")
        print(f"수익률: {result['summary']['totalReturn']:.2f}%")
        print(f"MDD: {result['summary']['mdd']:.2f}%")
        print(f"CAGR: {result['summary']['cagr']:.2f}%")
        print(f"실현손익: {result['summary']['realizedProfitVal']:.2f}")
        print(f"히스토리 개수: {len(result['history'])}")
        print(f"상세 테이블 거래일 개수: {len(result['detailedTxTable'])}")
        
        # 첫 3개 테이블 행 출력
        print("\n상세 테이블 샘플:")
        for row in result['detailedTxTable'][:3]:
            print(row)
            
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    main()
