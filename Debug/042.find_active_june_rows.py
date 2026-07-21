# -*- coding: utf-8 -*-
"""
테스트 목적:
구글 시트 CSV 백업에서 2026-07-01 이전(행 174 이전)의 행들을 조사하여,
매수(R열)는 발생했으나 아직 매도(Y열, Z열 등)가 완료되지 않아
현재 7월 계좌에 이월 보유량 8주로 남아 있는 진짜 활성 배치들을 추적합니다.
"""
import os
import csv

csv_path = r"C:\Users\SunginKIm\PYthon_WorkSpace\WaveSurfer-Cloud\DOCS\SI_VR_WAVE_SURFER_V2.5(251027)_8265_자동화 - JJ.csv"

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

print("=== 6월 이전 매수 미매도 잔여 행 추적 ===")
active_old_batches = []

# 행 9번부터 174번까지 루프 (6월 말 이전)
for idx in range(9, 175):
    r = rows[idx]
    if len(r) > 28:
        date = r[9].strip()
        buy_qty_str = r[17].strip() # 매수량 (R열)
        sell_qty_str = r[26].strip() # 매도량 (AA열)
        
        # 매수량은 양수인데 매도량이 비어있거나 0인 행 = 아직 보유 중인 배치!
        if buy_qty_str:
            try:
                buy_qty = int(buy_qty_str.replace(",", ""))
                sell_qty = 0
                if sell_qty_str:
                    sell_qty = int(sell_qty_str.replace(",", ""))
                    
                # 매수량과 매도량이 불일치하거나 매도가 안 된 경우
                if buy_qty > 0 and sell_qty == 0:
                    buy_price = float(r[16].replace(",", "").strip())
                    print(f"발견! [행 {idx:03d} - {date}] 매수량: {buy_qty}주 | 매수가: ${buy_price:.2f} | 매도량: {sell_qty} (미매도!)")
                    active_old_batches.append({
                        "row": idx,
                        "date": date,
                        "qty": buy_qty,
                        "price": buy_price
                    })
            except Exception as e:
                pass

print(f"\n총 미매도 배치 개수: {len(active_old_batches)}")
total_qty = sum(b["qty"] for b in active_old_batches)
print(f"미매도 이월 총합 수량: {total_qty}주")
