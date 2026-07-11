# 테스트 목적: SOXL 실제 종가(7/1~) 기반 WaveSurfer 전략 시뮬레이션 이력 생성
# 생성된 데이터를 trade_batches, trade_history JSON으로 저장하고 결과 출력

import yfinance as yf
import json
import os
import datetime

SEED = 10000
SPLIT = 7
SAFE_BUY_PCT = 3.0
SAFE_SELL_PCT = 0.2
AGG_BUY_PCT = 5.0
AGG_SELL_PCT = 2.5
SAFE_LIMIT = 30
AGG_LIMIT = 7

START_DATE = "2026-07-01"
TODAY = datetime.date.today().strftime("%Y-%m-%d")
TICKER = "SOXL"
RSI_TICKER = "QQQ"

print(f"=== SOXL WaveSurfer 시뮬레이션 ({START_DATE} ~ {TODAY}) ===")
print(f"원금: ${SEED}, 분할: {SPLIT}분할, 안전매수: {SAFE_BUY_PCT}%, 안전매도: {SAFE_SELL_PCT}%\n")

# ----- 1. 가격 데이터 다운로드 -----
# 7/1일의 전영업일 종가를 구하기 위해 6/25일부터 다운로드
df_soxl = yf.download(TICKER, start="2026-06-25", end=TODAY, progress=False, auto_adjust=True)
df_qqq_wk = yf.download(RSI_TICKER, period="1y", interval="1wk", progress=False, auto_adjust=True)

if df_soxl.empty:
    print("ERROR: SOXL 데이터를 불러올 수 없습니다.")
    exit(1)

# 종가 시리즈
soxl_close = df_soxl['Close']
if hasattr(soxl_close, 'squeeze'):
    soxl_close = soxl_close.squeeze()

# ----- 2. QQQ 주간 RSI 계산 -----
qqq_close = df_qqq_wk['Close']
if hasattr(qqq_close, 'squeeze'):
    qqq_close = qqq_close.squeeze()

delta = qqq_close.diff()
gain = delta.where(delta > 0, 0.0)
loss = -delta.where(delta < 0, 0.0)
avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
rsi_series = 100 - (100 / (1 + avg_gain / avg_loss))

prev_rsi = float(rsi_series.iloc[-2])
latest_rsi = float(rsi_series.iloc[-1])
trend = "상승" if latest_rsi >= prev_rsi else "하락"

# 모드 판별 (시작 시점)
current_mode = "안전모드"
if trend == "상승":
    if prev_rsi <= 50 < latest_rsi or 50 < latest_rsi < 60 or latest_rsi < 35:
        current_mode = "공세모드"

print(f"[QQQ RSI] prev={prev_rsi:.2f}, latest={latest_rsi:.2f}, trend={trend} => {current_mode}\n")

# ----- 3. 날짜별 시뮬레이션 -----
batches = []
history = []
cash = float(SEED)
buy_limit_per_split = cash / SPLIT
batch_id_counter = 1

print(f"{'날짜':<12} {'종가':>8} {'모드':<8} {'매수LOC':>9} {'매수량':>5} {'결과'}")
print("-" * 60)

dates = sorted(soxl_close.index)
prev_close = None

for i, date in enumerate(dates):
    try:
        close = float(soxl_close.iloc[i] if hasattr(soxl_close, 'iloc') else soxl_close[date])
        if hasattr(close, '__len__'):
            close = float(close.iloc[0])
    except Exception as e:
        print(f"  {str(date)[:10]}: 가격 파싱 오류 {e}")
        continue

    date_str = str(date)[:10]

    # 7/1 이전의 데이터는 prev_close 갱신만 하고 시뮬레이션은 실행하지 않음
    if date_str < "2026-07-01":
        prev_close = close
        continue

    if prev_close is None:
        prev_close = close
        continue

    buy_pct = AGG_BUY_PCT if current_mode == "공세모드" else SAFE_BUY_PCT

    sell_pct = AGG_SELL_PCT if current_mode == "공세모드" else SAFE_SELL_PCT

    # LOC 매수 목표가 (전일 종가 기준)
    target_buy = round(prev_close * (1 + buy_pct / 100), 2)
    buy_qty = int(buy_limit_per_split // target_buy)

    # 매도 처리 (보유 배치 순회)
    sold_ids = []
    for batch in batches:
        if batch["buyDate"] == date_str:
            batch["cycleDays"] += 1
            continue
        bmode = batch["buyMode"]
        b_limit = AGG_LIMIT if bmode == "공세모드" else SAFE_LIMIT
        b_sell_pct = AGG_SELL_PCT if bmode == "공세모드" else SAFE_SELL_PCT
        target_sell = round(batch["buyPrice"] * (1 + b_sell_pct / 100), 2)

        if batch["cycleDays"] >= b_limit:
            # MOC 강제 청산
            sell_price = round(close, 2)
            profit = round((sell_price - batch["buyPrice"]) * batch["qty"], 2)
            history.append({
                "date": date_str,
                "type": "SELL",
                "order_type": "MOC",
                "buyPrice": batch["buyPrice"],
                "sellPrice": sell_price,
                "qty": batch["qty"],
                "realized_profit": profit,
                "buyDate": batch["buyDate"],
                "buyMode": bmode,
                "reason": "MOC강제청산"
            })
            cash += sell_price * batch["qty"]
            sold_ids.append(batch["id"])
            print(f"{date_str:<12} {close:>8.2f} {current_mode:<8}  MOC청산 ${sell_price} 손익${profit:+.2f}")
        elif close >= target_sell:
            # LOC 매도 체결
            sell_price = round(close, 2)
            profit = round((sell_price - batch["buyPrice"]) * batch["qty"], 2)
            history.append({
                "date": date_str,
                "type": "SELL",
                "order_type": "LOC",
                "buyPrice": batch["buyPrice"],
                "sellPrice": sell_price,
                "qty": batch["qty"],
                "realized_profit": profit,
                "buyDate": batch["buyDate"],
                "buyMode": bmode,
                "reason": f"LOC매도"
            })
            cash += sell_price * batch["qty"]
            sold_ids.append(batch["id"])
            print(f"{date_str:<12} {close:>8.2f} {current_mode:<8}  LOC매도 ${sell_price} 손익${profit:+.2f}")

    batches = [b for b in batches if b["id"] not in sold_ids]

    # 경과일 증가 (아직 안 팔린 배치)
    for b in batches:
        b["cycleDays"] += 1

    # LOC 매수 처리 (당일 종가가 목표가 이하면 체결 가정)
    if buy_qty > 0 and close <= target_buy and cash >= target_buy * buy_qty:
        buy_price = round(close, 2)
        cost = round(buy_price * buy_qty, 2)
        batch_id = f"B_{date_str.replace('-','')}_{batch_id_counter:03d}"
        batch_id_counter += 1
        batches.append({
            "id": batch_id,
            "buyPrice": buy_price,
            "qty": buy_qty,
            "cycleDays": 0,
            "buyMode": current_mode,
            "buyDate": date_str
        })
        history.append({
            "date": date_str,
            "type": "BUY",
            "order_type": "LOC",
            "buyPrice": buy_price,
            "sellPrice": None,
            "qty": buy_qty,
            "realized_profit": None,
            "buyDate": date_str,
            "buyMode": current_mode,
            "reason": f"LOC매수(목표${target_buy})"
        })
        cash -= cost
        print(f"{date_str:<12} {close:>8.2f} {current_mode:<8} {target_buy:>9.2f} {buy_qty:>5}  매수체결 ${buy_price}x{buy_qty}주 (잔액${cash:.0f})")
    else:
        reason = "미체결(고가)" if close > target_buy else "잔액부족"
        print(f"{date_str:<12} {close:>8.2f} {current_mode:<8} {target_buy:>9.2f}   -   {reason}")

    prev_close = close

print("\n" + "=" * 60)
print(f"\n[최종 결과]")
print(f"잔여 현금: ${cash:.2f}")
print(f"보유 배치 수: {len(batches)}")
for b in batches:
    print(f"  - {b['buyDate']} | {b['qty']}주 @ ${b['buyPrice']:.2f} | D+{b['cycleDays']} | {b['buyMode']}")
total_profit = sum(h['realized_profit'] for h in history if h.get('realized_profit') is not None)
print(f"총 실현 손익: ${total_profit:.2f}")
print(f"총 체결 이력: {len(history)}건 (매수:{sum(1 for h in history if h['type']=='BUY')}, 매도:{sum(1 for h in history if h['type']=='SELL')})")

# ----- 4. JSON 파일 저장 -----
config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config")

batches_path = os.path.join(config_dir, "trade_batches_task_3917820f.json")
history_path = os.path.join(config_dir, "trade_history_task_3917820f.json")

with open(batches_path, "w", encoding="utf-8") as f:
    json.dump(batches, f, ensure_ascii=False, indent=2)
print(f"\n배치 저장: {batches_path}")

with open(history_path, "w", encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)
print(f"히스토리 저장: {history_path}")
print("\n완료! 대시보드 '투자내역' 탭을 새로고침 하세요.")
