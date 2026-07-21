# -*- coding: utf-8 -*-
"""
테스트 목적:
2025-11-11 행의 컬럼 29, 30, 31, 32, 33 값을 정확히 확인하여
realized 값이 어느 컬럼에 있는지 파악합니다.
"""
import urllib.request, csv, io

url = 'https://docs.google.com/spreadsheets/d/1jOasXDShdBXHP37v0MruSz8y8HnhGi3PNxVa0vPGmzQ/export?format=csv&gid=879227790'
with urllib.request.urlopen(url) as r:
    raw = r.read()
data = raw.decode('utf-8-sig')
reader = csv.reader(io.StringIO(data))
rows = list(reader)

# 11월 11일 행 찾기 (행 18: 11.10., 행 19: 11.11.)
for row_i in range(5, 30):
    cols = rows[row_i]
    date_raw = cols[9].strip() if len(cols) > 9 else ''
    if '11.11' in date_raw or '11.10' in date_raw or '11.12' in date_raw:
        non_empty = [(j, cols[j].strip()) for j in range(len(cols)) if cols[j].strip()]
        print(f'행{row_i} [{date_raw}]: {non_empty[:30]}')
        print()
