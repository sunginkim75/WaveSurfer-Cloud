# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트의 매수/매도 행 구조를 정확히 파악합니다.
인접한 여러 행의 전체 컬럼을 출력하여 구조를 이해합니다.
"""
import urllib.request, csv, io

url = 'https://docs.google.com/spreadsheets/d/1jOasXDShdBXHP37v0MruSz8y8HnhGi3PNxVa0vPGmzQ/export?format=csv&gid=879227790'
with urllib.request.urlopen(url) as r:
    raw = r.read()
data = raw.decode('utf-8-sig')

reader = csv.reader(io.StringIO(data))
rows = list(reader)
print(f'총 {len(rows)}행')

# 초반 행들 (행 6~25) 전체 출력
for row_i in range(6, 25):
    if row_i >= len(rows):
        break
    cols = rows[row_i]
    non_empty = [(j, cols[j].strip()) for j in range(len(cols)) if cols[j].strip()]
    print(f'행{row_i}({len(cols)}컬): {non_empty[:18]}')

print('\n=== 7월 구간 (행 175~190) ===')
for row_i in range(175, 190):
    if row_i >= len(rows):
        break
    cols = rows[row_i]
    non_empty = [(j, cols[j].strip()) for j in range(len(cols)) if cols[j].strip()]
    print(f'행{row_i}({len(cols)}컬): {non_empty[:18]}')
