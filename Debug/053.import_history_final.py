# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트의 2025-10-28 이후 전체 완료 거래 이력을 정확한 컬럼 매핑으로 파싱하여
config/trade_history_task_009a82ba.json 에 이식합니다.

CSV 컬럼 매핑 (CSV 파서 기준):
  [9]  날짜 (해당 거래 날짜)
  [16] 실제 매수가
  [17] 실제 매수수량
  [18] 실제 매수금액
  [24] 실제 매도일
  [25] 실제 매도가
  [26] 실제 매도수량
  [27] 실제 매도금액
  [29] 실현손익
"""
import urllib.request, csv, io, json, re, os

url = 'https://docs.google.com/spreadsheets/d/1jOasXDShdBXHP37v0MruSz8y8HnhGi3PNxVa0vPGmzQ/export?format=csv&gid=879227790'
with urllib.request.urlopen(url) as r:
    raw = r.read()
data = raw.decode('utf-8-sig')

reader = csv.reader(io.StringIO(data))
rows = list(reader)
print(f'총 {len(rows)}행')

def parse_kor_date(s):
    """'10.28.(화)' → ISO 날짜. 연도 추정: 10~12월=2025, 1~9월=2026"""
    if not s:
        return None
    s = re.sub(r'\s+', '', s.strip())
    m = re.match(r'(\d{1,2})\.(\d{2})\.\(', s)
    if not m:
        return None
    month = int(m.group(1))
    day = int(m.group(2))
    year = 2025 if month >= 10 else 2026
    return f"{year}-{month:02d}-{day:02d}"

def safe_float(s):
    if not s:
        return None
    s = s.strip().replace(',', '').replace(' ', '')
    try:
        v = float(s)
        return v if v != 0.0 else None
    except:
        return None

def safe_int(s):
    v = safe_float(s)
    return int(v) if v is not None else None

history_records = []

DATA_START = 9  # 헤더 행 이후 실제 데이터 시작

for i, cols in enumerate(rows):
    if i < DATA_START:
        continue
    if len(cols) < 27:
        continue

    # 날짜 파싱 (컬럼 9)
    date_raw = cols[9].strip() if len(cols) > 9 else ''
    buy_date = parse_kor_date(date_raw)
    if not buy_date:
        continue

    # 매수 정보 (컬럼 16, 17)
    buy_price = safe_float(cols[16]) if len(cols) > 16 else None
    buy_qty = safe_int(cols[17]) if len(cols) > 17 else None

    if not buy_price or not buy_qty or buy_qty <= 0:
        continue

    # 매도 정보 (컬럼 24, 25, 26, 27)
    sell_date_raw = cols[24].strip() if len(cols) > 24 else ''
    sell_date = parse_kor_date(sell_date_raw)
    sell_price = safe_float(cols[25]) if len(cols) > 25 else None
    sell_qty = safe_int(cols[26]) if len(cols) > 26 else None

    # 실현손익 (컬럼 30: 실현손익, 컬럼 29는 수수료)
    realized = None
    if len(cols) > 30:
        realized = safe_float(cols[30])

    # 매도 완료 여부
    is_sold = bool(sell_date and sell_price and sell_qty and sell_qty > 0)

    # 시드증액 (컬럼 36) 및 입출금 (컬럼 37) 파싱
    seed_add_val = safe_float(cols[36]) if len(cols) > 36 else None
    dep_with_val = safe_float(cols[37]) if len(cols) > 37 else None

    if seed_add_val:
        history_records.append({
            "date": buy_date,
            "type": "SEED_ADD",
            "amount": seed_add_val
        })
        print(f'행{i}: 시드증액 {seed_add_val} 감지 (날짜: {buy_date})')

    if dep_with_val:
        history_records.append({
            "date": buy_date,
            "type": "DEPOSIT_WITHDRAW",
            "amount": dep_with_val
        })
        print(f'행{i}: 입출금 {dep_with_val} 감지 (날짜: {buy_date})')

    print(f'행{i}: {buy_date} 매수={buy_price}@{buy_qty} → '
          f'매도={sell_date}@{sell_price}@{sell_qty} 실현={realized} '
          f'{"[완료]" if is_sold else "[진행중]"}')

    if is_sold:
        record = {
            "buyDate": buy_date,
            "buyPrice": buy_price,
            "buyQty": buy_qty,
            "buyAmt": round(buy_price * buy_qty, 2),
            "date": sell_date,
            "sellDate": sell_date,
            "sellPrice": sell_price,
            "sellQty": sell_qty,
            "sellAmt": round(sell_price * sell_qty, 2),
            "realized": realized if realized is not None else 0.0,
            "type": "SELL"
        }
        history_records.append(record)

print(f'\n총 완료 및 변동 이력: {len(history_records)}건')

# 저장
output_path = r'C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\config\trade_history_task_009a82ba.json'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(history_records, f, indent=4, ensure_ascii=False)

print(f'[OK] 저장 완료: {output_path}')

