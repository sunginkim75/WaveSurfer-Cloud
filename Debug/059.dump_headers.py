# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트의 헤더(행 8)와 실제 데이터 행들의 30~50번 컬럼 데이터를 정밀 분석하여
시드 증액과 입출금 컬럼의 위치와 데이터 형식을 파악합니다.
"""
import urllib.request, csv, io, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

url = 'https://docs.google.com/spreadsheets/d/1jOasXDShdBXHP37v0MruSz8y8HnhGi3PNxVa0vPGmzQ/export?format=csv&gid=879227790'
with urllib.request.urlopen(url) as r:
    raw = r.read()
data = raw.decode('utf-8-sig')
reader = csv.reader(io.StringIO(data))
rows = list(reader)

# 헤더 출력 (행 8)
header = rows[8]
print("=== 헤더 매핑 ===")
for idx, name in enumerate(header):
    name_clean = name.strip().replace('\n', ' ')
    if name_clean:
        print(f"  [{idx}] {name_clean}")

# 시드 증액이 발생하는 행 찾기 (데이터는 행 9부터 시작)
print("\n=== 시드증액/입출금 관련 값이 존재하는 행 샘플 ===")
for i in range(9, len(rows)):
    cols = rows[i]
    if len(cols) < 45:
        continue
    # [36]=자금갱신?, [37]=시드증액?, [38]=입출금?, [39]=예수금?, [40]=보유량? 등
    # 인덱스 33~37번 출력
    val_33 = cols[33].strip() if len(cols) > 33 else '' # 갱신
    val_34 = cols[34].strip() if len(cols) > 34 else '' # 복리금액
    val_35 = cols[35].strip() if len(cols) > 35 else '' # 자금갱신
    val_36 = cols[36].strip() if len(cols) > 36 else '' # 시드증액
    val_37 = cols[37].strip() if len(cols) > 37 else '' # 입출금

    if val_36 or val_37:
        date_raw = cols[9].strip()
        print(f"행 {i:3d} [{date_raw}]: 갱신(33)={val_33} | 복리금(34)={val_34} | 자금갱신(35)={val_35} | 시드증액(36)={val_36} | 입출금(37)={val_37}")
