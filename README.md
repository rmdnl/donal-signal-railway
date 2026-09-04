# 🤖 DONAL Signal Railway

> *"Bukan bot trading biasa. Ini tool disiplin buat nge-hunt cuan tanpa FOMO. No cap."* 💀🔥

Bot crypto **Python + CCXT + Binance Spot** dengan 3 mode operasi, dashboard web real-time, dan Telegram anti-spam.

## 🎛️ Mode Operasi (`TRADING_MODE` di `.env`)

| Mode | Perilaku |
|---|---|
| `off` | Signal-only: kirim sinyal BUY/EXIT ke Telegram, tanpa order nyata (default, aman) |
| `testnet` | Auto-trading di Binance Spot Testnet (uang virtual) |
| `live` | Auto-trading uang beneran — WAJIB validasi di testnet dulu! |

## 🧠 Strategy: 4H Trend + 1H Breakout

- **Tren 4H**: EMA20 > EMA60 && RSI > 50.
- **Entry 1H** (saat candle close): close > EMA20, RSI > level entry, breakout high 20 bar.
- **Filter**: resistance room, volume breakout, **ADX (trend strength)**, session UTC 8-22.
- **SL/TP**: ATR-based, structure-based (pivot S/R), volatility-scaled.
- **Exit**: SL HIT / TP HIT / **TREND EXIT** (close < EMA20 atau RSI < level exit).

## 🛡️ Risk Management

- Risk per trade 1% saldo + slippage guard saat entry.
- Max concurrent positions & correlation guard.
- Daily/weekly loss limit (circuit breaker).
- Break-even protection (SL geser ke modal setelah profit).
- **Native OCO SL/TP di exchange** — proteksi tetep aktif walau bot/VPS mati.
- Anti duplicate order + reconciliation otomatis setelah restart.
- Mode live: bot nolak jalan kalau API key punya izin withdrawal (fail-closed).

## 📱 Telegram Anti-Spam

- Dedup pesan identik (2 menit) + max 6 pesan/menit.
- Notif sah: startup, BUY SIGNAL, SL/TP/TREND EXIT, error penting (di-throttle 5 menit).

## 📊 Dashboard Web (Terminal X)

- `dashboard.py` — Streamlit + Plotly, auto-refresh 5 detik, port 8501.
- Equity, PnL realized/unrealized, win rate, open positions, history, candlestick chart.
- Status bot online/offline + badge mode.

## 📂 Struktur Project

```text
donal-signal-railway/
├── signal_bot.py      # bot utama
├── dashboard.py       # dashboard web
├── requirements.txt
├── .env.example       # template config
├── README.md
└── .gitignore
```

File runtime (di-ignore git): `state_signals.json`, `trade_history.json`.

## 🚀 Deploy VPS (systemd)

```bash
sudo systemctl enable --now donal-signal.service      # bot
sudo systemctl enable --now donal-dashboard.service   # dashboard
```

Keduanya `Restart=always` → auto-nyala setelah reboot atau crash.

## ⚙️ Setup Cepat

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # isi token/key sesuai mode
```

## ⚠️ Aturan Main

- Jangan pernah commit `.env`.
- Testnet dulu sebelum live.
- API key live: **spot trading ONLY, withdrawal MATI**.
- Bot ini tool disiplin, bukan mesin cetak uang. Market kadang villain arc. 📉
