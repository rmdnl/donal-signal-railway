# 🤖 DONAL Signal Robot — 4H Trend, 1H Breakout

> _Bot ini sigma male grindset financial freedom tool._ 💀

Bot trading crypto **Python + CCXT + Binance Spot**, 24/7 VPS.

---

## ⚠️ 3 Mode: `off` / `testnet` / `live` 🔴

**JANGAN** commit `.env` ke Git.

---

## ✨ Strategy (Pine Script Aligned)

Persis `donal2_pine_fixed-2.pine`:

- **HTF 4H:** EMA20>EMA60 AND RSI>50
- **Entry 1H:** Close>EMA20 AND RSI>50 AND Close>HH20
- **Exit:** Close<EMA20 OR RSI<45
- **Volume:** >1.5x MA20 (Pine volMult=1.5)
- **ADX:** >20 | **Res Room:** >1 ATR

## 🎯 TP Dinamis (ATR + Struktur S/R)

1. ATR: TP=Entry+(ATR×2.5)
2. Struktur: TP=Resistance-(ATR×0.3)
3. Validasi: TP harus > Entry
4. Locked at entry, gak bergeser

## 🎯 Precision Entry

- Market (default) | Limit (`USE_LIMIT_ENTRY=true`)
- Limit: close+0.1%, timeout 120s

## 🛡️ Risk Management

- Risk 1%/trade | MaxPos 25% equity
- BE: profit≥1% → SL=Entry+0.15%
- Vol-Scaled SL/TP: 0.8x-1.5x
- Daily 3% / Weekly 6% loss limit
- Correlation guard | Slippage <0.2%

## 📡 Dashboard Pro

- Signal Radar: skor 0-100% auto-ranking 🔥/⚡
- Countdown timer (WIB)
- P&L unrealized/realized + %
- Plotly: candle+EMA+S/R+BUY/SELL markers

## 🔄 24/7 Nonstop (no session filter)

## 🧪 Testnet: OCO fallback polling SL/TP

---

## 📊 Pine vs Python: 12/12 Match ✅

| Logic | Match |
|---|---|
| HTF Trend | ✅ |
| Buy/Exit | ✅ |
| Volume 1.5x | ✅ |
| ADX>20 | ✅ |
| SL/TP Struct | ✅ |
| Fee 0.1% | ✅ |
| ProcOnClose | ✅ |
| Qty Cap | ✅ |
| Slippage | ✅ |

---

## Config: lihat `.env.example`

**WAGMI** 🤝
