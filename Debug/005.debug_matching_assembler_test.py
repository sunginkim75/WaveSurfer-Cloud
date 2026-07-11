# -*- coding: utf-8 -*-
"""
테스트 목적: core.backtest_assembler.BacktestAssembler 모듈의 실제 Task 데이터 병합 및 17열 엑셀 매매 대조표 조립 알고리즘 동작 유효성 검증
"""
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.backtest_assembler import BacktestAssembler
from utils.db_handler import DBHandler

def main():
    print("Task 매칭 테이블 조립 테스트 시작...")
    db = DBHandler()
    config_path = "config/config.json"
    
    try:
        config = db.load_json(config_path)
        tasks = config.get("tasks", [])
        
        if not tasks:
            print("설정 파일에 등록된 Task가 없습니다.")
            return
            
        # 첫 번째 Task (SI_MOCK) 선택
        task = tasks[0]
        print(f"선택된 Task: {task.get('nickname')} (ID: {task.get('id')})")
        
        # 조립 실행
        rows = BacktestAssembler.assemble_matching_table(task)
        
        print("조립 완료!")
        print(f"조립된 총 행수: {len(rows)}")
        
        # 첫 5개 행 샘플 출력
        print("\n처음 5개 행 데이터:")
        for r in rows[:5]:
            print(f"날짜: {r['date']} | 종가: {r['close']} | 모드: {r['mode']} | 매수: {r['buyPrice']} | 매도: {r['sellPrice']} | 예수금: {r['cash']:.2f}")
            
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    main()
