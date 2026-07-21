# -*- coding: utf-8 -*-
# 테스트 목적: 실제 거래 내역이 들어 있는 task_3917820f에 대해 
# BacktestAssembler.assemble_matching_report를 호출하여 오류 없이 결과를 생성하는지 검증합니다.

import os
import sys

# 프로젝트 루트 경로 설정
project_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, project_root)

from core.backtest_assembler import BacktestAssembler
from utils.db_handler import DBHandler

def main():
    print("=" * 80)
    print("실제 거래 데이터 기반 매매 대조표 조립 검증 시작")
    print("=" * 80)
    
    db = DBHandler()
    config_path = "config/config.json"
    config_data = db.load_json(config_path)
    
    # task_3917820f 찾기
    task_config = None
    for t in config_data.get("tasks", []):
        if t.get("id") == "task_3917820f":
            task_config = t
            break
            
    if not task_config:
        print("[오류] task_3917820f 설정을 찾을 수 없습니다.")
        return
        
    try:
        print("BacktestAssembler.assemble_matching_report 호출 중...")
        report = BacktestAssembler.assemble_matching_report(task_config)
        print("[성공] 매매 대조표 리포트가 정상적으로 조립되었습니다!")
        
        summary = report.get("summary", {})
        detailed_table = report.get("detailedTxTable", [])
        
        print("\n--- 리포트 요약 ---")
        print(f"티커: {report.get('ticker')}")
        print(f"시작일: {report.get('startDate')}")
        print(f"종료일: {report.get('endDate')}")
        print(f"총 수익률: {summary.get('totalReturn'):.2f}%")
        print(f"최종 자산: {summary.get('totalAsset'):.2f}")
        print(f"실현 손익: {summary.get('realizedProfitVal'):.2f}")
        print(f"MDD: {summary.get('mdd'):.2f}%")
        print(f"상세 테이블 행 개수: {len(detailed_table)}")
        
        if detailed_table:
            print("\n상세 테이블의 마지막 3개 행:")
            for r in detailed_table[-3:]:
                # 가독성을 위해 일부 필드만 출력
                print(f"  - 날짜: {r.get('date')} | 모드: {r.get('mode')} | 종가: {r.get('close')} | 누적수익: {r.get('accumProfit')} | 예수금: {r.get('cash'):.2f} | 총자산: {r.get('totalAsset'):.2f}")
                
    except Exception as e:
        print(f"[실패] 조립 도중 오류 발생: {e}")

if __name__ == "__main__":
    main()
