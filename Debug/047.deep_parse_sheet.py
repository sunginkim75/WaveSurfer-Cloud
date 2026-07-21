# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트의 실제 데이터 구조를 파악 - 거래 이력 컬럼 위치 탐색
"""
import urllib.request, csv, io

url = 'https://docs.google.com/spreadsheets/d/1jOasXDShdBXHP37v0MruSz8y8HnhGi3PNxVa0vPGmzQ/export?format=csv&gid=879227790'
with urllib.request.urlopen(url) as r:
    raw = r.read()

data = raw.decode('utf-8-sig')
lines = data.strip().split('\n')
print(f'총 {len(lines)}행')

# 처음 10행 모두 출력 (컬럼 구조 파악)
print('\n=== 처음 10행 ===')
for i, line in enumerate(lines[:10]):
    cols = line.split(',')
    print(f'행{i}({len(cols)}컬럼): ', end='')
    for j, c in enumerate(cols[:30]):
        c2 = c.strip().strip('"')
        if c2:
            print(f'[{j}]{c2}', end=' ')
    print()

# 숫자값이 있는 행 탐색 (숫자로 시작하거나 숫자가 많이 포함된 행)
print('\n=== 행 5~25 상세 ===')
for i, line in enumerate(lines[5:25], start=5):
    cols = line.split(',')
    non_empty = [(j, c.strip().strip('"')) for j, c in enumerate(cols) if c.strip().strip('"')]
    if non_empty:
        print(f'행{i}: {non_empty[:20]}')

# 특정 값이 있는 행을 탐색 - 거래 데이터
print('\n=== 숫자가 많은 행 탐색 (행100-200) ===')
for i, line in enumerate(lines[100:200], start=100):
    cols = line.split(',')
    nums = [c.strip().strip('"') for c in cols if c.strip().strip('"').replace('.','').replace('-','').isdigit()]
    if len(nums) >= 5:
        print(f'행{i}({len(nums)}개숫자): {line[:300]}')
