# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트 CSV에서 2026-07-01부터 최근 2026-07-12까지의
SOXL Wave Surfer 실제 매매 체결 이력(J열 ~ AC열에 걸친 주요 컬럼값들)을
빠짐없이 수집하여 진짜 활성 상태인 배치 상세 목록을 추출합니다.
"""
import os
import csv

csv_path = r"C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\DOCS\SI_VR_WAVE_SURFER_V2.5(251027)_8265_자동화 - JJ.csv"

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

print("=== 7월 Wave Surfer 실제 행 데이터 디테일 분석 ===")
# 헤더 컬럼명 출력 (Row 08)
header = rows[8]
print(f"Header: {[f'{i}:{name.strip()}' for i, name in enumerate(header) if name.strip()]}")

# 7월 데이터 행들 (Row 175 ~ 190)
for idx in range(175, 195):
    if idx < len(rows):
        r = rows[idx]
        date = r[9].strip() if len(r) > 9 else ""
        
        # 유의미한 데이터가 있는 행만
        if date:
            # 주요 컬럼값들 매핑 추출
            # J(9): 거래일자, K(10): 종가, L(11): 매매모드, O(14): LOC 매수목표, Q(16): 매수가, R(17): 매수량, S(18): 매수금액, W(22): MOC매도목표, AB(27): 매도금액
            # AH(33): 예수금, AI(34): 보유량, AJ(35): 평가금, AK(36): 총자산, AL(37): 평단
            print(f"\n[행 {idx:03d} - {date}]")
            print(f"  - 종가: {r[10].strip()} | 매매모드: {r[11].strip()}")
            print(f"  - [매수] 목표량: {r[15].strip()} | 매수가: {r[16].strip()} | 매수량: {r[17].strip()} | 매수금액: {r[18].strip()}")
            print(f"  - [매도] 매도일: {r[22].strip()} | 매도가: {r[25].strip()} | 매도량: {r[26].strip()} | 매도금액: {r[27].strip()}")
            print(f"  - [계좌] 예수금: {r[33].strip()} | 보유량: {r[34].strip()} | 평가금: {r[35].strip()} | 총자산: {r[36].strip()} | 평단: {r[37].strip()}")
