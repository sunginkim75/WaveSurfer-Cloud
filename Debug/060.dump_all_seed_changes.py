# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트의 전체 행을 순회하면서 [36] 시드증액, [37] 입출금에
값이 존재하는 행을 모두 찾아내어 덤프합니다.
"""
import urllib.request, csv, io, sys, re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

url = 'https://docs.google.com/spreadsheets/d/1jOasXDShdBXHP37v0MruSz8y8HnhGi3PNxVa0vPGmzQ/export?format=csv&gid=879227790'
with urllib.request.urlopen(url) as r:
    raw = r.read()
data = raw.decode('utf-8-sig')
reader = csv.reader(io.StringIO(data))
rows = list(reader)

def parse_kor_date(s):
    s = re.sub(r'\s+', '', s.strip())
    m = re.match(r'(\d{1,2})\.(\d{2})\.\(', s)
    if not m: return None
    month, day = int(m.group(1)), int(m.group(2))
    year = 2025 if month >= 10 else 2026
    return f"{year}-{month:02d}-{day:02d}"

print("=== 시드 증액 / 입출금 내역 전체 추출 ===")
count = 0
for i in range(9, len(rows)):
    cols = rows[i]
    if len(cols) < 39: continue
    
    date_raw = cols[9].strip()
    d = parse_kor_date(date_raw)
    
    seed_add = cols[36].strip()
    dep_with = cols[37].strip()
    
    if seed_add or dep_with:
        count += 1
        print(f"행 {i:3d} | 날짜: {date_raw} ({d}) | 시드증액: {seed_add:>10} | 입출금: {dep_with:>10}")

print(f"총 {count}건 추출됨")
