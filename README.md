# 🤖 DONAL Signal Robot — 4H Trend, 1H Breakout

*"Bot ini bukan bot trading biasa. Ini sigma male grindset financial freedom tool. No cap, fr fr."* 💀

Bot trading crypto berbasis Python + CCXT + Binance Spot, dijagain 24/7 di VPS.
Dia mantau market biar lu bisa tidur. Karena kalau lu yang mantau, lu gak tidur. Besoknya trading pake emosi. Terus rungkad. Terus nyalahin bot.

Padahal bot udah bilang skip. 🗿

## ⚠️ Baca Dulu, Bestie

**BOT INI PUNYA 3 MODE:**

| Mode | Fungsi | Uang |
|------|--------|------|
| `off` (default) | Cuma teriak di Telegram | Gak pegang |
| `testnet` | Auto-trading uang monopoli | Virtual |
| `live` 🔴 | Auto-trading uang beneran | **RIL** |

> 🚨 **JANGAN PERNAH commit `.env` ke Git.** Isinya API key. Kecuali lu mau jadi konten "kena hack" di Twitter.

---

## ✨ Kenapa Bot Ini Goated?

### 🧠 Strategy: "4H Trend, 1H Breakout" (Pine Script Aligned)

**7 Filter Entry** (semua match Pine Script):

1. **HTF 4H Trend:** EMA20 > EMA60 AND RSI > 50 → cuma trade searah tren besar
2. **1H Price:** Close > EMA20
3. **1H RSI:** RSI > 50
4. **1H Breakout:** Close > Highest High 20 bar
5. **Volume:** Volume > 1.5x MA20 (match Pine `volMult=1.5`)
6. **ADX:** ADX > 20 → cuma trade kalau tren kuat
7. **Resistance Room:** Skip kalau mepet resistance (< 1 ATR)

**Exit Trigger:** Close < EMA20 OR RSI < 45 → trend exit otomatis di candle close

### 🎯 Take Profit Dinamis (ATR + Struktur Pasar)

Bukan TP fixed %! Bot hitung berdasarkan logic Pine Script:

- **ATR Based:** `TP = Entry + (ATR × 2.5)` → adaptif volatilitas
- **Struktur S/R:** Kalau ada Resistance di dekat situ, TP geser ke `Resistance - (ATR × 0.3)` → amankan cuan
- **Validation:** TP struktur cuma dipakai kalau `TP > Entry` → fallback ke ATR
- **Locked at Entry:** Nilai ATR & Pivot **dibekukan** saat order dikirim → gak bergeser

### 🎯 Precision Entry (Match Pine `process_orders_on_close`)

**Market Order Only** — prioritas kepastian eksekusi di atas presisi harga. Market order langsung fill di candle close, gak ada konsep timeout/cancel. Slippage dilaporkan tapi gak membatalkan exit (exit = risk management, harus jalan).

### 🛡️ 5 Lapis Fail-Closed Protection

| Layer | Trigger | Perilaku |
|-------|---------|----------|
| **1. Withdrawal Check** | API key LIVE punya izin withdrawal | ❌ STOP + notif |
| **2. State Corrupt** | `state_signals.json` rusak di LIVE | ❌ STOP + backup + notif |
| **3. State Persistence** | `save_state()` gagal (disk penuh) | ❌ STOP via `StatePersistenceError` |
| **4. Exchange Verify** | Open order asing > $10 di LIVE | ❌ STOP + notif |
| **5. Idempotent Intents** | Timeout setelah order dikirim | ✅ Reconcile via clientOrderId, gak duplicate |

**Filosofi:** `UNKNOWN ≠ NOT_FOUND`. Network error ≠ izin buat submit order kedua.

### 🧮 Honest Accounting

- **Performance Baseline:** ROI dihitung dari *starting equity* (dicatat sekali di startup), bukan current balance yang fluktuatif
- **Fee Deduction:** Fee dihitung dari actual fill kedua leg (entry + exit), bukan perkiraan
- **Partial Fill:** Gross executedQty pre-fee dipakai deteksi partial, bukan saldo post-fee

### 📡 Dashboard Pro-Grade (Streamlit + Plotly)

Akses via `http://your-vps-ip:8501`:

- **Signal Strength Radar:** Scan 7/7 filter Pine pakai **closed candle 1H** (bukan forming). Threshold baca dari `.env`. Single source of truth dengan bot.
- **4H Fallback Match Bot:** Kalau 4H fetch gagal, radar set False (sama seperti bot yang skip).
- **Next Signal Countdown:** Timer real-time candle 1H berikutnya (WIB)
- **Unrealized/Realized P&L:** Mark-to-market + ROI dari baseline
- **Plotly Chart:** Candlestick + EMA20/60 + Support/Resistance + BUY/SELL marker + Background bull trend
- **Risk Snapshot:** Daily/Weekly loss limit, sizing 20% equity
- **Weekly Loss Limit:** Circuit breaker mingguan (6% default)

### 🧪 Testnet-Ready & Anti-Fragile

- **Native OCO Fallback:** Testnet gak support OCO → polling SL/TP tiap 30 detik
- **Fee Deduction Fix:** `filled_qty` di-adjust setelah fee dipotong → qty OCO match saldo real
- **Anti-Zombie Intents:** Cleanup order intent nyangkut setelah restart
- **Partial Fill Handling:** State qty synced immediately setelah partial fill
- **Self-Healing Exit:** Clamp qty SELL ke free balance + dust handler

### 🔄 24/7 Nonstop Trading

Session filter dibuang total. Bot scan market 24 jam nonstop — persis Pine Script yang gak pake filter jam.

---

## 📊 Pine Script vs Python — Cross-Reference

| Logic | Pine Script (`donal2_pine_fixed-2.pine`) | Python Bot | Match |
|-------|------------------------------------------|------------|-------|
| HTF Trend | `ema20[1] > ema60[1] AND rsi > 50` | `ema20 > ema60 AND rsi14 > 50` (closed) | ✅ |
| Buy Trigger | `close > ema20 AND rsi > 50 AND close > hh20` | Identical | ✅ |
| Exit Trigger | `close < ema20 OR rsi < 45` | Identical | ✅ |
| Volume Filter | `volume > volMA * 1.5` | `VOLUME_MULT=1.5` (env) | ✅ |
| ADX Filter | `ta.dmi(14,14) → ADX > 20` | Custom `adx()` Wilder's RMA | ✅ |
| SL/TP Structure | Pivot-based + buffer ATR | `compute_sl_tp()` + `SR_BUFFER_ATR=0.3` | ✅ |
| Commission | `0.1%` per side | `TAKER_FEE_PCT=0.1` | ✅ |
| EMA Smoothing | `ta.ema = α=2/(n+1)` | `ewm(span=n) = α=2/(n+1)` | ✅ |
| RMA Smoothing | Wilder's RMA `α=1/n` | `ewm(alpha=1/n)` | ✅ |
| Process Orders | `process_orders_on_close=true` | Market order di candle close | ✅ |
| Default Qty | `percent_of_equity=20` | `PCT_OF_EQUITY=20.0` (env) | ✅ |
| Slippage | `slippage=2` ticks | Reported, not blocking exit | ✅ |

**12/12 core logic points verified.** Bot adalah eksekusi live faithful dari backtest TradingView.

---

## 🚀 Cara Install di VPS Ubuntu

```bash
git clone https://github.com/rmdnl/donal-signal-railway.git
cd donal-signal-railway
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env
python3 signal_bot.py
```

Kalau muncul `🤖 DONAL Signal Robot started`, berarti bot hidup. W. 🎉

---

## 🔐 Setup `.env`

### Mode Signal Only (Default, Aman)

```env
SYMBOLS=BTC/USDT,ETH/USDT,BNB/USDT,SOL/USDT
TIMEFRAME=1h
HTF_TIMEFRAME=4h
TRADING_MODE=off
PCT_OF_EQUITY=20.0
DAILY_LOSS_LIMIT_PCT=3.0
WEEKLY_LOSS_LIMIT_PCT=6.0
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=token_dari_botfather
TELEGRAM_CHAT_ID=chat_id_lo
```

### Tambahan Buat Testnet

```env
TRADING_MODE=testnet
BINANCE_TESTNET_API_KEY=key_testnet_lo
BINANCE_TESTNET_API_SECRET=secret_testnet_lo
USE_NATIVE_OCO_SLTP=true
TAKER_FEE_PCT=0.1
```

### Tambahan Buat Live 🔴

```env
TRADING_MODE=live
BINANCE_LIVE_API_KEY=key_live_lo
BINANCE_LIVE_API_SECRET=secret_live_lo
```

> ⚠️ **LIVE API Key TIDAK BOLEH punya izin Withdrawal.** Bot akan stop otomatis kalau detect izin ini aktif.

---

## ⚙️ Variable `.env` Lengkap

| Variable | Default | Fungsi |
|----------|---------|--------|
| `SYMBOLS` | `BTC/USDT` | Pair pantauan (comma-separated) |
| `TIMEFRAME` | `1h` | Timeframe entry |
| `HTF_TIMEFRAME` | `4h` | Timeframe trend filter |
| `TRADING_MODE` | `off` | `off` / `testnet` / `live` |
| `SL_MULT` / `TP_MULT` | `1.5` / `2.5` | Pengali ATR untuk SL/TP |
| `RSI_ENTRY` / `RSI_EXIT` | `50` / `45` | Batas RSI entry/exit |
| `VOLUME_MULT` | `1.5` | Min volume ratio vs MA (match Pine) |
| `VOLUME_MA_LENGTH` | `20` | Periode MA volume |
| `USE_ADX_FILTER` | `true` | Skip kalau ADX rendah |
| `ADX_LENGTH` | `14` | Periode ADX |
| `ADX_THRESHOLD` | `20` | Minimum ADX untuk entry |
| `USE_RES_FILTER` | `true` | Skip kalau mepet resistance |
| `MIN_ROOM_ATR` | `1.0` | Min jarak ke resistance (x ATR) |
| `PCT_OF_EQUITY` | `20.0` | % equity per posisi (match Pine) |
| `TAKER_FEE_PCT` | `0.1` | Fee per sisi (%) |
| `DAILY_LOSS_LIMIT_PCT` | `3.0` | Circuit breaker harian |
| `WEEKLY_LOSS_LIMIT_PCT` | `6.0` | Circuit breaker mingguan |
| `USE_NATIVE_OCO_SLTP` | `true` | OCO native (fallback polling di Testnet) |
| `MAX_ENTRY_DELAY_MINUTES` | `15` | Skip sinyal basi setelah restart |

---

## 🧠 Kenapa Bot Skip Entry?

- ❌ Tren 4H mendung (EMA20 < EMA60 atau RSI < 50)
- ❌ Breakout belum valid (Close < HH20)
- ❌ Mepet resistance (jarak < 1 ATR)
- ❌ Volume tipis (< 1.5x MA)
- ❌ ADX lemes (< 20)
- ❌ Sinyal basi (> 15 menit sejak candle close)
- ❌ Saldo 0 / sizing gak valid
- ❌ Limit rugi kena (daily/weekly circuit breaker)
- ❌ Posisi udah terbuka (1 posisi per symbol)

Kalau bot skip, **jangan baper**. Dia lagi ngejaga dompet lu. 🗿

---

## 🖥️ Jalanin di Background (Sigma Mode)

```bash
sudo systemctl enable --now donal-signal.service
sudo systemctl enable --now donal-dashboard.service
```

---

## 📜 Disclaimer

Bot ini **bukan financial advice.**

- Crypto volatil. Bisa naik, bisa turun, bisa bikin lu jadi philosopher jam 2 pagi.
- Semua keputusan di tangan lu. Bot cuma alat. Bukan dukun. Bukan jaminan cuan.
- **Mode Live = risiko tinggi.** Proteksi modal dulu. Profit belakangan.

---

## 🫡 Credits

Dibuat oleh DONAL buat trader yang pengen disiplin, gak FOMO, dan gak mau jadi exit liquidity whale.

Kasih ⭐ kalau membantu. Pakai bijak. Touch grass sesekali. 🌱

## 📄 License

MIT. Bebas dipakai & dimodifikasi.

Tapi jangan dijual ulang jadi "robot premium VIP". Itu cringe. 💀

---

## 🗣️ Testimoni Fiktif (Tapi Relate)

> ⭐⭐⭐⭐⭐
> *"Dulu gw nyangkut di pucuk 3 bulan. Sekarang bot yang nentuin SL, jadi gw cuma nyangkut di perasaan."*
> — Bang Rungkad, 27, mantan holder pucuk 🗿

> ⭐⭐⭐⭐⭐
> *"Bot-nya bilang skip. Gw maksa entry manual. Gw yang rugi. Ternyata yang perlu di-upgrade bukan bot-nya, tapi gw."*
> — Kak Delulu, 24, korban FOMO berulang 😭

> ⭐⭐⭐⭐⭐
> *"Testnet 2 minggu profit. Pindah live rugi. Ternyata masalahnya di mental, bukan di bot."*
> — Mas Menyala, 30, aura -1000 🔥

> ⭐⭐⭐⭐⭐
> *"Gw clone repo ini, temen-temen gw juga clone. Kita semua profit. Bot-nya goated af."*
> — DONAL, trader ganteng yang udah WAGMI 💋

> ⭐⭐⭐
> *"Kurang satu bintang soalnya bot-nya gak bisa diajak healing."*
> — Bestie, umur rahasia 💅

---

## ❓ FAQ

**Q: Bot ini bisa bikin kaya?**
A: Dia bikin disiplin. Kaya itu efek samping. Yang pasti lu gak FOMO sendirian.

**Q: Bot ini gak bakal rugi?**
A: Bakal. Dia bot, bukan dukun. Kalau ada yang janji "pasti cuan", tutup repo ini dan lapor polisi.

**Q: Kok gak ada sinyal-sinyal?**
A: Market lagi jelek dan bot pemilih. Lu juga harusnya pemilih. Cek Signal Radar di dashboard — kalau skor semua <60%, ya emang belum waktunya.

**Q: Boleh pakai uang pinjol?**
A: 🗿 **Tidak. Jangan.** Ini satu-satunya bagian yang gak bercanda.

**Q: Bot-nya bisa jadi pacar?**
A: Dia konsisten, fast response, gak ghosting. Tapi gak bisa diajak makan seblak. Jadi tidak.

**Q: Gw clone repo ini, boleh pake API key yang sama bareng temen?**
A: JANGAN. Satu orang salah klik, OCO kalian tabrakan. Bikin key masing-masing.

**Q: Kenapa session filter dibuang?**
A: Pine Script asli gak pake filter jam. Market crypto 24/7. Bot scan nonstop.

---

## 🧠 Quotes of the Repo

> "Entry tanpa plan = sedekah ke whale."
>
> "SL itu asuransi, bukan penghinaan."
>
> "Market gak peduli lu butuh uang buat self reward."
>
> "Kalau bot bilang skip, ya skip. Lu bukan main character di market."
>
> "Rungkad itu canon event. Rungkad berulang itu pilihan."
>
> "Discipline > Emotion. Protect Capital First."
>
> "In crypto we trust, in DONAL we believe." 🚀

**WAGMI 🤝**

Dibuat dengan 💻 dari VPS, dijaga sama AI yang gak mau lu rungkad.
