# -*- coding: utf-8 -*-
"""
테스트 목적:
12/12일 시드 증액 발생 시점 전후의 구글 시트 데이터를 정밀 분석하여
시드 증액이 복리자금(compounding_cash)에 어떻게 가산되는지 수식적으로 규명합니다.
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

print("=== [구글 시트] 12/9 ~ 12/16 ===")
for i in range(35, 50):
    cols = rows[i]
    date_raw = cols[9].strip()
    d = parse_kor_date(date_raw)
    if not d: continue
    
    def g(idx):
        if idx < len(cols): return cols[idx].strip()
        return ''
        
    print(f"행 {i:3d} [{d}] | 복리자금(35): {g(35):>10} | 시드증액(36): {g(36):>10} | 입출금(37): {g(37):>10} | 예수금(38): {g(38):>10} | 총자산(41): {g(41):>10} | 갱신여부(33): {g(33):>5}")
