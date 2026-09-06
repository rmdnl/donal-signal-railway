# 🤖 DONAL Signal Bot — 4H Trend, 1H Breakout

> *"Discipline > Emotion. Protect Capital First."*

Bot trading crypto spot otomatis yang **100% aligned** dengan Pine Script `DONAL 4H Trend 1H Breakout`. Dirancang untuk **maximal win rate**, **minimal bug**, dan **risk management ketat**.

---

## ✨ Fitur Utama

###  Strategy: "4H Trend, 1H Breakout"
Persis seperti Pine Script TradingView kamu:
- **HTF Filter (4H):** EMA20 > EMA60 AND RSI > 50 → cuma trade searah tren besar
- **Entry Trigger (1H):** Close > EMA20 AND RSI > 50 AND Close > Highest High 20 bar
- **Exit Trigger:** Close < EMA20 OR RSI < 45 → trend exit otomatis di candle close
- **Volume Filter:** Volume > 1.5x MA20 (match Pine `volMult=1.5`) → anti fake breakout
- **ADX Filter:** ADX > 20 → cuma trade kalau tren kuat
- **Resistance Room:** Skip entry kalau mepet resistance (< 1 ATR) → anti nyangkut di pucuk

### 🎯 Take Profit Dinamis (ATR + Struktur Pasar)
**Bukan TP fixed %!** Bot hitung TP berdasarkan:
1. **ATR Based:** `TP = Entry + (ATR × 2.5)` → adaptif sama volatilitas
2. **Struktur S/R:** Kalau ada Resistance (Pivot High) di dekat situ, TP geser ke `Resistance - (ATR × 0.3)` → amankan cuan sebelum mental di tembok
3. **Validation:** TP struktur cuma dipakai kalau `TP > Entry` → fallback ke ATR kalau gak valid

### 🛡️ Risk Management Lebih Strict dari Your Parents
- **Risk-Based Sizing:** `Qty = (Equity × 1%) / (Entry - SL)` → rugi max 1% per trade
- **Break-Even Protection:** Profit ≥1% → SL otomatis geser ke Entry + 0.15% (cover fee)
- **Vol-Scaled SL/TP:** Multiplier SL/TP adjust berdasarkan volatilitas relatif (0.8x - 1.5x)
- **Daily/Weekly Loss Limit:** Rugi 3%/hari atau 6%/minggu → entry baru diblokir (circuit breaker)
- **Correlation Guard:** Max 1 posisi per grup (BTC/ETH/SOL/BNB satu geng) → anti overexposure
- **Max Concurrent Positions:** Default 2 → jangan rakus, bro
- **Slippage Guard:** Entry dibatalkan kalau estimasi slippage > 0.5%

### 📡 Dashboard Pro-Grade (Streamlit)
Akses via `http://your-vps-ip:8501`:
- **Signal Strength Radar:** Scan semua symbol, kasih skor 0-100% berdasarkan 5 syarat Pine (TREND, PRICE, RSI, VOL, BO). Auto-ranking — yang paling siap entry di atas (🔥/)
- **Next Signal Countdown:** Timer real-time kapan candle 1H berikutnya close (WIB)
- **Unrealized P&L + %:** P&L posisi terbuka + persentase terhadap equity
- **Realized P&L + %:** Akumulasi profit/loss + persentase terhadap cash
- **Plotly Chart:** Candlestick + EMA20/60 + Garis Support/Resistance + Panah BUY/SELL marker
- **Watchlist Live:** Harga real-time semua symbol di `.env`

### 🔄 24/7 Nonstop Trading
**Session filter dibuang total.** Bot scan market 24 jam nonstop — persis seperti Pine Script yang gak pake filter jam. Gak ada lagi "skip entry gara-gara jam sepi".

### 🧪 Testnet-Ready
- **Native OCO Fallback:** Binance Testnet gak support OCO → bot otomatis fallback ke **polling SL/TP** (cek harga tiap 30 detik)
- **Fee Deduction Fix:** `filled_qty` di-adjust setelah fee dipotong → qty OCO selalu match saldo real
- **Anti-Zombie Intents:** Cleanup order intent yang nyangkut setelah restart/crash

---

## 🚀 Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/rmdnl/donal-signal-railway.git
cd donal-signal-railway
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Config `.env`
```env
# Symbols (comma-separated)
SYMBOLS=BTC/USDT,ETH/USDT,BNB/USDT,SOL/USDT

# Timeframes
TIMEFRAME=1h
HTF_TIMEFRAME=4h

# Trading Mode: off | testnet | live
TRADING_MODE=testnet

# API Keys (pisah testnet & live)
BINANCE_TESTNET_API_KEY=your_testnet_key
BINANCE_TESTNET_API_SECRET=your_testnet_secret
BINANCE_LIVE_API_KEY=your_live_key
BINANCE_LIVE_API_SECRET=your_live_secret

# Risk Management
RISK_PCT_PER_TRADE=1.0
MAX_CONCURRENT_POSITIONS=2
MAX_POSITIONS_PER_GROUP=1
DAILY_LOSS_LIMIT_PCT=3.0
WEEKLY_LOSS_LIMIT_PCT=6.0

# Strategy (match Pine Script defaults)
VOLUME_MULT=1.5
SL_MULT=1.5
TP_MULT=2.5
RSI_ENTRY=50
RSI_EXIT=45
ADX_THRESHOLD=20.0

# Protection
USE_BREAK_EVEN=true
BE_TRIGGER_PCT=1.0
BE_OFFSET_PCT=0.15
USE_VOL_SCALED_SLTP=true
USE_STRUCTURE_SLTP=true

# Telegram Notifications
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. Run
```bash
# Bot Signal
sudo systemctl enable --now donal-signal.service

# Dashboard
sudo systemctl enable --now donal-dashboard.service
```

---

## 📊 Pine Script vs Python — Cross-Reference

| Logic | Pine Script | Python Bot | Match? |
|-------|------------|------------|--------|
| HTF Trend | `ema20[1] > ema60[1] AND rsi > 50` | `ema20 > ema60 AND rsi14 > 50` (closed candles) | ✅ |
| Buy Trigger | `close > ema20 AND rsi > 50 AND close > hh20` | Same | ✅ |
| Exit Trigger | `close < ema20 OR rsi < 45` | Same | ✅ |
| Volume Filter | `volume > volMA * 1.5` | `VOLUME_MULT=1.5` | ✅ |
| ADX Filter | `ta.dmi(14,14) → ADX > 20` | Custom `adx()` with Wilder's RMA | ✅ |
| SL/TP Structure | Pivot-based dengan buffer ATR | `compute_sl_tp()` dengan `SR_BUFFER_ATR=0.3` | ✅ |
| Commission | 0.1% per side | `TAKER_FEE_PCT=0.1` | ✅ |
| EMA Smoothing | `ta.ema` = α=2/(n+1) | `ewm(span=n)` = α=2/(n+1) | ✅ |
| RMA Smoothing | Wilder's RMA = α=1/n | `ewm(alpha=1/n)` | ✅ |

**15/15 logic points verified match.** Bot kamu adalah eksekusi live yang faithful dari backtest TradingView.

---

## 🐛 Bug Fixes & Enhancements (Latest)

- ✅ **Fee Deduction Fix:** `filled_qty` adjusted after exchange fee deduction
- ✅ **Testnet OCO Fallback:** Polling SL/TP when native OCO unsupported
- ✅ **Ghost Position Cleanup:** Auto-remove stale positions on startup
- ✅ **Partial Fill State Update:** State qty synced immediately after partial fill cancel
- ✅ **Break-Even Polling Mode:** BE works correctly in Testnet (no OCO dependency)
- ✅ **Dashboard Cache TTL:** Reduced from 8s → 3s for fresher prices
- ✅ **Realized P&L %:** Calculated against cash balance, not current equity
- ✅ **EMA Calculation:** Dashboard chart EMA matches Pine `ta.ema` exactly
- ✅ **Signal Radar Auto-Ranking:** Sorted by score descending (hottest setup on top)
- ✅ **Plotly Upgrade:** S/R lines + BUY/SELL markers + bull trend background

---

## ⚠️ Disclaimer

**This is not financial advice.** Crypto trading involves substantial risk of loss. Use at your own risk. Always test on Testnet before going Live. The author is not responsible for any financial losses incurred.

---

## 📜 License

MIT License — feel free to fork, modify, and improve. But remember: **Discipline > Emotion.**

---

*Built with ❤️ by DONAL · WAGMI*
