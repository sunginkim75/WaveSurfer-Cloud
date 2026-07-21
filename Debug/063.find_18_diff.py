# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트와 API 간의 각 거래일자별 실현손익(realized)을 정밀 비교하여
정확히 18.00달러의 오차가 발생하는 날짜를 찾아냅니다.
"""
import urllib.request, csv, io, json, sys, re

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

sheet_realized = {}
for i, cols in enumerate(rows):
    if i < 9: continue
    if len(cols) < 31: continue
    date_raw = cols[9].strip()
    d = parse_kor_date(date_raw)
    if not d: continue
    
    # 세전 실현손익 [30]
    r_val = cols[30].strip().replace(',','')
    try:
        val = float(r_val)
        if val != 0.0:
            sheet_realized[d] = val
    except:
        pass

# API 호출
req = urllib.request.Request("http://localhost:8000/api/v1/tasks/task_009a82ba/matching")
with urllib.request.urlopen(req) as r:
    result = json.loads(r.read())

api_realized = {}
for r in result.get('detailedTxTable', []):
    d = r.get('date','')
    val = r.get('todayRealized')
    if val is not None and val != '' and val != '-':
        try:
            f_val = float(val)
            if f_val != 0.0:
                api_realized[d] = f_val
        except:
            pass

print("=== 실현손익 차이 분석 ===")
all_dates = sorted(list(set(sheet_realized.keys()) | set(api_realized.keys())))
for d in all_dates:
    sv = sheet_realized.get(d, 0.0)
    av = api_realized.get(d, 0.0)
    diff = sv - av
    if abs(diff) > 0.01:
        print(f"[{d}] 시트: {sv:>10.2f} | API: {av:>10.2f} | 차이: {diff:>10.2f}")
