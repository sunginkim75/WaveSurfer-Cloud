# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트와 API 응답 간의 10/28 ~ 11/12 전 컬럼의 값을 정확하게 상세 비교합니다.
출력 인코딩 오류를 방지하기 위해 sys.stdout의 인코딩을 utf-8로 설정합니다.
"""
import urllib.request, csv, io, json, re, sys

# 출력 인코딩을 강제로 utf-8로 설정하여 윈도우 cmd/powershell 환경 오류 방지
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

TARGET_DATES = [
    '2025-10-28','2025-10-29','2025-10-30','2025-10-31',
    '2025-11-03','2025-11-04','2025-11-05','2025-11-06',
    '2025-11-07','2025-11-10','2025-11-11','2025-11-12',
]

sheet_rows = {}
for i, cols in enumerate(rows):
    if i < 9: continue
    if len(cols) < 10: continue
    date_raw = cols[9].strip()
    d = parse_kor_date(date_raw)
    if d not in TARGET_DATES: continue

    def g(idx):
        if idx < len(cols):
            return cols[idx].strip()
        return ''

    sheet_rows[d] = {
        'date': d,
        'close': g(10),
        'mode': g(11),
        'change': g(12),
        'buyLimitAmt': g(13),
        'targetBuy': g(14),
        'targetQty': g(15),
        'buyPrice': g(16),
        'buyQty': g(17),
        'buyAmt': g(18),
        'sellDate': g(24),
        'sellPrice': g(25),
        'sellQty': g(26),
        'sellAmt': g(27),
        'fee': g(29),
        'realized': g(30),
        'profitRate': g(31),
        'accumProfit': g(32),
        'compoundingCash': g(35),
        'cash': g(38),
        'heldQty': g(39),
        'evalAmt': g(40),
        'totalAsset': g(41),
        'totalProfitRate': g(42),
    }

# API 호출
req = urllib.request.Request("http://localhost:8000/api/v1/tasks/task_009a82ba/matching")
with urllib.request.urlopen(req) as r:
    result = json.loads(r.read())

api_rows = {}
for r in result.get('detailedTxTable', []):
    d = r.get('date','')
    if d in TARGET_DATES:
        api_rows[d] = r

print("=" * 100)
print(f"{'날짜':12s} | {'필드명':20s} | {'시트 값':20s} | {'API 값':20s} | {'상태'}")
print("=" * 100)

fields_to_compare = [
    ('close', '종가'),
    ('mode', '매매모드'),
    ('change', '변동률'),
    ('buyLimitAmt', '매수예정액'),
    ('targetBuy', 'LOC매수목표'),
    ('targetQty', '목표량'),
    ('buyPrice', '매수가'),
    ('buyQty', '매수량'),
    ('buyAmt', '매수금액'),
    ('sellDate', '매도일'),
    ('sellPrice', '매도가'),
    ('sellQty', '매도량'),
    ('sellAmt', '매도금액'),
    ('fee', '수수료'),
    ('realized', '당일실현'),
    ('accumProfit', '누적손익'),
    ('cash', '예수금'),
    ('heldQty', '보유량'),
    ('evalAmt', '평가금'),
    ('totalAsset', '총자산'),
]

def clean_and_float(v):
    if v is None or v == '' or v == '-' or v == '보유중':
        return None
    v_str = str(v).replace(',','').replace('%','').replace('주','').replace('$','').strip()
    try:
        return float(v_str)
    except:
        return str(v_str)

for d in TARGET_DATES:
    sr = sheet_rows.get(d)
    ar = api_rows.get(d)
    if not sr:
        print(f"{d} | 시트 데이터 없음")
        continue
    if not ar:
        print(f"{d} | API 데이터 없음")
        continue

    print(f"\n--- {d} 비교 ---")
    for field_key, field_name in fields_to_compare:
        s_val = sr.get(field_key, '')
        
        # API 매핑 이름 대응
        if field_key == 'fee':
            a_val = ar.get('fee', '')
        elif field_key == 'realized':
            a_val = ar.get('todayRealized', '')
        elif field_key == 'mode':
            a_val = ar.get('mode', '')
        else:
            a_val = ar.get(field_key, '')

        # 비교용 전처리
        s_clean = clean_and_float(s_val)
        a_clean = clean_and_float(a_val)

        is_match = False
        if s_clean is None and a_clean is None:
            is_match = True
        elif isinstance(s_clean, float) and isinstance(a_clean, float):
            # 오차 허용 범위 1.0 이내
            if abs(s_clean - a_clean) < 1.0:
                is_match = True
        elif str(s_clean).strip() == str(a_clean).strip():
            is_match = True

        status_str = "일치" if is_match else "불일치 ❌"
        print(f"{d} | {field_name:15s} | 시트: {str(s_val):18s} | API: {str(a_val):18s} | {status_str}")
