# -*- coding: utf-8 -*-
"""테스트 목적: 11월 trade_history 데이터 realized 값 검증"""
import json
with open('config/trade_history_task_009a82ba.json', encoding='utf-8') as f:
    data = json.load(f)
for r in data:
    bd = r.get('buyDate', '')
    if '2025-11' in bd:
        print(f"{bd} @{r['buyPrice']}x{r['buyQty']} -> 매도:{r['sellDate']} @{r['sellPrice']} 실현:{r['realized']}")
