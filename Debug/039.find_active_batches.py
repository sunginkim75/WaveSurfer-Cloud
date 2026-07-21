# -*- coding: utf-8 -*-
"""
테스트 목적:
CSV 백업 파일에서 63077091 계좌 또는 SOXL 매수 내역 중
수량 합이 91주가 되는 활성 배치(Active Batches) 정보를 역산하고 파악합니다.
"""
import os
import csv

csv_path = r"C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\DOCS\SI_VR_WAVE_SURFER_V2.5(251027)_8265_자동화 - JJ.csv"

if not os.path.exists(csv_path):
    print("[ERROR] CSV 파일 없음")
    exit()

print("CSV 파일 읽기 및 활성 배치 분석...")
# CSV의 모든 행을 메모리에 적재
rows = []
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for r in reader:
        rows.append(r)

print(f"총 행 수: {len(rows)}")

# '63077091' 키워드가 들어있는 행 번호 찾기
found_lines = []
for idx, r in enumerate(rows):
    row_str = " ".join(r)
    if "63077091" in row_str or "SITW" in row_str or "6307709110" in row_str:
        found_lines.append((idx, r[:10]))

print(f"\n[1] 관련 키워드 발견 위치:")
for idx, content in found_lines:
    print(f"  - 행 {idx}: {content}")

# CSV 내에서 SOXL의 배치 이력(날짜별 매수) 정보 수집
# J열 ~ AC열에 해당하는 데이터를 파싱하여 화면에 정보 노출
# 보통 LOC 매수일(보통 15번째 열 전후)과 매수단가, 수량이 기입된 행 탐색
print("\n[2] SOXL 매수 정보가 포함된 구역 탐색...")
# 행들을 돌면서 날짜 패턴(예: 26.07.xx 또는 07.01 등)이 있고 수량이 찍힌 부분 탐색
for idx in range(len(rows)):
    row = rows[idx]
    if len(row) > 15:
        # 9열(Index 9) 근처에 날짜가 있고, 13열(Index 13) 근처에 수량이나 가격이 있는지 검색
        date_val = row[9].strip()
        if date_val and ("." in date_val or "-" in date_val) and any(char.isdigit() for char in date_val):
            # 이 행이 매수 행인지 체크
            # 수량과 단가가 숫자인지 파악
            try:
                qty_val = row[13].replace(",", "").strip()
                price_val = row[10].replace(",", "").strip()
                # 간단한 출력 (샘플링)
                if idx < 40:
                    print(f"행 {idx:03d} | 날짜: {date_val} | 가격/지표: {price_val} | 값: {qty_val} | 전체: {row[9:17]}")
            except Exception:
                pass
