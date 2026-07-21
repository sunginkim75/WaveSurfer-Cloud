# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트 2025-10-28 이후 전체 완료 거래 이력을 CSV 모듈로 정확히 파싱하여
trade_history_task_009a82ba.json 파일에 이식합니다.
컬럼 매핑:
  [9]  날짜 (매수일)
  [17] 실제 매수가
  [18] 실제 매수수량
  [21] 매도목표가
  [23] FALSE/TRUE (isMOC)
  [26] 실제 매도일
  [27] 실제 매도가
  [28] 실제 매도수량
  [33] 실현손익
  [34] 수익률
"""
import urllib.request, csv, io, json, re, os

url = 'https://docs.google.com/spreadsheets/d/1jOasXDShdBXHP37v0MruSz8y8HnhGi3PNxVa0vPGmzQ/export?format=csv&gid=879227790'
with urllib.request.urlopen(url) as r:
    raw = r.read()
data = raw.decode('utf-8-sig')

# CSV 파싱 (쉼표 내 숫자 처리를 위해)
reader = csv.reader(io.StringIO(data))
rows = list(reader)
print(f'총 {len(rows)}행')

def parse_kor_date(s):
    """'10.28.(화)' 또는 '07.01.(화)' 형식의 날짜를 ISO 형식으로 변환."""
    if not s:
        return None
    s = s.strip()
    # 공백 제거 후 매칭 (예: '12. 10.(수)' → '12.10.(수)')
    s = re.sub(r'\s+', '', s)
    m = re.match(r'(\d{1,2})\.(\d{2})\.\(', s)
    if not m:
        return None
    month = int(m.group(1))
    day = int(m.group(2))
    # 연도 추정: 10~12월 → 2025, 1~9월 → 2026
    year = 2025 if month >= 10 else 2026
    return f"{year}-{month:02d}-{day:02d}"

def safe_float(s):
    if not s:
        return None
    s = s.strip().replace(',', '').replace(' ', '')
    try:
        return float(s)
    except:
        return None

def safe_int(s):
    v = safe_float(s)
    return int(v) if v is not None else None

history_records = []

for i, cols in enumerate(rows):
    if i < 5:
        continue
    if len(cols) < 30:
        continue

    date_raw = cols[9].strip() if len(cols) > 9 else ''
    buy_date = parse_kor_date(date_raw)
    if not buy_date:
        continue

    buy_price = safe_float(cols[17]) if len(cols) > 17 else None
    buy_qty = safe_int(cols[18]) if len(cols) > 18 else None

    if not buy_price or not buy_qty or buy_qty <= 0:
        continue

    # 매도 관련
    sell_date_raw = cols[26].strip() if len(cols) > 26 else ''
    sell_date = parse_kor_date(sell_date_raw)
    sell_price = safe_float(cols[27]) if len(cols) > 27 else None
    sell_qty = safe_int(cols[28]) if len(cols) > 28 else None
    realized = safe_float(cols[33]) if len(cols) > 33 else None

    # 매도 완료 여부 판단
    is_sold = bool(sell_date and sell_price and sell_qty and sell_qty > 0)

    record = {
        "buyDate": buy_date,
        "buyPrice": buy_price,
        "buyQty": buy_qty,
        "buyAmt": round(buy_price * buy_qty, 2),
        "isSafe": True,  # 모드 정보가 없으므로 기본값
    }

    if is_sold:
        record["date"] = sell_date
        record["sellDate"] = sell_date
        record["sellPrice"] = sell_price
        record["sellQty"] = sell_qty
        record["sellAmt"] = round(sell_price * sell_qty, 2) if sell_price and sell_qty else 0
        record["realized"] = realized if realized is not None else 0
        record["type"] = "SELL"
    else:
        record["type"] = "HOLD"

    print(f"행{i}: {buy_date} 매수={buy_price}@{buy_qty} 매도={sell_date}@{sell_price}@{sell_qty} 실현={realized} {'[완료]' if is_sold else '[보유중]'}")
    history_records.append(record)

print(f'\n총 {len(history_records)}건 파싱 완료')
completed = [r for r in history_records if r["type"] == "SELL"]
holding = [r for r in history_records if r["type"] == "HOLD"]
print(f'  완료된 거래: {len(completed)}건')
print(f'  보유 중: {len(holding)}건')

# 완료된 이력만 trade_history에 저장
output_path = r'C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\config\trade_history_task_009a82ba.json'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(completed, f, indent=4, ensure_ascii=False)

print(f'\n[OK] trade_history 저장 완료: {output_path}')
print(f'     총 {len(completed)}건의 완료 이력')
