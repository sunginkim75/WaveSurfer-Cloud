# -*- coding: utf-8 -*-
"""
테스트 목적:
7월 1일(행 177) 이후의 거래 행들을 돌면서,
매수(17열)는 완료되었으나 매도(26열)가 비어있어
실질적으로 '보유 중'인 7월 활성 배치들을 찾아내어 수량 합이 91주가 되는지 대조합니다.
"""
import os
import csv

csv_path = r"C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\DOCS\SI_VR_WAVE_SURFER_V2.5(251027)_8265_자동화 - JJ.csv"

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

print("=== 7월 미매도 활성 배치 정밀 추적 ===")
july_active = []

for idx in range(177, len(rows)):
    r = rows[idx]
    if len(r) > 28:
        date = r[9].strip()
        buy_qty_str = r[17].strip() # 매수량 (R열)
        sell_qty_str = r[26].strip() # 매도량 (AA열)
        
        if date and buy_qty_str:
            try:
                buy_qty = int(buy_qty_str.replace(",", ""))
                sell_qty = 0
                if sell_qty_str:
                    sell_qty = int(sell_qty_str.replace(",", ""))
                
                # 매수량은 있고 매도량은 아직 0(비어있음)인 행 찾기
                if buy_qty > 0 and sell_qty == 0:
                    buy_price = float(r[16].replace(",", "").strip())
                    print(f"활성 배치 발견: [행 {idx:03d} - {date}] 매수량: {buy_qty}주 | 매수가: ${buy_price:.2f}")
                    july_active.append({
                        "date": date,
                        "qty": buy_qty,
                        "price": buy_price,
                        "row": idx
                    })
            except Exception as e:
                pass

print(f"\n총 활성 배치 개수: {len(july_active)}")
total_qty = sum(b["qty"] for b in july_active)
print(f"활성 배치 수량 합계: {total_qty}주 (목표: 91주)")
