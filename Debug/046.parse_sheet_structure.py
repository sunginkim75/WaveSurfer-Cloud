# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트의 컬럼 구조와 날짜 데이터 위치를 탐색하여
2025-10-28 이후 이력 데이터를 파악합니다.
"""
import urllib.request, csv, io

url = 'https://docs.google.com/spreadsheets/d/1jOasXDShdBXHP37v0MruSz8y8HnhGi3PNxVa0vPGmzQ/export?format=csv&gid=879227790'
with urllib.request.urlopen(url) as r:
    raw = r.read()

for enc in ['utf-8-sig', 'utf-8', 'cp949']:
    try:
        data = raw.decode(enc)
        lines = data.strip().split('\n')
        print(f'[인코딩: {enc}] 총 {len(lines)}행')
        # 날짜 포함 행 탐색
        found = []
        for i, line in enumerate(lines):
            cols = line.split(',')
            for j, c in enumerate(cols[:30]):
                c = c.strip().strip('"')
                if len(c) >= 8 and c[:4].isdigit() and '-' in c:
                    found.append((i, j, c, line[:250]))
                    break
        print(f'날짜 포함 행: {len(found)}개')
        for row_i, col_j, date_val, row_val in found[:20]:
            print(f'  행{row_i} 열{col_j}: {date_val} | {row_val}')
        print('...')
        for row_i, col_j, date_val, row_val in found[-10:]:
            print(f'  행{row_i} 열{col_j}: {date_val} | {row_val}')
        break
    except Exception as e:
        print(f'인코딩 {enc} 실패: {e}')
