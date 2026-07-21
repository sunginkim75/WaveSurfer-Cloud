# -*- coding: utf-8 -*-
"""
테스트 목적:
7/6 ~ 7/13 사이의 구글 시트 데이터와 API의 매수예정액, 복리자금, 예수금 등을 상세 덤프하여 비교합니다.
"""
import urllib.request, csv, io, json, sys, re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 1. 구글 시트 데이터 덤프
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

print("=== [구글 시트] 7/6 ~ 7/13 ===")
sheet_data = {}
for i, cols in enumerate(rows):
    if i < 9: continue
    if len(cols) < 10: continue
    date_raw = cols[9].strip()
    d = parse_kor_date(date_raw)
    if not d: continue
    if not d.startswith("2026-07"): continue
    
    def g(idx):
        if idx < len(cols): return cols[idx].strip()
        return ''
        
    sheet_data[d] = {
        'buyLimitAmt': g(13),
        'compoundingCash': g(35),
        'cash': g(38),
        'totalAsset': g(41),
        'close': g(10),
        'buyPrice': g(16),
        'buyQty': g(17),
        'realized': g(30)
    }
    print(f"[{d}] 매수예정: {g(13):>10} | 복리자금: {g(35):>10} | 예수금: {g(38):>10} | 총자산: {g(41):>10} | 매수가: {g(16):>6} | 매수량: {g(17):>3}")

# 2. API 데이터 덤프
print("\n=== [API 응답] 7/6 ~ 7/13 ===")
req = urllib.request.Request("http://localhost:8000/api/v1/tasks/task_009a82ba/matching")
with urllib.request.urlopen(req) as r:
    result = json.loads(r.read())

for r in result.get('detailedTxTable', []):
    d = r.get('date','')
    if not d.startswith("2026-07"): continue
    print(f"[{d}] 매수예정: {r.get('buyLimitAmt'):>10.2f} | 복리자금: {r.get('updatedCompoundingCash'):>10} | 예수금: {r.get('cash'):>10.2f} | 총자산: {r.get('totalAsset'):>10.2f} | 매수가: {r.get('buyPrice'):>6} | 매수량: {r.get('buyQty'):>3}")
