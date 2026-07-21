# -*- coding: utf-8 -*-
"""
테스트 목적:
컬럼 인덱스를 정확히 파악하기 위해 특정 행의 전체 컬럼 값 출력
"""
import urllib.request

url = 'https://docs.google.com/spreadsheets/d/1jOasXDShdBXHP37v0MruSz8y8HnhGi3PNxVa0vPGmzQ/export?format=csv&gid=879227790'
with urllib.request.urlopen(url) as r:
    raw = r.read()
data = raw.decode('utf-8-sig')
lines = data.strip().split('\n')

# 행 10(첫 번째 매수행), 15(매도완료행) 상세 출력
for row_i in [10, 15, 178, 179]:
    if row_i >= len(lines):
        continue
    line = lines[row_i]
    cols = line.split(',')
    print(f'=== 행{row_i} ({len(cols)}컬럼) ===')
    for j, c in enumerate(cols):
        c2 = c.strip().strip('"').strip()
        if c2:
            print(f'  [{j}] {c2}')
    print()
