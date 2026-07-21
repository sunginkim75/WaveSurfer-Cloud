# -*- coding: utf-8 -*-
"""
테스트 목적:
CSV 파서로 정확하게 파싱하여 컬럼 구조를 재검증
행 10(첫 거래행), 15(완료된 거래), 179(7월 완료된 거래)의 정확한 컬럼 매핑 확인
"""
import urllib.request, csv, io

url = 'https://docs.google.com/spreadsheets/d/1jOasXDShdBXHP37v0MruSz8y8HnhGi3PNxVa0vPGmzQ/export?format=csv&gid=879227790'
with urllib.request.urlopen(url) as r:
    raw = r.read()
data = raw.decode('utf-8-sig')

reader = csv.reader(io.StringIO(data))
rows = list(reader)
print(f'총 {len(rows)}행')

# 행 10, 15, 179, 181 상세 출력 (CSV 파서 결과)
for row_i in [10, 15, 179, 181]:
    if row_i >= len(rows):
        continue
    cols = rows[row_i]
    print(f'\n=== 행{row_i} (CSV파싱, {len(cols)}컬럼) ===')
    for j, c in enumerate(cols):
        c2 = c.strip()
        if c2:
            print(f'  [{j}] {repr(c2)}')
