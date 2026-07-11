# -*- coding: utf-8 -*-
"""
테스트 목적: core.backtest_assembler.BacktestAssembler.assemble_matching_report의 실제 Task 매칭 결과 가공 및 통계(MDD, CAGR) 계산 연산 유효성 검증
"""
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.backtest_assembler import BacktestAssembler
from utils.db_handler import DBHandler

def main():
    print("Task 매칭 레포트 조립 테스트 시작...")
    db = DBHandler()
    config_path = "config/config.json"
    
    try:
        config = db.load_json(config_path)
        tasks = config.get("tasks", [])
        
        if not tasks:
            print("설정 파일에 등록된 Task가 없습니다.")
            return
            
        task = tasks[0]
        print(f"선택된 Task: {task.get('nickname')} (ID: {task.get('id')})")
        
        # 보고서 조립 실행
        report = BacktestAssembler.assemble_matching_report(task)
        
        print("보고서 조립 완료!")
        print(f"티커: {report.get('ticker')}")
        print(f"시작일: {report.get('startDate')} | 종료일: {report.get('endDate')}")
        
        summary = report.get("summary", {})
        print("\n[요약 정보]")
        print(f"누적 복리 수익률: {summary.get('totalReturn'):.2f}%")
        print(f"최대 낙폭 (MDD): {summary.get('mdd'):.2f}%")
        print(f"연환산 수익률 (CAGR): {summary.get('cagr'):.2f}%")
        print(f"실현 손익: ${summary.get('realizedProfitVal'):,.2f}")
        
        history = report.get("history", [])
        print(f"\n자산 추이 이력 수 (History): {len(history)}")
        if history:
            print("자산 추이 최초 3일:")
            for h in history[:3]:
                print(f"  날짜: {h['date']} | 총자산: ${h['totalAsset']:.2f} | 예수금: ${h['cash']:.2f} | 평가액: ${h['evalAmt']:.2f} | MDD: {h['mdd']:.2f}%")
            print("자산 추이 최종 3일:")
            for h in history[-3:]:
                print(f"  날짜: {h['date']} | 총자산: ${h['totalAsset']:.2f} | 예수금: ${h['cash']:.2f} | 평가액: ${h['evalAmt']:.2f} | MDD: {h['mdd']:.2f}%")
                
        rows = report.get("detailedTxTable", [])
        print(f"\n상세 거래 내역 행 수 (detailedTxTable): {len(rows)}")
        if rows:
            print("상세 내역 처음 3행 필드 검증:")
            for r in rows[:3]:
                print(f"  날짜: {r.get('date')} | 종가: {r.get('close')} | 모드: {r.get('mode')} | 당일실현(todayRealized): {r.get('todayRealized')} | 손익금액(profitAmt): {r.get('profitAmt')} | 누적손익: {r.get('accumProfit')}")
                
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    main()
