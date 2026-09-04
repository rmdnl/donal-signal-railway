# 🤖 DONAL Signal Railway

> *"Bukan bot trading biasa. Ini sigma male grindset financial freedom tool. No cap, fr fr."* 💀🔥

Bot sinyal crypto berbasis **Python + CCXT + Binance Spot** yang bakal jadi **bestie** kamu buat nge-hunt cuan di market.

Dia gak bakal FOMO.
Dia gak bakal FUD.
Dia gak bakal ghosting kayak mantan.
Dan yang paling penting: **dia disiplin banget.** Very demure, very mindful. 🙏

---

## ⚠️ Baca Dulu, Bestie

> **BOT INI BISA 3 MODE:**
>
> 1. **`off`** (default, aman) — cuma kirim sinyal ke Telegram, gak ada order nyata. Lo yang eksekusi manual.
> 2. **`testnet`** — auto-trading di Binance Testnet (uang virtual). Buat nyobain dulu sebelum gaspol.
> 3. **`live`** — auto-trading uang beneran. **WAJIB** test dulu di testnet. Kalau lo loss, jangan nyalahin bot. Market emang kadang villain arc. 📉

---

## ✨ Kenapa Bot Ini Slay?

### 🧢 No Cap: 3 Mode Sekali Setup
Ganti mode tinggal ubah `TRADING_MODE` di `.env`. Gak perlu hapus-pasang kode.

### 📊 Multi-Timeframe Rizz
- **4H** buat cek tren besar (EMA20 > EMA60 && RSI > 50).
- **1H** buat cari entry (close > EMA20, RSI > level entry, breakout high 20 bar).

Jadi gak asal masuk cuma karena candle ijo dikit. Kita bukan NPC.

### 🚨 Anti Fakeout Detector
Bot ini punya filter:
- **Resistance room filter**: kalau udah mepet resistance, skip. Jangan jadi exit liquidity whale.
- **Volume filter**: breakout tanpa volume itu red flag. Skip.
- **ADX filter**: cek kekuatan tren (ADX > 20). Market lemes? Skip.
- **Session filter**: cuma entry di sesi aktif (UTC 8-22). Sesi Asia sepi? Skip.

### 🛡️ Risk Management Goated
- **SL/TP** berbasis ATR + structure (pivot S/R).
- **Break-even protection**: kalau profit udah 1%, SL geser ke modal. Cuan dikunci.
- **Daily/weekly loss limit**: kalau rugi udah kena batas (3%/6%), entry baru diblokir. Posisi yang udah kebuka tetep dijaga.
- **Native OCO SL/TP**: SL/TP nempel langsung di Binance. Bot mati, VPS crash, proteksi tetep aktif.
- **Max concurrent positions** & **correlation guard**: biar gak buka BTC, ETH, SOL barengan kayak lagi koleksi kerugian.
- **Anti duplicate order**: kalau request timeout, bot cek dulu order-nya beneran ada atau gak. Gak bikin order dobel.

### 📱 Telegram Bestie (Anti-Spam)
Begitu ada sinyal, bot langsung kirim ke Telegram. **Tapi gak spam.**
- Pesan identik dalam 2 menit → dibuang.
- Max 6 pesan/menit → lewat dari itu dibuang.
- Notif sah: startup, BUY SIGNAL, SL/TP/TREND EXIT, error penting (di-throttle 5 menit).

Fast response. Gak kayak doi yang cuma read.

### 📊 Dashboard Terminal X (Web UI)
Buka `dashboard.py` di port 8501, dapet:
- **Equity** (saldo + unrealized PnL).
- **Realized & Unrealized PnL** + **Win Rate**.
- **Open Positions** (pair, entry, last price, PnL, TP/SL).
- **Equity Curve** (grafik pertumbuhan).
- **History** (trade terakhir + reason exit).
- **Candlestick chart** pake Plotly.
- **Status bot**: online/offline + badge mode.

Auto-refresh tiap 5 detik. Glassmorphism dark theme. Very aesthetic.

---

## 🧠 Strategi: "4H Trend, 1H Breakout"

Ini lore-nya.

### 1. Cek Tren di 4H — Big Brain Energy 🧠
Bot cek:
- EMA 20 > EMA 60?
- RSI > 50?

Kalau dua-duanya iya, market dianggap lagi punya **bullish vibe**.

Kalau gak? Ya skip. Kita gak counter-trend kayak orang nekat.

### 2. Cari Entry di 1H — Small Brain Execution 🎯
Bot cari kondisi (saat candle close):
- Close > EMA 20
- RSI > batas entry
- Close breakout high 20 bar sebelumnya
- ADX > 20 (tren kuat)
- Volume > rata-rata

Kalau semua checklist terpenuhi, bot bilang:

> **"Let him cook."** 👨‍🍳🔥

### 3. Filter Tambahan — Anti Rug Pull 🚫
Bot juga cek:
- Apakah jarak ke resistance masih cukup?
- Apakah volume breakout valid?
- Apakah ADX nunjukin tren kuat?
- Apakah sesi lagi aktif?
- Apakah sinyal belum basi?
- Apakah slot posisi masih tersedia?
- Apakah asetnya gak terlalu correlated sama posisi yang udah ada?

Kalau ada yang sus, sinyal di-skip.

### 4. Exit Strategy — 3 Pintu Keluar 🚪
- **SL HIT**: cut loss keras kalau harga jatoh ke stop.
- **TP HIT**: take profit kalau target kesentuh.
- **TREND EXIT**: pintu "pulang cepet" — tren patah (close < EMA20 atau RSI < 45) sebelum SL/TP kena. Nyelametin profit.

---

## 📂 Struktur Project

```text
donal-signal-railway/
├── signal_bot.py         # bot utama
├── dashboard.py          # dashboard web (Streamlit)
├── requirements.txt      # dependencies
├── .env.example          # template config (copy ke .env)
├── README.md             # you are here
└── .gitignore            # biar file rahasia gak ke-commit
```

File runtime (auto-generated, di-ignore git):
- `state_signals.json` — otak bot (posisi virtual, last candle, intents)
- `trade_history.json` — history closed trades

---

## 🚀 Deploy VPS (systemd)

Bikin 2 service biar bot & dashboard auto-nyala walau VPS restart:

### Bot Service
```bash
sudo nano /etc/systemd/system/donal-signal.service
```
```ini
[Unit]
Description=DONAL Signal Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/donal-signal-railway
ExecStart=/home/ubuntu/donal-signal-railway/venv/bin/python /home/ubuntu/donal-signal-railway/signal_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Dashboard Service
```bash
sudo nano /etc/systemd/system/donal-dashboard.service
```
```ini
[Unit]
Description=DONAL Dashboard
After=network.target donal-signal.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/donal-signal-railway
ExecStart=/home/ubuntu/donal-signal-railway/venv/bin/streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Aktifkan
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now donal-signal.service
sudo systemctl enable --now donal-dashboard.service
```

Sekarang mau VPS di-restart, dicabut colokannya, atau kiamat sekalipun, bot & dashboard bakal **auto-nyala** dalam 10 detik.

---

## ⚙️ Setup Cepat

```bash
git clone https://github.com/rmdnl/donal-signal-railway.git
cd donal-signal-railway
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env   # isi token Telegram + API key (kalau mode testnet/live)
```

### Mode `off` (Signal-Only)
Cuma butuh:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### Mode `testnet` / `live`
Tambahin:
- `BINANCE_TESTNET_API_KEY` + `BINANCE_TESTNET_API_SECRET` (buat testnet)
- `BINANCE_LIVE_API_KEY` + `BINANCE_LIVE_API_SECRET` (buat live)

**Generate testnet key**: https://testnet.binance.vision  
**Generate live key**: Binance → API Management → centang **Spot Trading ONLY**, **WITHDRAWAL MATI**.

---

## 🛠️ Monitoring

### Cek status bot
```bash
sudo systemctl status donal-signal.service
```

### Liat log realtime
```bash
sudo journalctl -u donal-signal.service -f
```

### Cek dashboard
Buka `http://<IP-VPS>:8501` di browser. Jangan lupa buka port 8501 di Security Group cloud provider.

---

## ⚠️ Aturan Main

- **Jangan pernah commit `.env`** — isinya API key & token. Udah di-ignore.
- **Testnet dulu sebelum live** — validasi strategy di uang virtual.
- **API key live**: spot trading ONLY, withdrawal MATI. Bot bakal nolak jalan kalau withdrawal aktif (fail-closed).
- **Bot ini tool disiplin, bukan mesin cetak uang** — market kadang villain arc. 📉
- **Kalau lo loss, itu salah market, bukan salah bot** (jk, ini salah lo juga sih kalau gak disiplin).

---

## 🧩 Tech Stack

- **Python 3** — karena kita mau cuan, bukan mau bikin enterprise Java boilerplate.
- **CCXT** — koneksi ke Binance (public + private API).
- **Pandas + NumPy** — biar ngitung indikator gak pakai sempoa.
- **Streamlit + Plotly** — dashboard web yang aesthetic.
- **python-dotenv** — biar secret gak bocor ke GitHub.
- **systemd** — biar bot auto-nyala walau VPS restart.
- **Telegram Bot API** — karena notif harus cepet, kayak gosip.

---

## 📞 Support

Kalau ada bug, buka issue di GitHub. Kalau lo cuma mau ngeluh karena loss, itu bukan bug, itu life lesson. 😌

---

**WAGMI (We All Gonna Make It)** 🚀

*Tapi seriusan, protect your capital first. Cuan nomor dua.*
