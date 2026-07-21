# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트에서 완료된 매매 이력(매수/매도가 모두 있는 행)만 추출하여
trade_history JSON DB 형식으로 변환합니다.
날짜는 한국어 요일 형식(07.01.(화)) → 연도 추정 후 ISO 형식으로 변환합니다.
"""
import urllib.request, json, re
from datetime import datetime, timedelta

url = 'https://docs.google.com/spreadsheets/d/1jOasXDShdBXHP37v0MruSz8y8HnhGi3PNxVa0vPGmzQ/export?format=csv&gid=879227790'
with urllib.request.urlopen(url) as r:
    raw = r.read()

data = raw.decode('utf-8-sig')
lines = data.strip().split('\n')
print(f'총 {len(lines)}행')

def parse_kor_date(s, reference_year=None):
    """'07.01.(화)' 형식의 날짜를 ISO 형식으로 변환. 연도는 reference_year 기준"""
    s = s.strip().strip('"').strip()
    m = re.match(r'(\d{2})\.(\d{2})\.\(', s)
    if not m:
        return None
    month = int(m.group(1))
    day = int(m.group(2))
    # 연도 추정: 10월이 시작이면 2025, 그 이후는 이어짐
    # reference_year가 주어지면 사용, 없으면 현재 연도 기준
    if reference_year is None:
        reference_year = 2025
    return f"{reference_year}-{month:02d}-{day:02d}"

def parse_float(s):
    s = s.strip().strip('"').replace(',', '').strip()
    try:
        return float(s)
    except:
        return None

def parse_int(s):
    s = s.strip().strip('"').replace(',', '').strip()
    try:
        return int(float(s))
    except:
        return None

# 첫 20행에서 컬럼 구조 파악
print('\n=== 처음 20행 컬럼 탐색 ===')
for i, line in enumerate(lines[:20]):
    cols = line.split(',')
    non_empty = [(j, c.strip().strip('"')) for j, c in enumerate(cols[:40]) if c.strip().strip('"')]
    if non_empty:
        print(f'행{i}({len(cols)}컬): {non_empty[:15]}')

# 데이터 행들에서 컬럼 9가 날짜인지 확인
print('\n=== 컬럼9 날짜 형식 확인 (행5~200) ===')
current_year = 2025
all_trades = []

for i, line in enumerate(lines[5:], start=5):
    cols = line.split(',')
    if len(cols) < 15:
        continue
    
    # 컬럼 9: 날짜
    date_raw = cols[9].strip().strip('"').strip()
    if not re.match(r'\d{2}\.\d{2}\.\(', date_raw):
        continue
    
    # 연도 추정: 10~12월은 2025, 1~9월은 2026
    m = re.match(r'(\d{2})\.(\d{2})\.\(', date_raw)
    if m:
        month = int(m.group(1))
        if month >= 10:
            year = 2025
        else:
            year = 2026
        day = int(m.group(2))
        iso_date = f"{year}-{month:02d}-{day:02d}"
    else:
        continue
    
    # 컬럼 10: 종가, 컬럼 13: 매수예정액, 컬럼 14: LOC매수목표가, 컬럼 15: 매수수량
    # 컬럼 16: 실제매수가, 컬럼 17: 실제매수수량
    # 뒤쪽에 매도 날짜/가격 확인
    close_val = parse_float(cols[10]) if len(cols) > 10 else None
    buy_price = parse_float(cols[16]) if len(cols) > 16 else None
    buy_qty = parse_int(cols[17]) if len(cols) > 17 else None
    
    # 매도 관련: 컬럼 21(매도목표일), 컬럼 22(사이클일수), 컬럼 23(매도일), 컬럼 24(매도가), 컬럼 25(매도수량), 컬럼 26(매도금액)
    sell_date_raw = cols[23].strip().strip('"').strip() if len(cols) > 23 else ''
    sell_price = parse_float(cols[24]) if len(cols) > 24 else None
    sell_qty = parse_int(cols[25]) if len(cols) > 25 else None
    realized = parse_float(cols[28]) if len(cols) > 28 else None
    
    # 매도 날짜 파싱
    sell_date = None
    if re.match(r'\d{2}\.\d{2}\.\(', sell_date_raw):
        sm = re.match(r'(\d{2})\.(\d{2})\.\(', sell_date_raw)
        if sm:
            smonth = int(sm.group(1))
            sday = int(sm.group(2))
            syear = 2025 if smonth >= 10 else 2026
            sell_date = f"{syear}-{smonth:02d}-{sday:02d}"
    
    if buy_price and buy_qty and buy_qty > 0:
        trade = {
            'row': i,
            'date': iso_date,
            'close': close_val,
            'buyDate': iso_date,
            'buyPrice': buy_price,
            'buyQty': buy_qty,
            'sellDate': sell_date,
            'sellPrice': sell_price,
            'sellQty': sell_qty,
            'realized': realized,
        }
        all_trades.append(trade)
        print(f'행{i}: {iso_date} 매수={buy_price}@{buy_qty} 매도={sell_date}@{sell_price}@{sell_qty} 실현={realized}')

print(f'\n총 거래 이력: {len(all_trades)}건')
