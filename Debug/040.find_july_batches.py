# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트 CSV 백업에서 2026년 7월 부근의 SOXL 거래 이력을 역추적하고,
보유량(MOC/LOC 매수 누적 후 매도되지 않고 남은 분량)을 확인하여 91주의 상세 배치 상태를 규명합니다.
"""
import os
import csv

csv_path = r"C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\DOCS\SI_VR_WAVE_SURFER_V2.5(251027)_8265_자동화 - JJ.csv"

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

print(f"총 행 수: {len(rows)}")

# 1. 2026년 7월 날짜가 포함된 행 검색
# CSV에서 날짜는 Index 9 (J열)에 주로 있습니다.
print("\n[1] 2026년 7월(07.) 날짜가 들어있는 행과 해당 컬럼들 조회:")
for idx, r in enumerate(rows):
    if idx < 5:
        continue
    if len(r) > 10:
        date_str = r[9].strip()
        # 07.xx 형태나 7.xx 형태 매칭 (7월)
        # 예: 07.01, 07.02, 7.10 등
        if date_str.startswith("07.") or date_str.startswith("7.") or "07.10" in date_str or "07.09" in date_str:
            # 주요 지표 출력: 날짜, 종가(10), 매매모드(11), 매수가(16), 매수량(17), 보유량(33) 등
            # 인덱스를 안전하게 가드하여 출력
            safe_print_cols = [f"{i}:{val.strip()}" for i, val in enumerate(r[:40]) if val.strip()]
            print(f"Row {idx:04d} | {safe_print_cols[:12]}")
            
# 2. 특히 파일 상단 혹은 어딘가에 있는 "현재 보유량"과 "평단" 확인
print("\n[2] 상단 요약부 보유량/평단가 행 확인:")
for idx in range(25):
    r = rows[idx]
    safe_print = [f"{i}:{val.strip()}" for i, val in enumerate(r[:30]) if val.strip()]
    print(f"Row {idx:02d} | {safe_print}")
