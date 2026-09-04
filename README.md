# 🤖 DONAL Signal Robot VPS

> *"Dia gak tidur, gak makan, gak minta validasi. Kerjaannya cuma satu: ngejaga modal lo dari tangan lo sendiri."* 🗿

Robot trading crypto berbasis **Python + CCXT + Binance Spot**, ditujukan untuk deployment 24/7 di VPS.
Dia mantau market 24/7 biar lo bisa tidur.
Karena kalau lo yang mantau, lo gak tidur. Besoknya lo trading pakai emosi. Terus rungkad. Terus nyalahin market.

Padahal market gak kenal lo. 🗿

---

## ⚠️ Baca Dulu, Bestie

> **ROBOT INI PUNYA 3 MODE:**
>
> 1. **SIGNAL ONLY** (default) — robot teriak di Telegram, lo yang eksekusi. Cocok buat yang belum percaya sama diri sendiri (valid).
> 2. **TESTNET** — robot trading pakai uang monopoli. Lo belajar, modal aman.
> 3. **LIVE** 🔴 — robot trading pakai UANG BENERAN. Baca disclaimer. Terus baca lagi. Terus istighfar.
>
> **Default = SIGNAL ONLY.** Mau auto-trading? Ubah `TRADING_MODE` + isi API key.
>
> **JANGAN PERNAH** commit `.env` ke Git. Isinya API key. Kecuali lo mau jadi konten "kena hack" di Twitter.

---

## ✨ Kenapa Robot Ini Goated?

### 🧢 Signal Only by Default
Robot cuma teriak, gak pegang uang lo.
Dia tau diri.

### 🤖 Auto Order (Opt-In)
Kalau lo aktifin, robot bakal:
- Beli pas sinyal valid
- Pasang SL/TP langsung di exchange (native OCO) dan rekonsiliasi order setelah restart/network failure
- Jual pas kena SL/TP/trend exit

Semua pakai market order. Karena limit order itu kayak nunggu doi bales chat — kadang gak pernah. 💀

### ️ Risk Management Lebih Ketat dari Ortu
- Max posisi terbuka
- Guard korelasi (BTC/ETH/SOL satu geng, gak dibeli bareng)
- Limit rugi harian & mingguan (circuit breaker)
- Filter sesi (skip jam market sepi)
- Guard slippage (batal masuk kalau harga kejauhan)
- Sizing berbasis risiko dengan validasi saldo tersedia dan actual fill price

Kalau semua ini masih bikin lo rugi, berarti market lagi gak masuk akal.
Tapi setidaknya lo rugi **terencana**. 🗿

### 🚨 Anti Fakeout Detector
- **Resistance room**: mepet atap? Skip. Robot gak mau nyangkut di pucuk terus jadi konten ratapan.
- **Volume filter**: breakout tanpa volume itu kayak chat "pagi" dari doi — keliatannya ada, tapi kosong.
- **ATR scaling**: SL/TP ngikutin volatilitas, gak asal tempel.

### 🛡️ Execution Safety
- Client order ID deterministic untuk mencegah duplicate BUY/SELL
- Intent order disimpan sebelum request exchange
- Timeout/network error direkonsiliasi sebelum retry
- OCO tidak pernah dibuat ulang secara blind
- Status proteksi yang UNKNOWN memblokir market SELL sampai status exchange jelas
- Restart VPS melakukan recovery intent/order

### 📱 Telegram Bestie
Notif cepet. Fast response. Gak ghosting.
Pokoknya semua yang gak bisa dilakuin doi. 😭

---

## 🧠 Strategi: "4H Trend, 1H Breakout"

### 1. Tren 4H — Cek Cuaca Dulu 🧠
- EMA 20 > EMA 60?
- RSI > 50?

Dua-duanya iya = cuaca cerah, boleh piknik.
Selain itu = mendung. Jangan maksa piknik. Nanti kehujanan. Terus nangis.

### 2. Entry 1H — Nunggu Konfirmasi 🎯
Robot nunggu:
- Close > EMA 20
- RSI > RSI_ENTRY
- Breakout high 20 bar
- Volume > rata-rata
- Jarak ke resistance masih lega

Semua iya? **Gaskeun.** 👨‍🍳
Ada yang enggak? **Skip.** Robot gak kenal kata "tanggung".

### 3. Exit — Gak Pakai Perasaan 🚪
- **TP HIT**: cuan, ambil. Jangan serakah.
- **SL HIT**: rugi, terima. Besok masih ada market.
- **TREND EXIT**: tren rusak, keluar. Jangan jadi holder abadi.

---

## 🚀 Cara Install di VPS Ubuntu

```bash
# 1. Clone
git clone https://github.com/rmdnl/donal-signal-railway.git
cd donal-signal-railway

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Bikin .env
cp .env.example .env
nano .env

# 4. Jalanin
python3 signal_bot.py
```

Kalau muncul `🤖 DONAL Signal Robot started`, berarti robot hidup. W. 🎉

---

## 🔐 Setup `.env` (Canon Event, Jangan Skip)

### Mode Signal Only (Default, Aman)

```env
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
```

### Tambahan Buat Testnet (Uang Monopoli)

```env
TRADING_MODE=testnet
BINANCE_TESTNET_API_KEY=key_testnet_lo
BINANCE_TESTNET_API_SECRET=secret_testnet_lo

RISK_PCT_PER_TRADE=1.0
MAX_ENTRY_SLIPPAGE_PCT=0.5
USE_NATIVE_OCO_SLTP=true
TAKER_FEE_PCT=0.1
```

### Tambahan Buat Live (UANG BENERAN) 🔴

```env
TRADING_MODE=live
# HANYA centang "Spot Trading". JANGAN centang withdrawal. SERIUS.
BINANCE_LIVE_API_KEY=key_live_lo
BINANCE_LIVE_API_SECRET=secret_live_lo

RISK_PCT_PER_TRADE=1.0
MAX_ENTRY_SLIPPAGE_PCT=0.5
USE_NATIVE_OCO_SLTP=true
TAKER_FEE_PCT=0.1
```

---

## 📱 Telegram Token & Chat ID

1. Chat `@BotFather` (yang verified, bukan yang fake)
2. Kirim `/newbot`, ikutin instruksi
3. Copy token → paste ke `TELEGRAM_BOT_TOKEN`

Chat ID:
1. Chat `@userinfobot`
2. Kirim apa aja, dia kasih ID lo
3. Paste ke `TELEGRAM_CHAT_ID`

---

## 🤖 Binance API Key

### Testnet
1. Buka https://testnet.binance.vision
2. Login pakai GitHub
3. Generate key, copy-paste

### Live 🔴
1. Binance → API Management
2. Bikin key baru
3. **CENTANG**: Enable Spot Trading
4. **JANGAN CENTANG**: Withdrawals, Futures
5. Copy-paste ke `.env`

Kalau lo centang withdrawal, robot ini berubah jadi mesin sedekah ke hacker. Jangan.

---

## 🖥️ Jalanin di Background

Robot bukan tuyul. Kalau terminal ditutup, dia mati. Jadi:

### Pakai `screen` (Santai)

```bash
sudo apt install screen -y
screen -S donal-robot
python3 signal_bot.py
# Detach: Ctrl+A, D
# Balik: screen -r donal-robot
```

### Pakai `systemd` (Sigma Mode, Auto-Restart)

```bash
sudo nano /etc/systemd/system/donal-robot.service
```

```ini
[Unit]
Description=DONAL Signal Robot - Financial Freedom Machine
After=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/donal-signal-railway
ExecStart=/usr/bin/python3 /home/ubuntu/donal-signal-railway/signal_bot.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable donal-robot
sudo systemctl start donal-robot
```

Cek: `sudo systemctl status donal-robot`
Log: `sudo journalctl -u donal-robot -f`

---

## 📊 Contoh Output Telegram

### BUY (Signal Only)

```text
🟢 BUY SIGNAL BTC/USDT
Strategy: DONAL 4H Trend 1H Breakout
Status: SIGNAL ONLY (tanpa auto order)
Entry ideal close 1H: 67420.50
Harga saat alert: 67425.10
SL: 66850.20
TP: 68500.00
ATR: 380.15
Struktur S/R: SL, TP
Volume: 1.85x MA
Catatan: Eksekusi manual, gunakan risiko kecil.
```

### BUY Executed (Auto Trading)

```text
🟢 BUY ORDER EXECUTED BTC/USDT
Mode: TESTNET
Qty: 0.015 BTC
Entry: 67425.10
SL: 66850.20 (OCO di exchange)
TP: 68500.00 (OCO di exchange)
Risk: 1.0% dari saldo USDT
Status: Posisi aktif.
```

### SL HIT

```text
🔴 SL HIT BTC/USDT
Mode: TESTNET
Entry: 67425.10
Exit: 66850.20
PnL Net: -8.75 USDT (-1.30%)
Status: Posisi ditutup. OCO di-cancel.
```

Kalau kena SL jangan marah. SL itu asuransi, bukan penghinaan.

---

## ⚙️ Variable `.env` (Versi Singkat Tapi Ngena)

| Variable | Default | Fungsi |
|---|---:|---|
| `SYMBOLS` | `BTC/USDT` | Pair pantauan |
| `TIMEFRAME` / `HTF_TIMEFRAME` | `1h` / `4h` | TF entry / TF tren |
| `TRADING_MODE` | `off` | off / testnet / live |
| `SL_MULT` / `TP_MULT` | `1.5` / `2.5` | Pengali ATR buat SL/TP |
| `MIN_RISK_REWARD` | `1.0` | Minimum R:R sebelum entry |
| `RSI_ENTRY` / `RSI_EXIT` | `50` / `45` | Batas RSI masuk/keluar |
| `USE_RES_FILTER` | `true` | Skip kalau mepet resistance |
| `MIN_ROOM_ATR` | `1.0` | Minimal napas ke resistance |
| `USE_STRUCTURE_SLTP` | `true` | SL/TP pakai pivot S/R |
| `USE_VOLUME_FILTER` | `true` | Breakout wajib ada volume |
| `VOLUME_MULT` | `1.0` | Volume harus > MA x ini |
| `USE_VOL_SCALED_SLTP` | `true` | SL/TP ngikutin volatilitas |
| `MAX_CONCURRENT_POSITIONS` | `2` | Max posisi terbuka |
| `MAX_POSITIONS_PER_GROUP` | `1` | Max posisi per geng korelasi |
| `RISK_PCT_PER_TRADE` | `1.0` | Risiko target per trade (% saldo) |
| `MAX_ACTUAL_RISK_PCT` | `1.25` | Batas risiko setelah actual fill + SL |
| `RISK_OVERSHOOT_ACTION` | `reduce` | reduce / exit / hold saat risiko aktual melewati batas |
| `MAX_ENTRY_SLIPPAGE_PCT` | `0.5` | Batas slippage entry |
| `USE_NATIVE_OCO_SLTP` | `true` | SL/TP native OCO di exchange + reconciliation-first |
| `TAKER_FEE_PCT` | `0.1` | Fee per sisi (0.075 kalau pakai BNB) |
| `DAILY_LOSS_LIMIT_PCT` | `3.0` | Rugi harian segini = stop entry |
| `WEEKLY_LOSS_LIMIT_PCT` | `6.0` | Rugi mingguan segini = stop entry |
| `SESSION_START_HOUR` / `END` | `8` / `22` | Jam trading (UTC) |

---

## 🧮 Matematika Robot (Biar Gak Dibilang Judi)

### SL/TP
```text
SL = Entry - (ATR * SL_MULT)
TP = Entry + (ATR * TP_MULT)
```

### Position Size
```text
qty = (saldo * RISK_PCT_PER_TRADE%) / (entry - SL)
```

Contoh: saldo 1000 USDT, risk 1%, entry 67425, SL 66850 →
```text
risk = 10 USDT
qty = 10 / 575 = 0.0174 BTC
```

Robot juga cek minQty & minNotional exchange. Gak valid? Skip. Robot gak maksa.

---

## 🧠 Kenapa Robot Skip Entry?

1. Tren 4H mendung
2. Breakout belum valid
3. Mepet resistance (mau nyangkut di pucuk? enggak)
4. Volume tipis (breakout KW)
5. Slot posisi penuh
6. Satu geng korelasi udah ada yang open
7. Sinyal basi
8. Di luar jam trading
9. (Auto) Saldo 0 / sizing gak valid
10. (Auto) Slippage kejauhan
11. (Auto) Limit rugi harian/mingguan kena

Kalau robot skip, jangan baper. Dia lagi ngejaga dompet lo.

---

## 🗣️ Testimoni Fiktif (Tapi Relate)

> ⭐⭐⭐⭐⭐
> "Dulu aku nyangkut di pucuk 3 bulan. Sekarang robot yang nentuin SL, jadi aku cuma nyangkut di perasaan."
> — **Bang Rungkad**, 27, mantan holder pucuk 🗿

> ⭐⭐⭐⭐⭐
> "Robotnya bilang skip. Aku maksa entry manual. Aku yang rugi. Ternyata yang perlu di-upgrade bukan robotnya, tapi aku."
> — **Kak Delulu**, 24, korban FOMO berulang 😭

> ⭐⭐⭐⭐⭐
> "Testnet 2 minggu profit. Pindah live rugi. Ternyata masalahnya di mental, bukan di robot."
> — **Mas Menyala**, 30, aura -1000 🔥

> ⭐⭐⭐
> "Kurang satu bintang soalnya robotnya gak bisa diajak healing."
> — **Bestie**, umur rahasia 💅

---

## ❓ FAQ (Frequently Asked Questions oleh Orang Delulu)

**Q: Robot ini bisa bikin kaya?**
A: Dia bikin disiplin. Kaya itu efek samping. Yang pasti lo gak FOMO sendirian.

**Q: Robot ini gak bakal rugi?**
A: Bakal. Dia robot, bukan dukun. Kalau ada yang janji "pasti cuan", tutup repo ini dan lapor polisi.

**Q: Kok gak ada sinyal-sinyal?**
A: Market lagi jelek dan robot pemilih. Lo juga harusnya pemilih. Gak semua candle wajib di-entry.

**Q: Boleh pakai uang pinjol?**
A: 🗿 Tidak. Jangan. Ini satu-satunya bagian yang gak bercanda.

**Q: Robotnya bisa jadi pacar?**
A: Dia konsisten, fast response, gak ghosting. Tapi gak bisa diajak makan seblak. Jadi tidak.

---

## 🐛 Troubleshooting

| Masalah | Solusi |
|---|---|
| `ModuleNotFoundError` | `pip3 install -r requirements.txt` |
| Telegram 404 | Token salah, cek BotFather |
| Telegram 401 | Token gak valid, regenerate |
| Telegram diem | Chat ID salah / robot belum di-Start |
| Robot mati pas terminal ditutup | Pakai `screen` / `systemd` |
| Gak ada sinyal | Market sideways. Sabar = cuan |
| `TRADING_MODE tidak dikenal` | Isi `off` / `testnet` / `live` doang |
| Key testnet/live kosong | Isi dulu di `.env`, jangan cuma niat |
| Gagal kirim BUY | Cek permission API, saldo, minNotional |
| OCO gagal/unknown | Robot menahan status protection_unknown dan tidak blind retry/SELL sampai exchange bisa direkonsiliasi |
| State file ilang | Backup / pakai volume |

---

## 📁 `state_signals.json` = Memori Robot

Isinya posisi, candle terakhir, alert terakhir, tracking rugi.
Kalau ilang, robot amnesia. Kayak lo abis kena SL — lupa semua rencana. 🗿

Backup:
```bash
cp state_signals.json state_signals.backup.json
```

---

## 🔄 Recovery Setelah VPS Restart

Bot menyimpan `entry_intents`, `oco_intents`, dan `exit_intents` sebelum request yang berisiko ambigu. Saat start ulang, bot mencari order berdasarkan client ID yang sama sebelum membuat order baru. Jika status exchange tidak bisa dipastikan, bot memilih aman: **tidak mengirim duplicate order**.

## 🧯 Cara Stop Robot

```bash
# screen
screen -r donal-robot   # terus Ctrl+C

# systemd
sudo systemctl stop donal-robot
```

---

## 🧱 Tech Stack

- **Python 3** — biar cuan, bukan bikin enterprise Java
- **CCXT** — jembatan ke Binance
- **Pandas + NumPy** — ngitung indikator tanpa sempoa
- **python-dotenv** — biar secret gak bocor
- **Telegram API** — notif secepat gosip

---

## 🧠 Catatan Risk Management (Serius, Gak Kocak)

### Mode Live 🔴
- JANGAN aktifkan withdrawal di API key
- Mulai dari risk 0.5–1%
- Test di testnet minimal seminggu
- Pantau tiap hari
- Ada error? Stop dulu, jangan biarin

### Umum
- Jangan pakai uang makan, uang kos, uang pinjol
- Jangan all-in
- Jangan balas dendam ke market
- Jangan geser SL sambil bilang "nanti juga balik"

Market bukan tempat buktiin ego.
Market tempat eksekusi rencana.

Setup jelek? Bilang jelek. Setup bagus? Bilang bagus. Gak yakin? Skip.
**Cash juga posisi.**

---

## 📜 Disclaimer

> **Robot ini bukan financial advice.**
>
> Crypto volatil. Bisa naik, bisa turun, bisa bikin lo jadi philosopher jam 2 pagi.
>
> Semua keputusan di tangan lo. Robot cuma alat. Bukan dukun. Bukan jaminan cuan.
>
> **Mode Live = risiko tinggi.**
>
> Proteksi modal dulu. Profit belakangan.
> Karena di market, yang penting bukan cuma cuan, tapi **survive dulu**.

---

## 🚀 Roadmap

- [ ] Trailing stop
- [ ] Backtesting
- [x] Web dashboard
- [ ] Exchange lain
- [ ] Multi Telegram
- [ ] News filter
- [ ] Statistik win rate
- [ ] Drawdown tracking

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

> *"Entry tanpa plan = sedekah ke whale."*

> *"SL itu asuransi, bukan penghinaan."*

> *"Market gak peduli lo butuh uang buat self reward."*

> *"Kalau robot bilang skip, ya skip. Lo bukan main character di market."*

> *"Rungkad itu canon event. Rungkad berulang itu pilihan."*

---

*"In crypto we trust, in DONAL we believe."* 🚀

**WAGMI** 🤝
