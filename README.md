# 🤖 DONAL Signal Robot

> _"Bot ini bukan bot trading biasa. Ini sigma male grindset financial freedom tool. No cap, fr fr."_ 💀🔥

Bot trading crypto berbasis **Python + CCXT + Binance Spot**, dijagain 24/7 di VPS.
Dia mantau market biar lu bisa tidur.
Karena kalau lu yang mantau, lu gak tidur. Besoknya trading pake emosi. Terus rungkad. Terus nyalahin bot.

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

### 🧢 Signal Only by Default
Bot cuma teriak, gak pegang uang lu. Dia tau diri. Very demure, very mindful.

### 🤖 Auto Order (Opt-In)
Kalau lu aktifin, bot bakal:
- Beli pas sinyal valid
- Pasang SL/TP langsung di exchange (native OCO)
- Reconcile order setelah restart/network failure
- Jual pas kena SL/TP/trend exit

Semua pake market order. Karena limit order itu kayak nunggu doi bales chat — kadang gak pernah. 💀

### 🛡️ Risk Management Lebih Ketat dari Ortu Lu

- Max posisi terbuka (jangan rakus, bro)
- Guard korelasi (BTC/ETH/SOL satu geng, gak dibeli bareng)
- Limit rugi harian & mingguan (circuit breaker)
- Filter sesi (skip jam market sepi)
- Guard slippage (batal masuk kalau harga kejauhan)
- Sizing berbasis risiko + validasi saldo

Kalau semua ini masih bikin lu rugi, berarti market lagi gak masuk akal.
Tapi setidaknya lu rugi **terencana**. 🗿

### 🚨 Anti Fakeout Detector
- **Resistance room**: mepet atap? Skip. Gak mau nyangkut di pucuk terus jadi konten ratapan.
- **Volume filter**: breakout tanpa volume itu kayak chat "pagi" dari doi — keliatannya ada, tapi kosong.
- **ADX filter**: cek kekuatan tren (ADX > 20). Market lemes? Skip.
- **ATR scaling**: SL/TP ngikutin volatilitas, gak asal tempel.

### 🛡️ Execution Safety (Anti-Duplicate Order)
- Client order ID deterministic
- Intent disimpan sebelum request exchange
- Timeout/network error direkonsiliasi SEBELUM retry
- OCO tidak pernah dibuat ulang secara blind
- Status proteksi UNKNOWN = blokir SELL sampai exchange jelas
- Restart VPS recovery intent/order

### 📱 Telegram Bestie
Notif cepet. Fast response. Gak ghosting.
Pokoknya semua yang gak bisa dilakuin doi lu. 😭

---

## 🧠 Strategy: "4H Trend, 1H Breakout"

### 1. Tren 4H — Cek Cuaca Dulu 🧠
- EMA 20 > EMA 60?
- RSI > 50?

Dua-duanya iya = cuaca cerah, boleh piknik.
Selain itu = mendung. Jangan maksa piknik. Nanti kehujanan. Terus nangis.

### 2. Entry 1H — Nunggu Konfirmasi 🎯
Bot nunggu:
- Close > EMA 20
- RSI > RSI_ENTRY
- Breakout high 20 bar
- Volume > rata-rata
- Jarak ke resistance masih lega

Semua iya? **Let him cook.** 👨‍🍳🔥
Ada yang enggak? **Skip.** Bot gak kenal kata "tanggung".

### 3. Exit — Gak Pake Perasaan 🚪
- **TP HIT**: cuan, ambil. Jangan serakah.
- **SL HIT**: rugi, terima. Besok masih ada market.
- **TREND EXIT**: tren rusak, keluar. Jangan jadi holder abadi.

---

## 🚀 Cara Install di VPS Ubuntu

~~~bash
# 1. Clone
git clone https://github.com/rmdnl/donal-signal-railway.git
cd donal-signal-railway

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Bikin .env (WAJIB)
cp .env.example .env
nano .env

# 4. Jalanin
python3 signal_bot.py
~~~

Kalau muncul `🤖 DONAL Signal Bot started`, berarti bot hidup. W. 🎉

---

## 🔐 Setup `.env` (Canon Event, Jangan Skip)

### Mode Signal Only (Default, Aman)

~~~
SYMBOLS=BTC/USDT,ETH/USDT,BNB/USDT,SOL/USDT
TIMEFRAME=1h
HTF_TIMEFRAME=4h

TRADING_MODE=off

MAX_CONCURRENT_POSITIONS=2
MAX_POSITIONS_PER_GROUP=1
DAILY_LOSS_LIMIT_PCT=3.0
WEEKLY_LOSS_LIMIT_PCT=6.0

SESSION_FILTER_ENABLED=true
SESSION_START_HOUR=8
SESSION_END_HOUR=22

TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=token_dari_botfather
TELEGRAM_CHAT_ID=chat_id_lo
~~~

### Tambahan Buat Testnet (Uang Monopoli)

~~~
TRADING_MODE=testnet
BINANCE_TESTNET_API_KEY=key_testnet_lo
BINANCE_TESTNET_API_SECRET=secret_testnet_lo

RISK_PCT_PER_TRADE=1.0
MAX_ENTRY_SLIPPAGE_PCT=0.5
USE_NATIVE_OCO_SLTP=true
TAKER_FEE_PCT=0.1
~~~

### Tambahan Buat Live (UANG BENERAN) 🔴

~~~
TRADING_MODE=live
# HANYA centang "Spot Trading". JANGAN centang withdrawal. SERIUS.
BINANCE_LIVE_API_KEY=key_live_lo
BINANCE_LIVE_API_SECRET=secret_live_lo
~~~

---

## 📱 Cara Dapet Token & ID

### Telegram
1. Chat `@BotFather` (yang verified)
2. `/newbot`, ikutin instruksi
3. Copy token → `TELEGRAM_BOT_TOKEN`
4. Chat `@userinfobot` buat dapet Chat ID

### Binance API
- **Testnet:** https://testnet.binance.vision → login GitHub → generate key
- **Live:** Binance → API Management → **CENTANG: Spot Trading ONLY** → **JANGAN CENTANG: Withdrawals**

Kalau lu centang withdrawal, bot ini berubah jadi mesin sedekah ke hacker. Jangan. 🗿

---

## 🖥️ Jalanin di Background (Sigma Mode)

Pake `systemd` biar auto-restart:

~~~bash
sudo nano /etc/systemd/system/donal-signal.service
~~~

~~~ini
[Unit]
Description=DONAL Signal Bot
After=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/donal-signal-railway
ExecStart=/home/ubuntu/donal-signal-railway/venv/bin/python /home/ubuntu/donal-signal-railway/signal_bot.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
~~~

~~~bash
sudo systemctl daemon-reload
sudo systemctl enable --now donal-signal.service
~~~

---

## 📊 Contoh Output Telegram

### BUY (Signal Only)
~~~
🟢 BUY SIGNAL BTC/USDT
Strategy: DONAL 4H Trend 1H Breakout
Status: SIGNAL ONLY
Entry ideal close 1H: 67420.50
Harga saat alert: 67425.10
SL: 66850.20
TP: 68500.00
ATR: 380.15
Volume: 1.85x MA
ADX: 28.5 (Trend Strength)
Breakeven (fee 0.20%): 67559.93
Catatan: Eksekusi manual, gunakan risiko kecil.
~~~

### SL HIT
~~~
🔴 SL HIT BTC/USDT
Entry: 67425.10
Exit: 66850.20
PnL Net: -8.75 USDT (-1.30%)
Status: Posisi ditutup. OCO di-cancel.
~~~

Kalau kena SL jangan marah. SL itu asuransi, bukan penghinaan. 😌

---

## ⚙️ Variable `.env` Lengkap

| Variable | Default | Fungsi |
|---|---|---|
| `SYMBOLS` | `BTC/USDT` | Pair pantauan |
| `TIMEFRAME` / `HTF_TIMEFRAME` | `1h` / `4h` | TF entry / TF tren |
| `TRADING_MODE` | `off` | off / testnet / live |
| `SL_MULT` / `TP_MULT` | `1.5` / `2.5` | Pengali ATR |
| `RSI_ENTRY` / `RSI_EXIT` | `50` / `45` | Batas RSI |
| `USE_ADX_FILTER` | `true` | Skip kalau ADX < 20 |
| `USE_RES_FILTER` | `true` | Skip kalau mepet resistance |
| `USE_VOLUME_FILTER` | `true` | Breakout wajib ada volume |
| `MAX_CONCURRENT_POSITIONS` | `2` | Max posisi terbuka |
| `RISK_PCT_PER_TRADE` | `1.0` | Risiko per trade |
| `MAX_ENTRY_SLIPPAGE_PCT` | `0.5` | Batas slippage |
| `USE_NATIVE_OCO_SLTP` | `true` | OCO native di exchange |
| `TAKER_FEE_PCT` | `0.1` | Fee per sisi |
| `DAILY_LOSS_LIMIT_PCT` | `3.0` | Circuit breaker harian |
| `WEEKLY_LOSS_LIMIT_PCT` | `6.0` | Circuit breaker mingguan |

---

## 🧠 Kenapa Bot Skip Entry?

01. Tren 4H mendung
02. Breakout belum valid
03. Mepet resistance
04. Volume tipis
05. Slot posisi penuh
06. Satu geng korelasi udah ada yang open
07. Sinyal basi
08. Di luar jam trading
09. Saldo 0 / sizing gak valid
10. Slippage kejauhan
11. Limit rugi kena

Kalau bot skip, jangan baper. Dia lagi ngejaga dompet lu. 🗿

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
A: Market lagi jelek dan bot pemilih. Lu juga harusnya pemilih. Gak semua candle wajib di-entry.

**Q: Boleh pakai uang pinjol?**
A: 🗿 Tidak. Jangan. Ini satu-satunya bagian yang gak bercanda.

**Q: Bot-nya bisa jadi pacar?**
A: Dia konsisten, fast response, gak ghosting. Tapi gak bisa diajak makan seblak. Jadi tidak.

**Q: Gw clone repo ini, boleh pake API key yang sama bareng temen?**
A: **JANGAN.** Satu orang salah klik, OCO kalian tabrakan. Bikin key masing-masing.

---

## 🧯 Cara Stop Bot

~~~bash
sudo systemctl stop donal-signal.service
~~~

---

## 🧱 Tech Stack

- **Python 3** — biar cuan, bukan bikin enterprise Java
- **CCXT** — jembatan ke Binance
- **Pandas + NumPy** — ngitung indikator tanpa sempoa
- **Streamlit + Plotly** — dashboard web aesthetic
- **python-dotenv** — biar secret gak bocor
- **systemd** — biar bot auto-nyala walau VPS restart
- **Telegram API** — notif secepat gosip

---

## 🧠 Catatan Risk Management (Serius, Gak Kocak)

### Mode Live 🔴
- JANGAN aktifkan withdrawal di API key
- Mulai dari risk 0.5–1%
- Test di testnet minimal seminggu
- Pantau tiap hari
- Ada error? Stop dulu

### Umum
- Jangan pakai uang makan, uang kos, uang pinjol
- Jangan all-in
- Jangan balas dendam ke market
- Jangan geser SL sambil bilang "nanti juga balik"

Market bukan tempat buktiin ego.
**Cash juga posisi.**

---

## 📜 Disclaimer

> **Bot ini bukan financial advice.**
>
> Crypto volatil. Bisa naik, bisa turun, bisa bikin lu jadi philosopher jam 2 pagi.
>
> Semua keputusan di tangan lu. Bot cuma alat. Bukan dukun. Bukan jaminan cuan.
>
> **Mode Live = risiko tinggi.**
> Proteksi modal dulu. Profit belakangan.
> Karena di market, yang penting bukan cuma cuan, tapi **survive dulu**.

---

## 🫡 Credits

Dibuat oleh **DONAL** buat trader yang pengen disiplin, gak FOMO, dan gak mau jadi exit liquidity whale.

Kasih ⭐ kalau membantu. Pakai bijak. Touch grass sesekali. 🌱

---

## 📄 License

MIT. Bebas dipakai & dimodifikasi.
Tapi jangan dijual ulang jadi "robot premium VIP". Itu cringe. 💀

---

## 🧠 Quotes of the Repo

> _"Entry tanpa plan = sedekah ke whale."_

> _"SL itu asuransi, bukan penghinaan."_

> _"Market gak peduli lu butuh uang buat self reward."_

> _"Kalau bot bilang skip, ya skip. Lu bukan main character di market."_

> _"Rungkad itu canon event. Rungkad berulang itu pilihan."_

---

_"In crypto we trust, in DONAL we believe."_ 🚀

**WAGMI** 🤝

_Dibuat dengan 💻 dari VPS, dijaga sama AI yang gak mau lu rungkad._
