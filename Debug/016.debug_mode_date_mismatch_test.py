# -*- coding: utf-8 -*-
# 테스트 목적: 2026년 6월 1일부터 6월 15일까지의 백테스트 매매 모드 출력을 실행하여 
# 구글 시트의 실제 매매 모드와 일치하는지(6/5 공세, 6/8 안전) 정밀 검증합니다.

import os
import sys

# 프로젝트 루트 경로 설정
project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, project_root)

from core.backtester import Backtester

def main():
    print("=" * 80)
    print("6/1 ~ 6/15 백테스트 매매 모드 매칭 검증")
    print("=" * 80)
    
    try:
        # 백테스트 수행 (6월 초반부 검증)
        result = Backtester.run_backtest(
            ticker="SOXL",
            start_date_str="2026-01-01", # 충분한 모드 기록 추적용
            end_date_str="2026-06-20",
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
        
        tx_table = result["detailedTxTable"]
        
        # 구글 시트 실제 모드와 비교 매핑 테이블
        # Row  10 (JJ): 날짜=06.01.(월) | 매매모드=공세
        # Row  11 (JJ): 날짜=06.02.(화) | 매매모드=공세
        # Row  12 (JJ): 날짜=06.03.(수) | 매매모드=공세
        # Row  13 (JJ): 날짜=06.04.(목) | 매매모드=공세
        # Row  14 (JJ): 날짜=06.05.(금) | 매매모드=공세
        # Row  15 (JJ): 날짜=06.08.(월) | 매매모드=안전
        # Row  16 (JJ): 날짜=06.09.(화) | 매매모드=안전
        # Row  17 (JJ): 날짜=06.10.(수) | 매매모드=안전
        sheet_modes = {
            "2026-06-01": "공세",
            "2026-06-02": "공세",
            "2026-06-03": "공세",
            "2026-06-04": "공세",
            "2026-06-05": "공세",
            "2026-06-08": "안전",
            "2026-06-09": "안전",
            "2026-06-10": "안전",
            "2026-06-11": "안전",
            "2026-06-12": "안전",
            "2026-06-15": "안전"
        }
        
        print(f"\n{'날짜':<12} | {'시트 모드':<6} | {'로컬 백테스트 모드':<12} | {'결과'}")
        print("-" * 65)
        
        match_count = 0
        total_count = 0
        
        for row in tx_table:
            date_str = row["date"]
            if date_str in sheet_modes:
                total_count += 1
                sheet_m = sheet_modes[date_str]
                local_m = row["mode"].replace("모드", "") # "공세모드" -> "공세"
                is_match = sheet_m == local_m
                if is_match:
                    match_count += 1
                status = "PASS" if is_match else "FAIL (불일치)"
                print(f"{date_str:<12} | {sheet_m:<8s} | {local_m:<16s} | {status}")
                
        print("\n" + "=" * 80)
        print(f"최종 결과: {total_count}건 중 {match_count}건 일치 (일치율: {match_count/total_count*100:.1f}%)")
        if match_count == total_count:
            print("[성공] 6/5 공세모드 및 6/8 안전모드 전환 시점이 구글 시트와 100% 완벽히 일치합니다!")
        else:
            print("[실패] 모드 불일치가 여전히 존재합니다. 추가 원인 파악이 필요합니다.")
            
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    main()
