# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트 10/28 ~ 11/12 구간의 전 컬럼을 API 응답과 1:1 비교합니다.
"""
import urllib.request, csv, io, json, re

# ── 구글 시트 CSV 파싱 ──
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

def sf(s):
    try: return float(s.strip().replace(',',''))
    except: return None

# 시트에서 10/28 ~ 11/12 행 추출
print("=" * 120)
print("구글 시트 원본 (10/28 ~ 11/12)")
print("=" * 120)

TARGET_DATES = {
    '2025-10-28','2025-10-29','2025-10-30','2025-10-31',
    '2025-11-03','2025-11-04','2025-11-05','2025-11-06',
    '2025-11-07','2025-11-10','2025-11-11','2025-11-12',
}

sheet_rows = {}
for i, cols in enumerate(rows):
    if i < 9: continue
    if len(cols) < 10: continue
    date_raw = cols[9].strip()
    d = parse_kor_date(date_raw)
    if d not in TARGET_DATES: continue

    # 컬럼 매핑 (CSV 파서 기준)
    # [9]=날짜, [10]=종가, [12]=변동률, [13]=매수예정액, [14]=LOC목표가, [15]=목표수량
    # [16]=매수가, [17]=매수수량, [18]=매수금액
    # [24]=매도일, [25]=매도가, [26]=매도수량, [27]=매도금액
    # [29]=수수료, [30]=실현손익, [31]=수익률, [32]=누적손익
    # [35]=복리자금(last_compounding_cash)
    # [38]=예수금(cash), [39]=보유수량(heldQty), [40]=평가금(evalAmt), [41]=총자산

    def g(idx): 
        v = cols[idx].strip() if len(cols)>idx else ''
        return v

    row_data = {
        'date'       : d,
        'close'      : g(10),
        'change'     : g(12),
        'buyLimitAmt': g(13),
        'targetBuy'  : g(14),
        'targetQty'  : g(15),
        'buyPrice'   : g(16),
        'buyQty'     : g(17),
        'buyAmt'     : g(18),
        'sellDate'   : g(24),
        'sellPrice'  : g(25),
        'sellQty'    : g(26),
        'sellAmt'    : g(27),
        'fee'        : g(29),
        'realized'   : g(30),
        'profitRate' : g(31),
        'accumProfit': g(32),
        'compoundingCash': g(35),
        'cash'       : g(38),
        'heldQty'    : g(39),
        'evalAmt'    : g(40),
        'totalAsset' : g(41),
        'totalProfitRate': g(42),
    }
    sheet_rows[d] = row_data
    print(f"[시트] {d} | 종가:{g(10):>8} | 매수가:{g(16):>8} | 매수량:{g(17):>4} | 매수금:{g(18):>10} | 매도일:{g(24):>12} | 매도가:{g(25):>8} | 매도량:{g(26):>4} | 수수료:{g(29):>8} | 실현:{g(30):>8} | 누적:{g(32):>10} | 예수금:{g(38):>12} | 보유:{g(39):>4} | 평가금:{g(40):>12} | 총자산:{g(41):>12}")

# ── API 호출 ──
print()
print("=" * 120)
print("API 응답 (10/28 ~ 11/12)")
print("=" * 120)

import time
time.sleep(2)
req = urllib.request.Request("http://localhost:8000/api/v1/tasks/task_009a82ba/matching")
with urllib.request.urlopen(req) as r:
    result = json.loads(r.read())

api_rows = {}
for r in result.get('detailedTxTable', []):
    d = r.get('date','')
    if d in TARGET_DATES:
        api_rows[d] = r

def fv(v): 
    if v is None or v == '' or v == '-': return '         -'
    try: return f"{float(str(v).replace(',','')):.2f}"
    except: return str(v)

for d in sorted(TARGET_DATES):
    ar = api_rows.get(d)
    if not ar: continue
    print(f"[ API] {d} | 종가:{fv(ar.get('close')):>8} | 매수가:{fv(ar.get('buyPrice')):>8} | 매수량:{str(ar.get('buyQty','')):>4} | 매수금:{fv(ar.get('buyAmt')):>10} | 매도일:{str(ar.get('sellDate','')):>12} | 매도가:{fv(ar.get('sellPrice')):>8} | 매도량:{str(ar.get('sellQty','')):>4} | 수수료:{fv(ar.get('fee')):>8} | 실현:{fv(ar.get('todayRealized')):>8} | 누적:{fv(ar.get('accumProfit')):>10} | 예수금:{fv(ar.get('cash')):>12} | 보유:{str(ar.get('heldQty','')):>4} | 평가금:{fv(ar.get('evalAmt')):>12} | 총자산:{fv(ar.get('totalAsset')):>12}")

print()
print("=" * 120)
print("비교 (DIFF - 불일치 항목)")
print("=" * 120)

def compare_val(sheet_v, api_v, label):
    sv = sf(str(sheet_v).replace(',',''))
    av_str = str(api_v).replace(',','') if api_v is not None else ''
    av = sf(av_str)
    if sv is None and (api_v is None or api_v == '' or api_v == '-'):
        return
    if sv is not None and av is not None:
        if abs(sv - av) > 0.5:
            print(f"  ❌ {label:20s}: 시트={sv:.2f}  API={av:.2f}  (차이={sv-av:.2f})")
    elif sv != av:
        print(f"  ❌ {label:20s}: 시트={sheet_v}  API={api_v}")

for d in sorted(TARGET_DATES):
    sr = sheet_rows.get(d)
    ar = api_rows.get(d)
    if not sr or not ar:
        continue
    diffs = []
    checks = [
        ('buyPrice',   sr['buyPrice'],    ar.get('buyPrice')),
        ('buyQty',     sr['buyQty'],      ar.get('buyQty')),
        ('buyAmt',     sr['buyAmt'],      ar.get('buyAmt')),
        ('sellPrice',  sr['sellPrice'],   ar.get('sellPrice')),
        ('sellQty',    sr['sellQty'],     ar.get('sellQty')),
        ('fee',        sr['fee'],         ar.get('fee')),
        ('todayRealized', sr['realized'], ar.get('todayRealized')),
        ('accumProfit',sr['accumProfit'], ar.get('accumProfit')),
        ('cash(예수금)',sr['cash'],        ar.get('cash')),
        ('heldQty',    sr['heldQty'],     ar.get('heldQty')),
        ('evalAmt',    sr['evalAmt'],     ar.get('evalAmt')),
        ('totalAsset', sr['totalAsset'],  ar.get('totalAsset')),
    ]
    has_diff = False
    for label, sv, av in checks:
        s = sf(str(sv).replace(',',''))
        a_str = str(av).replace(',','') if av is not None else ''
        a = sf(a_str)
        if s is not None and a is not None and abs(s-a) > 0.5:
            if not has_diff:
                print(f"\n[{d}]")
                has_diff = True
            print(f"  ❌ {label:20s}: 시트={sv:>12}  API={str(av):>12}  차이={s-a:.2f}")
        elif sv and av and str(sv).replace(',','').replace('.','') and str(av).replace(',','').replace('.',''):
            if s is None and a is None:
                pass
            elif s is not None and a is None:
                if not has_diff:
                    print(f"\n[{d}]")
                    has_diff = True
                print(f"  ❌ {label:20s}: 시트={sv:>12}  API=None")
