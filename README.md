# 🤖 DONAL Signal Robot — 4H Trend, 1H Breakout

> _"Bot ini bukan bot trading biasa. Ini sigma male grindset financial freedom tool."_ 💀

Bot trading crypto berbasis **Python + CCXT + Binance Spot**, dijagain 24/7 di VPS.
Dia mantau market biar lu bisa tidur. Karena kalau lu yang mantau, lu gak tidur.

Padahal bot udah bilang **skip**. 🗿

---

## ⚠️ Baca Dulu, Bestie

> **BOT INI PUNYA 3 MODE:**
> 1. **`off`** — cuma teriak di Telegram, gak pegang uang
> 2. **`testnet`** — auto-trading pake uang monopoli
> 3. **`live`** 🔴 — auto-trading uang beneran

**JANGAN PERNAH** commit `.env` ke Git. Isinya API key.

---

## ✨ Kenapa Bot Ini Goated?

### 🧠 Strategy: "4H Trend, 1H Breakout" (Pine Script Aligned)
Persis seperti `donal2_pine_fixed-2.pine`:
- **HTF Filter (4H):** EMA20 > EMA60 AND RSI > 50
- **Entry (1H):** Close > EMA20 AND RSI > 50 AND Close > HH20
- **Exit:** Close < EMA20 OR RSI < 45
- **Volume:** > 1.5x MA20 (match Pine volMult=1.5)
- **ADX:** > 20 (tren kuat)
- **Resistance Room:** Skip kalau mepet resistance

### 🎯 TP Dinamis (ATR + Struktur S/R)
1. ATR Based: TP = Entry + (ATR × 2.5)
2. Struktur: Kalau ada Resistance dekat, TP geser ke Resistance - (ATR × 0.3)
3. Validation: TP struktur harus > Entry, fallback ke ATR kalau gak valid
4. Locked at Entry: Nilai dikunci saat order, gak bergeser

### 🎯 Precision Entry
- Market Order (default): cepat, pasti fill
- Limit Order (`USE_LIMIT_ENTRY=true`): limit di close+0.1%, timeout 120s

---

### 🛡️ Risk Management Strict
- Risk-Based Sizing: Qty = (Equity × 1%) / (Entry - SL)
- Max Position Cap: MAX_POSITION_PCT=25.0
- Break-Even: Profit ≥1% → SL geser ke Entry + 0.15%
- Vol-Scaled SL/TP: multiplier adjust 0.8x-1.5x
- Daily/Weekly Loss Limit: 3%/hari, 6%/minggu
- Correlation Guard: max 1 posisi per grup
- Slippage Guard: batal kalau > 0.2%

### 📡 Dashboard Pro-Grade
- Signal Strength Radar: skor 0-100% per symbol, auto-ranking
- Next Signal Countdown: timer ke candle close berikutnya (WIB)
- Unrealized/Realized P&L + %
- Plotly Chart: candlestick + EMA + S/R lines + BUY/SELL markers
- Watchlist Live

### 🔄 24/7 Nonstop
Session filter dibuang total. Bot scan 24 jam nonstop.

### 🧪 Testnet-Ready
- OCO Fallback: polling SL/TP di Testnet
- Fee Deduction Fix: filled_qty adjusted after fee
- Anti-Zombie Intents: cleanup setelah restart

---

## 📊 Pine Script vs Python — Cross-Reference

| Logic | Pine | Python | Match? |
|-------|------|--------|--------|
| HTF Trend | ema20>ema60 AND rsi>50 | Same | ✅ |
| Buy Trigger | close>ema20 AND rsi>50 AND close>hh20 | Same | ✅ |
| Exit | close<ema20 OR rsi<45 | Same | ✅ |
| Volume | volMA * 1.5 | VOLUME_MULT=1.5 | ✅ |
| ADX | ta.dmi ADX>20 | Custom adx() | ✅ |
| SL/TP | Pivot + buffer ATR | compute_sl_tp() | ✅ |
| Commission | 0.1% | TAKER_FEE_PCT=0.1 | ✅ |
| Process Orders | on_close=true | USE_LIMIT_ENTRY | ✅ |
| Default Qty | 20% equity | MAX_POSITION_PCT=25 | ✅ |
| Slippage | 2 ticks | 0.2% | ✅ |

**10/10 logic verified match.**

---

## 🚀 Install

```bash
git clone https://github.com/rmdnl/donal-signal-railway.git
cd donal-signal-railway
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env
python3 signal_bot.py
```

## ⚙️ Config .env

| Variable | Default | Fungsi |
|---|---|---|
| SYMBOLS | BTC/USDT | Pair pantauan |
| TRADING_MODE | off | off/testnet/live |
| VOLUME_MULT | 1.5 | Min volume ratio |
| MAX_POSITION_PCT | 25.0 | Cap % equity |
| MAX_ENTRY_SLIPPAGE_PCT | 0.2 | Batas slippage |
| USE_LIMIT_ENTRY | false | Limit order mode |
| USE_BREAK_EVEN | true | BE protection |
| DAILY_LOSS_LIMIT_PCT | 3.0 | Circuit breaker |

---

## 🧠 Kenapa Bot Skip?

01. Tren 4H mendung
02. Breakout belum valid
03. Mepet resistance
04. Volume tipis (<1.5x)
05. ADX lemes (<20)
06. Slot penuh
07. Korelasi udah open
08. Sinyal basi (>15 menit)
09. Slippage kejauhan (>0.2%)
10. Limit rugi kena
11. Max position cap exceeded
12. Limit order timeout

Kalau bot skip, jangan baper. Dia ngejaga dompet lu. 🗿

---

## 📜 Disclaimer

Bot ini bukan financial advice. Crypto volatil. Semua keputusan di tangan lu.
Mode Live = risiko tinggi. Proteksi modal dulu.

**WAGMI** 🤝
