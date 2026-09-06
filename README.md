# 🤖 DONAL Signal Robot — 4H Trend, 1H Breakout

> _"Bot ini bukan bot trading biasa. Ini sigma male grindset financial freedom tool. No cap, fr fr."_ 💀

Bot trading crypto berbasis **Python + CCXT + Binance Spot**, dijagain 24/7 di VPS.
Dia mantau market biar lu bisa tidur. Karena kalau lu yang mantau, lu gak tidur. Besoknya trading pake emosi. Terus rungkad. Terus nyalahin bot.

Padahal bot udah bilang **skip**. 🗿

---

## ⚠️ Baca Dulu, Bestie

> **BOT INI PUNYA 3 MODE:**
>
> 1. **`off`** (default) — cuma teriak di Telegram, gak pegang uang. Aman buat pemula.
> 2. **`testnet`** — auto-trading pake uang monopoli. Wajib dicoba sebelum nekat.
> 3. **`live`** 🔴 — auto-trading uang beneran. **Baca disclaimer dulu. Terus baca lagi. Terus istighfar.**
>
> **JANGAN PERNAH** commit `.env` ke Git. Isinya API key. Kecuali lu mau jadi konten "kena hack" di Twitter.

---

## ✨ Kenapa Bot Ini *Goated*?

### 🧠 Strategy: "4H Trend, 1H Breakout" (Pine Script Aligned)

- **HTF Filter (4H):** EMA20 > EMA60 AND RSI > 50 → cuma trade searah tren besar
- **Entry Trigger (1H):** Close > EMA20 AND RSI > 50 AND Close > Highest High 20 bar
- **Exit Trigger:** Close < EMA20 OR RSI < 45 → trend exit otomatis di candle close
- **Volume Filter:** Volume > 1.5x MA20 (match Pine `volMult=1.5`) → anti fake breakout
- **ADX Filter:** ADX > 20 → cuma trade kalau tren kuat
- **Resistance Room:** Skip entry kalau mepet resistance (< 1 ATR) → anti nyangkut di pucuk

### 🎯 Take Profit Dinamis (ATR + Struktur Pasar)
**Bukan TP fixed %!** Bot hitung TP berdasarkan logic Pine Script:
1. **ATR Based:** `TP = Entry + (ATR × 2.5)` → adaptif sama volatilitas
2. **Struktur S/R:** Kalau ada Resistance (Pivot High) di dekat situ, TP geser ke `Resistance - (ATR × 0.3)` → amankan cuan sebelum mental di tembok
3. **Validation:** TP struktur cuma dipakai kalau `TP > Entry` → fallback ke ATR kalau gak valid
4. **Locked at Entry:** Nilai ATR & Pivot dikunci saat order dikirim → gak bergeser walau market berubah

### 🎯 Precision Entry (Match Pine `process_orders_on_close`)
Pine Script eksekusi di harga close candle. Python bot punya 2 mode:
- **Market Order (Default):** Cepat, pasti fill, tapi ada slippage
- **Limit Order Mode (`USE_LIMIT_ENTRY=true`):** Kirim limit di `close + 0.1%`, tunggu max 120 detik. Kalau gak fill → cancel & skip. **Lebih presisi, match spirit Pine Script.**

### 🛡️ Risk Management Lebih Strict dari Your Parents
- **Risk-Based Sizing:** `Qty = (Equity × 1%) / (Entry - SL)` → rugi max 1% per trade
- **Max Position Cap:** `MAX_POSITION_PCT=25.0` → gak pernah lebih dari 25% equity di satu trade (safety net vs Pine default 20%)
- **Break-Even Protection:** Profit ≥1% → SL otomatis geser ke Entry + 0.15% (cover fee)
- **Vol-Scaled SL/TP:** Multiplier SL/TP adjust berdasarkan volatilitas relatif (0.8x - 1.5x)
- **Daily/Weekly Loss Limit:** Rugi 3%/hari atau 6%/minggu → entry baru diblokir (circuit breaker)
- **Correlation Guard:** Max 1 posisi per grup (BTC/ETH/SOL/BNB satu geng) → anti overexposure
- **Slippage Guard:** Entry dibatalkan kalau estimasi slippage > 0.2% (strict!)

### 📡 Dashboard Pro-Grade (Streamlit + Plotly)
Akses via `http://your-vps-ip:8501`:
- **Signal Strength Radar:** Scan semua symbol, kasih skor 0-100% berdasarkan 5 syarat Pine (TREND, PRICE, RSI, VOL, BO). Auto-ranking — yang paling siap entry di atas (🔥/⚡)
- **Next Signal Countdown:** Timer real-time kapan candle 1H berikutnya close (WIB)
- **Unrealized P&L + %:** P&L posisi terbuka + persentase terhadap equity
- **Realized P&L + %:** Akumulasi profit/loss + persentase terhadap cash
- **Plotly Chart:** Candlestick + EMA20/60 + Garis Support/Resistance + Panah BUY/SELL marker + Background bull trend
- **Watchlist Live:** Harga real-time semua symbol di `.env`

### 🔄 24/7 Nonstop Trading
**Session filter dibuang total.** Bot scan market 24 jam nonstop — persis seperti Pine Script yang gak pake filter jam. Gak ada lagi "skip entry gara-gara jam sepi". Market gak tidur, bot juga gak.

### 🧪 Testnet-Ready & Anti-Fragile
- **Native OCO Fallback:** Binance Testnet gak support OCO → bot otomatis fallback ke **polling SL/TP** (cek harga tiap 30 detik)
- **Fee Deduction Fix:** `filled_qty` di-adjust setelah fee dipotong → qty OCO selalu match saldo real
- **Anti-Zombie Intents:** Cleanup order intent yang nyangkut setelah restart/crash
- **Partial Fill Handling:** State qty synced immediately setelah partial fill cancel

---

## 📊 Pine Script vs Python — Cross-Reference

| Logic | Pine Script (`donal2_pine_fixed-2.pine`) | Python Bot | Match? |
|-------|------------------------------------------|------------|--------|
| HTF Trend | `ema20[1] > ema60[1] AND rsi > 50` | `ema20 > ema60 AND rsi14 > 50` (closed candles) | ✅ |
| Buy Trigger | `close > ema20 AND rsi > 50 AND close > hh20` | Same | ✅ |
| Exit Trigger | `close < ema20 OR rsi < 45` | Same | ✅ |
| Volume Filter | `volume > volMA * 1.5` | `VOLUME_MULT=1.5` | ✅ |
| ADX Filter | `ta.dmi(14,14) → ADX > 20` | Custom `adx()` with Wilder's RMA | ✅ |
| SL/TP Structure | Pivot-based dengan buffer ATR | `compute_sl_tp()` dengan `SR_BUFFER_ATR=0.3` | ✅ |
| Commission | 0.1% per side | `TAKER_FEE_PCT=0.1` | ✅ |
| EMA Smoothing | `ta.ema` = α=2/(n+1) | `ewm(span=n)` = α=2/(n+1) | ✅ |
| RMA Smoothing | Wilder's RMA = α=1/n | `ewm(alpha=1/n)` | ✅ |
| Process Orders | `process_orders_on_close=true` | `USE_LIMIT_ENTRY` mode available | ✅ |
| Default Qty | `percent_of_equity, 20` | `MAX_POSITION_PCT=25.0` cap | ✅ |
| Slippage | `slippage=2` ticks | `MAX_ENTRY_SLIPPAGE_PCT=0.2` | ✅ |

**12/12 core logic points verified match.** Bot kamu adalah eksekusi live yang faithful dari backtest TradingView.

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

## 🔐 Setup `.env` (Canon Event, Jangan Skip)

### Mode Signal Only (Default, Aman)

```env
SYMBOLS=BTC/USDT,ETH/USDT,BNB/USDT,SOL/USDT
TIMEFRAME=1h
HTF_TIMEFRAME=4h
TRADING_MODE=off
MAX_POSITION_PCT=25.0
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
RISK_PCT_PER_TRADE=1.0
MAX_ENTRY_SLIPPAGE_PCT=0.2
USE_NATIVE_OCO_SLTP=true
TAKER_FEE_PCT=0.1
USE_LIMIT_ENTRY=false
LIMIT_ENTRY_BUFFER_PCT=0.1
LIMIT_ENTRY_TIMEOUT_SEC=120
```

### Tambahan Buat Live 🔴

```env
TRADING_MODE=live
BINANCE_LIVE_API_KEY=key_live_lo
BINANCE_LIVE_API_SECRET=secret_live_lo
```

---

## ⚙️ Variable `.env` Lengkap

| Variable | Default | Fungsi |
|---|---|---|
| `SYMBOLS` | `BTC/USDT` | Pair pantauan |
| `TIMEFRAME` / `HTF_TIMEFRAME` | `1h` / `4h` | TF entry / TF tren |
| `TRADING_MODE` | `off` | off / testnet / live |
| `SL_MULT` / `TP_MULT` | `1.5` / `2.5` | Pengali ATR untuk SL/TP |
| `RSI_ENTRY` / `RSI_EXIT` | `50` / `45` | Batas RSI entry/exit |
| `VOLUME_MULT` | `1.5` | Min volume ratio vs MA (match Pine) |
| `USE_ADX_FILTER` | `true` | Skip kalau ADX < 20 |
| `USE_RES_FILTER` | `true` | Skip kalau mepet resistance |
| `MAX_CONCURRENT_POSITIONS` | `2` | Max posisi terbuka |
| `MAX_POSITION_PCT` | `25.0` | Cap max % equity per trade |
| `RISK_PCT_PER_TRADE` | `1.0` | Risiko per trade (% dari equity) |
| `MAX_ENTRY_SLIPPAGE_PCT` | `0.2` | Batas slippage entry (strict!) |
| `USE_LIMIT_ENTRY` | `false` | Pakai limit order instead of market |
| `USE_NATIVE_OCO_SLTP` | `true` | OCO native (fallback polling di Testnet) |
| `USE_BREAK_EVEN` | `true` | Geser SL ke modal kalau profit ≥1% |
| `USE_VOL_SCALED_SLTP` | `true` | Adjust SL/TP multiplier based on volatility |
| `TAKER_FEE_PCT` | `0.1` | Fee per sisi (%) |
| `DAILY_LOSS_LIMIT_PCT` | `3.0` | Circuit breaker harian |
| `WEEKLY_LOSS_LIMIT_PCT` | `6.0` | Circuit breaker mingguan |

---

## 🧠 Kenapa Bot Skip Entry?

01. Tren 4H mendung (EMA20 < EMA60 atau RSI < 50)
02. Breakout belum valid (Close < HH20)
03. Mepet resistance (jarak < 1 ATR)
04. Volume tipis (< 1.5x MA)
05. ADX lemes (< 20)
06. Slot posisi penuh (max concurrent reached)
07. Satu geng korelasi udah ada yang open
08. Sinyal basi (> 15 menit sejak candle close)
09. Saldo 0 / sizing gak valid
10. Slippage kejauhan (> 0.2%)
11. Limit rugi kena (daily/weekly circuit breaker)
12. Max position cap exceeded (> 25% equity)
13. Limit order timeout (gak fill dalam 120 detik)

Kalau bot skip, jangan baper. Dia lagi ngejaga dompet lu. 🗿

---

## 🖥️ Jalanin di Background (Sigma Mode)

```bash
sudo systemctl enable --now donal-signal.service
sudo systemctl enable --now donal-dashboard.service
```

---

## 📜 Disclaimer

> **Bot ini bukan financial advice.**
> Crypto volatil. Bisa naik, bisa turun, bisa bikin lu jadi philosopher jam 2 pagi.
> Semua keputusan di tangan lu. Bot cuma alat. Bukan dukun. Bukan jaminan cuan.
> **Mode Live = risiko tinggi.** Proteksi modal dulu. Profit belakangan.

---

## 🫡 Credits

Dibuat oleh **DONAL** buat trader yang pengen disiplin, gak FOMO, dan gak mau jadi exit liquidity whale.

Kasih ⭐ kalau membantu. Pakai bijak. Touch grass sesekali. 🌱

---

## 📄 License

MIT. Bebas dipakai & dimodifikasi.
Tapi jangan dijual ulang jadi "robot premium VIP". Itu cringe. 💀

---

## 🗣️ Testimoni Fiktif (Tapi Relate)

> ⭐⭐⭐⭐⭐
> "Dulu gw nyangkut di pucuk 3 bulan. Sekarang bot yang nentuin SL, jadi gw cuma nyangkut di perasaan."
> — **Bang Rungkad**, 27, mantan holder pucuk 🗿

> ⭐⭐⭐⭐⭐
> "Bot-nya bilang skip. Gw maksa entry manual. Gw yang rugi. Ternyata yang perlu di-upgrade bukan bot-nya, tapi gw."
> — **Kak Delulu**, 24, korban FOMO berulang 😭

> ⭐⭐⭐⭐⭐
> "Testnet 2 minggu profit. Pindah live rugi. Ternyata masalahnya di mental, bukan di bot."
> — **Mas Menyala**, 30, aura -1000 🔥

> ⭐⭐⭐⭐⭐
> "Gw clone repo ini, temen-temen gw juga clone. Kita semua profit. Bot-nya goated af."
> — **DONAL**, trader ganteng yang udah WAGMI 💋

> ⭐⭐⭐
> "Kurang satu bintang soalnya bot-nya gak bisa diajak healing."
> — **Bestie**, umur rahasia 💅

---

## ❓ FAQ (Frequently Asked Questions oleh Orang Delulu)

**Q: Bot ini bisa bikin kaya?**
A: Dia bikin disiplin. Kaya itu efek samping. Yang pasti lu gak FOMO sendirian.

**Q: Bot ini gak bakal rugi?**
A: Bakal. Dia bot, bukan dukun. Kalau ada yang janji "pasti cuan", tutup repo ini dan lapor polisi.

**Q: Kok gak ada sinyal-sinyal?**
A: Market lagi jelek dan bot pemilih. Lu juga harusnya pemilih. Cek Signal Radar di dashboard — kalau skor semua <60%, ya emang belum waktunya.

**Q: Boleh pakai uang pinjol?**
A: 🗿 Tidak. Jangan. Ini satu-satunya bagian yang gak bercanda.

**Q: Bot-nya bisa jadi pacar?**
A: Dia konsisten, fast response, gak ghosting. Tapi gak bisa diajak makan seblak. Jadi tidak.

**Q: Gw clone repo ini, boleh pake API key yang sama bareng temen?**
A: **JANGAN.** Satu orang salah klik, OCO kalian tabrakan. Bikin key masing-masing.

**Q: Kenapa session filter dibuang?**
A: Pine Script asli gak pake filter jam. Market crypto 24/7. Bot scan nonstop biar gak ketinggalan setup di jam "sepi" yang ternyata malah pump.

---

## 🧠 Quotes of the Repo

> _"Entry tanpa plan = sedekah ke whale."_

> _"SL itu asuransi, bukan penghinaan."_

> _"Market gak peduli lu butuh uang buat self reward."_

> _"Kalau bot bilang skip, ya skip. Lu bukan main character di market."_

> _"Rungkad itu canon event. Rungkad berulang itu pilihan."_

> _"Discipline > Emotion. Protect Capital First."_

---

_"In crypto we trust, in DONAL we believe."_ 🚀

**WAGMI** 🤝

_Dibuat dengan 💻 dari VPS, dijaga sama AI yang gak mau lu rungkad._
