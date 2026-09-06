import os
import json
import time
import logging
import signal
import threading
import urllib.request
import hashlib
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import ccxt
from dotenv import load_dotenv

load_dotenv()


def env_bool(key, default=False):
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "y", "on")


def env_list(key, default=""):
    val = os.getenv(key, default)
    return [x.strip().upper() for x in val.split(",") if x.strip()]


def env_int(key, default):
    try:
        return int(os.getenv(key, str(default)))
    except Exception:
        return default


def env_float(key, default):
    try:
        return float(os.getenv(key, str(default)))
    except Exception:
        return default


# =====================
# CONFIG
# =====================
SYMBOLS = env_list("SYMBOLS", "BTC/USDT")
TIMEFRAME = os.getenv("TIMEFRAME", "1h")
HTF_TIMEFRAME = os.getenv("HTF_TIMEFRAME", "4h")

ATR_LENGTH = env_int("ATR_LENGTH", 14)
RSI_LENGTH = env_int("RSI_LENGTH", 14)
SL_MULT = env_float("SL_MULT", 1.5)
TP_MULT = env_float("TP_MULT", 2.5)
RSI_ENTRY = env_int("RSI_ENTRY", 50)
RSI_EXIT = env_int("RSI_EXIT", 45)

SR_LEFT_BARS = env_int("SR_LEFT_BARS", 10)
SR_RIGHT_BARS = env_int("SR_RIGHT_BARS", 10)
USE_RES_FILTER = env_bool("USE_RES_FILTER", True)
MIN_ROOM_ATR = env_float("MIN_ROOM_ATR", 1.0)
USE_STRUCTURE_SLTP = env_bool("USE_STRUCTURE_SLTP", True)
SR_BUFFER_ATR = env_float("SR_BUFFER_ATR", 0.3)

USE_VOLUME_FILTER = env_bool("USE_VOLUME_FILTER", True)

# --- ADX Filter (Trend Strength) ---
USE_ADX_FILTER = env_bool("USE_ADX_FILTER", True)
ADX_LENGTH = env_int("ADX_LENGTH", 14)
ADX_THRESHOLD = env_float("ADX_THRESHOLD", 20.0)

# --- Strategy variant ---
VOLUME_MA_LENGTH = env_int("VOLUME_MA_LENGTH", 20)
VOLUME_MULT = env_float("VOLUME_MULT", 1.5)  # Match Pine Script default volMult=1.5



# --- Trading fee (Pine's strategy() already bakes commission_value=0.1 into its
# backtest results; the Python bot didn't, so gross PnL shown here was overstating
# real returns). Default matches Binance Spot standard taker fee. ---
TAKER_FEE_PCT = env_float("TAKER_FEE_PCT", 0.1)  # % per side (per trade leg)
ROUND_TRIP_FEE_PCT = TAKER_FEE_PCT * 2  # entry + exit

LOOP_INTERVAL_SECONDS = env_int("LOOP_INTERVAL_SECONDS", 30)
CANDLE_CONFIRM_OFFSET_SEC = env_int("CANDLE_CONFIRM_OFFSET_SEC", 5)

TRACK_SL_TP = env_bool("TRACK_SL_TP", True)
SEND_TREND_EXIT = env_bool("SEND_TREND_EXIT", True)
ENTRY_ON_FIRST_RUN = env_bool("ENTRY_ON_FIRST_RUN", False)
MAX_ENTRY_DELAY_MINUTES = env_int("MAX_ENTRY_DELAY_MINUTES", 15)


# =====================
# AUTO TRADING (Binance API)
# =====================
# TRADING_MODE:
#   off     -> signal-only (default, SAMA seperti sebelumnya, tidak ada order nyata)
#   testnet -> eksekusi order sungguhan tapi ke Binance Spot Testnet (uang virtual)
#   live    -> eksekusi order sungguhan ke akun Binance asli (UANG BENERAN)
# Ganti mode tinggal ubah baris ini di .env, key testnet & live disimpan terpisah
# supaya gonta-ganti mode tidak perlu hapus-pasang credential.
TRADING_MODE = os.getenv("TRADING_MODE", "off").strip().lower()

BINANCE_TESTNET_API_KEY = os.getenv("BINANCE_TESTNET_API_KEY", "").strip()
BINANCE_TESTNET_API_SECRET = os.getenv("BINANCE_TESTNET_API_SECRET", "").strip()
BINANCE_LIVE_API_KEY = os.getenv("BINANCE_LIVE_API_KEY", "").strip()
BINANCE_LIVE_API_SECRET = os.getenv("BINANCE_LIVE_API_SECRET", "").strip()

QUOTE_ASSET = os.getenv("QUOTE_ASSET", "USDT").strip().upper()

# Position sizing match Pine: percent_of_equity=20 (20% dari equity per posisi).
PCT_OF_EQUITY = env_float("PCT_OF_EQUITY", 20.0)  # match Pine percent_of_equity=20

# Entry & exit (SL/TP/trend exit) pakai MARKET order -- prioritas kepastian eksekusi
# di atas presisi harga. Karena market order langsung fill (bukan menunggu seperti
# limit order), tidak ada lagi konsep timeout/cancel untuk entry maupun exit.
#
# Konsekuensinya: harga fill bisa meleset dari harga referensi saat sinyal muncul
# estimasi slippage (bid/ask saat ini vs harga referensi) sudah melebihi batas ini,
# entry DIBATALKAN sebelum order dikirim (0 = nonaktif, selalu entry berapa pun
# slippage-nya). Untuk exit TIDAK ada guard semacam ini -- exit harus selalu jalan
# demi risk management, jadi cuma dilaporkan (bukan dibatalkan) berapa pun besarnya.
USE_LIMIT_ENTRY = env_bool("USE_LIMIT_ENTRY", False)  # [NEW] Pakai limit order instead of market (lebih presisi, match Pine process_orders_on_close)
LIMIT_ENTRY_BUFFER_PCT = env_float("LIMIT_ENTRY_BUFFER_PCT", 0.1)  # [NEW] Limit price = close + buffer%
LIMIT_ENTRY_TIMEOUT_SEC = env_int("LIMIT_ENTRY_TIMEOUT_SEC", 120)  # [NEW] Cancel kalau gak fill dalam X detik

# Native Binance OCO (One-Cancels-the-Other): SL/TP disimpan DI EXCHANGE, tetap
# aktif walau bot mati/koneksi putus. Kalau gagal terpasang (versi ccxt beda, dll),
# bot otomatis fallback ke polling-based SL/TP (mekanisme lama) supaya posisi
# tidak pernah dibiarkan tanpa proteksi sama sekali.
USE_NATIVE_OCO_SLTP = env_bool("USE_NATIVE_OCO_SLTP", True)

# --- Break-Even (BE) Protection ---

# --- Daily / Weekly loss limit (circuit breaker) ---
# Begitu rugi terealisasi (net setelah fee) di periode berjalan menyentuh batas ini,
# ENTRY BARU diblokir sampai periode berikutnya (hari/minggu baru, UTC). Posisi yang
# SUDAH terbuka TIDAK dipaksa tutup -- SL/TP/trend-exit tetap jalan seperti biasa.
# Kenapa tidak dipaksa tutup: menutup paksa posisi saat market sedang jelek justru
# bisa mengunci rugi lebih besar daripada membiarkan SL/TP yang sudah direncanakan
# bekerja. 0 = nonaktif (tidak ada limit).
#
# TRADING_MODE testnet/live: dihitung dari saldo riil (equity awal periode vs rugi
# realized dalam QUOTE_ASSET) -- akurat.
# TRADING_MODE off (signal-only): tidak ada saldo untuk dijadikan acuan, jadi dihitung
# dari akumulasi %PnL virtual tiap sinyal yang closed -- pendekatan (mengasumsikan
# ukuran posisi yang kurang lebih sama tiap trade), bukan angka saldo riil.
DAILY_LOSS_LIMIT_PCT = env_float("DAILY_LOSS_LIMIT_PCT", 3.0)
WEEKLY_LOSS_LIMIT_PCT = env_float("WEEKLY_LOSS_LIMIT_PCT", 6.0)

TELEGRAM_ENABLED = env_bool("TELEGRAM_ENABLED", True)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_NOTIFY_ERRORS = env_bool("TELEGRAM_NOTIFY_ERRORS", True)

PORT = env_int("PORT", 0)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger("donal-signal-railway")

# [TESTNET FIX] Binance Testnet gak support native OCO, fallback ke polling SL/TP
if TRADING_MODE == "testnet" and USE_NATIVE_OCO_SLTP:
    log.warning("⚠️ TESTNET MODE: Native OCO tidak didukung di Binance Testnet. Fallback ke polling SL/TP.")
    USE_NATIVE_OCO_SLTP = False

RUNNING = True
_telegram_warned = False
# [PATCH AUDIT] notify_throttled() dan state pendukungnya (_notify_last_time,
# NOTIFY_COOLDOWN_SEC) dihapus: fungsi ini tidak pernah dipanggil di manapun.
# Throttling notifikasi yang benar-benar aktif dipakai adalah notify_error_throttled()
# di bawah, dengan dict cooldown-nya sendiri (_notify_last).



def handle_shutdown(signum, frame):
    global RUNNING
    log.info("Shutdown signal diterima, menyimpan state dan berhenti...")
    RUNNING = False


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


def get_state_path():
    raw = os.getenv("STATE_FILE", "state_signals.json").strip()
    if not raw:
        raw = "state_signals.json"
    p = Path(raw)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        test_file = p.parent / f".write_test_{int(time.time() * 1000)}"
        test_file.write_text("ok")
        test_file.unlink()
        return p
    except Exception as e:
        fallback = Path("/tmp/state_signals.json")
        try:
            fallback.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        log.warning(
            f"State path {raw} tidak writable: {e}. "
            f"Fallback ke {fallback}. "
            f"Jika tidak pakai Railway Volume, state bisa hilang saat restart."
        )
        return fallback


STATE_FILE = get_state_path()
HISTORY_FILE = Path(os.getenv("HISTORY_FILE", "trade_history.json").strip() or "trade_history.json")

exchange = None
VALID_SYMBOLS = []


def start_health_server():
    if PORT <= 0:
        log.info("PORT tidak diset, health server tidak dijalankan.")
        return
    try:
        server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
        log.info(f"Health server listening on port {PORT}")
        server.serve_forever()
    except Exception as e:
        log.warning(f"Health server error: {e}")


# =====================
# UTILS
# =====================
def fmt(x):
    try:
        s = f"{float(x):.12f}".rstrip("0").rstrip(".")
        return s if s else "0"
    except Exception:
        return str(x)


def sleep_interruptible(seconds):
    end = time.time() + seconds
    while RUNNING and time.time() < end:
        time.sleep(1)




# =====================
# TELEGRAM
# =====================
_tg_dedup = {}
_tg_times = []
TG_DEDUP_SEC = 120      # pesan identik dalam 2 menit = spam, drop
TG_MAX_PER_MIN = 6      # maksimal 6 pesan per menit, titik.

def send_telegram(message):
    """Anti-spam di level paling bawah: dedup + global rate limit."""
    global _telegram_warned
    if not TELEGRAM_ENABLED:
        return
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        if not _telegram_warned:
            log.warning(
                "Telegram aktif tapi TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID kosong."
            )
            _telegram_warned = True
        return

    now = time.time()

    # 1) Dedup: pesan identik dalam TG_DEDUP_SEC langsung dibuang.
    key = hashlib.md5(message.encode("utf-8")).hexdigest()
    if now - _tg_dedup.get(key, 0) < TG_DEDUP_SEC:
        log.info("[tg-antispam] duplicate suppressed")
        return
    _tg_dedup[key] = now

    # 2) Global rate limit.
    _tg_times[:] = [t for t in _tg_times if now - t < 60]
    if len(_tg_times) >= TG_MAX_PER_MIN:
        log.warning("[tg-antispam] rate limit hit, suppressed")
        return
    _tg_times.append(now)

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps(
            {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "disable_web_page_preview": True
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log.warning(f"Telegram send failed: {e}")

def notify_event(message):
    log.info(message)
    if TELEGRAM_ENABLED:
        send_telegram(message)


def notify_error(message):
    log.error(message)
    if TELEGRAM_ENABLED and TELEGRAM_NOTIFY_ERRORS:
        send_telegram(f"⚠️ {message}")

# =====================
# ANTI-SPAM NOTIFICATION
# =====================
_notify_last = {}
NOTIFY_ERROR_COOLDOWN_SEC = 300  # 5 menit cooldown buat error yang sama

def notify_error_throttled(key, message):
    """Kirim error ke Telegram tapi dengan cooldown biar gak spam."""
    now = time.time()
    last = _notify_last.get(key, 0)
    if now - last >= NOTIFY_ERROR_COOLDOWN_SEC:
        _notify_last[key] = now
        notify_error(message)
    else:
        log.warning(f"[throttled] {key}: {message}")



# =====================
# EXCHANGE
# =====================
def make_exchange():
    """
    TRADING_MODE=off     -> tidak perlu API key, sama seperti sebelumnya (data publik saja).
    TRADING_MODE=testnet -> pakai BINANCE_TESTNET_API_KEY/SECRET + sandbox mode ccxt.
    TRADING_MODE=live    -> pakai BINANCE_LIVE_API_KEY/SECRET, akun & uang beneran.
    """
    api_key = ""
    api_secret = ""

    if TRADING_MODE == "testnet":
        api_key = BINANCE_TESTNET_API_KEY
        api_secret = BINANCE_TESTNET_API_SECRET
    elif TRADING_MODE == "live":
        api_key = BINANCE_LIVE_API_KEY
        api_secret = BINANCE_LIVE_API_SECRET

    ex = ccxt.binance(
        {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
            },
        }
    )

    if TRADING_MODE == "testnet":
        ex.set_sandbox_mode(True)

    ex.load_markets()
    return ex


# =====================
# STATE
# =====================
def _default_state():
    return {
        "version": 4,
        "last_bar_ts": {},
        "virtual_positions": {},
        "last_buy_alert_bar": {},
        "last_exit_alert_bar": {},
        "entry_intents": {},
        "oco_intents": {},
        "exit_intents": {},
        "risk_tracking": {},
    }


def _normalize_state(data):
    """Validate the persisted state shape without silently accepting bad types."""
    state = _default_state()
    if not isinstance(data, dict):
        raise ValueError("root state harus object/dict")
    state.update(data)
    dict_fields = (
        "last_bar_ts", "virtual_positions", "last_buy_alert_bar",
        "last_exit_alert_bar", "entry_intents", "oco_intents",
        "exit_intents", "risk_tracking",
    )
    for field in dict_fields:
        if not isinstance(state.get(field), dict):
            raise ValueError(f"state.{field} harus object/dict")
    state["version"] = max(int(state.get("version", 1) or 1), 4)
    return state


def load_state():
    state = _default_state()
    if STATE_FILE.exists():
        try:
            state = _normalize_state(json.loads(STATE_FILE.read_text(encoding="utf-8")))
        except Exception as e:
            backup = STATE_FILE.with_name(f"{STATE_FILE.name}.corrupt.{int(time.time())}")
            try:
                STATE_FILE.replace(backup)
                log.error(f"State file invalid/corrupt: {e}. File dipindahkan ke {backup.name}; memakai state baru.")
            except Exception as move_error:
                log.error(f"State file invalid/corrupt: {e}. Gagal backup state: {move_error}")
            state = _default_state()

    state.setdefault("last_bar_ts", {})
    state.setdefault("virtual_positions", {})
    state.setdefault("last_buy_alert_bar", {})
    state.setdefault("last_exit_alert_bar", {})
    state.setdefault("entry_intents", {})
    state.setdefault("oco_intents", {})
    state.setdefault("exit_intents", {})
    state.setdefault("risk_tracking", {})

    for symbol in VALID_SYMBOLS:
        state["last_bar_ts"].setdefault(symbol, 0)
        state["last_buy_alert_bar"].setdefault(symbol, 0)
        state["last_exit_alert_bar"].setdefault(symbol, 0)

    return state


def save_state(state):
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state["version"] = 4
        tmp = STATE_FILE.with_suffix(STATE_FILE.suffix + ".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, STATE_FILE)
    except Exception as e:
        log.error(f"Gagal save state: {e}")


def save_trade_history(symbol, pos, exit_price, reason, pnl_quote_gross=None, pnl_quote_net=None, fees_quote=None):
    """Simpan closed trade dengan gross/net PnL dan estimasi fee yang konsisten."""
    entry = float(pos.get("entry", 0.0))
    qty = float(pos.get("qty") or pos.get("filled_qty") or 1.0)
    exit_price = float(exit_price)
    pnl_gross = (exit_price - entry) * qty
    if pnl_quote_gross is not None:
        pnl_gross = float(pnl_quote_gross)
    if fees_quote is None:
        fees_quote = (entry * qty + exit_price * qty) * TAKER_FEE_PCT / 100.0
    if pnl_quote_net is None:
        pnl_quote_net = pnl_gross - float(fees_quote)
    pnl_pct_gross = (pnl_gross / (entry * qty) * 100.0) if entry > 0 and qty > 0 else 0.0
    pnl_pct_net = (float(pnl_quote_net) / (entry * qty) * 100.0) if entry > 0 and qty > 0 else 0.0

    history_file = HISTORY_FILE
    history = []
    if history_file.exists():
        try:
            loaded = json.loads(history_file.read_text(encoding="utf-8"))
            history = loaded if isinstance(loaded, list) else []
        except (OSError, ValueError, json.JSONDecodeError) as e:
            log.warning(f"Trade history invalid, mulai ulang history: {e}")

    history.append({
        "symbol": symbol,
        "entry": entry,
        "exit": exit_price,
        "qty": qty,
        "pnl_gross": round(pnl_gross, 8),
        "pnl_net": round(float(pnl_quote_net), 8),
        "fees_quote": round(float(fees_quote), 8),
        "pnl": round(float(pnl_quote_net), 8),  # backward-compatible alias = NET
        "pnl_pct_gross": round(pnl_pct_gross, 4),
        "pnl_pct_net": round(pnl_pct_net, 4),
        "pnl_pct": round(pnl_pct_net, 4),  # backward-compatible alias = NET
        "reason": reason,
        "entry_ts": int(pos.get("created_ts") or pos.get("entry_bar_ts") or 0),
        "exit_ts": int(time.time() * 1000),
    })
    history = history[-100:]

    try:
        history_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = history_file.with_suffix(history_file.suffix + ".tmp")
        tmp.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, history_file)
    except OSError as e:
        log.warning(f"Gagal save trade history: {e}")

# =====================
# INDICATORS
# =====================
def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


def rma(series, length):
    return series.ewm(alpha=1 / length, adjust=False).mean()


def rsi(close, length):
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = rma(gain, length)
    avg_loss = rma(loss, length)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_gain / avg_loss
        out = 100 - (100 / (1 + rs))
    return out

def atr(df, length):
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    tr = tr.fillna(high - low)
    return rma(tr, length)


def adx(df, length=14):
    """ADX dihitung pakai fungsi atr() yang udah ada biar efisien."""
    high = df["high"]
    low = df["low"]
    close = df["close"]
    
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    
    tr_rma = atr(df, length)  # Reuse existing atr() function
    plus_dm_rma = rma(pd.Series(plus_dm, index=df.index), length)
    minus_dm_rma = rma(pd.Series(minus_dm, index=df.index), length)
    
    plus_di = 100 * (plus_dm_rma / tr_rma.replace(0, np.nan))
    minus_di = 100 * (minus_dm_rma / tr_rma.replace(0, np.nan))
    
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    adx_val = rma(dx, length)
    
    return adx_val

def find_last_pivots(df, left, right):
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)

    last_high = None
    last_low = None

    start = n - 1 - right
    end = left
    if start < end:
        return last_high, last_low

    for i in range(start, end - 1, -1):
        if last_high is None:
            window_h = highs[i - left: i + right + 1]
            if len(window_h) and highs[i] == window_h.max():
                last_high = float(highs[i])
        if last_low is None:
            window_l = lows[i - left: i + right + 1]
            if len(window_l) and lows[i] == window_l.min():
                last_low = float(lows[i])
        if last_high is not None and last_low is not None:
            break

    return last_high, last_low


# =====================
# DATA
# =====================
def fetch_closed_ohlcv(symbol, timeframe, limit=300):
    tf_ms = exchange.parse_timeframe(timeframe) * 1000
    raw = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    if not raw:
        raise RuntimeError(f"OHLCV kosong untuk {symbol}")

    df = pd.DataFrame(
        raw,
        columns=["ts", "open", "high", "low", "close", "volume"]
    )

    now = int(time.time() * 1000) - (CANDLE_CONFIRM_OFFSET_SEC * 1000)
    df = df[df["ts"] + tf_ms <= now]

    if df.empty:
        raise RuntimeError(f"Belum ada candle closed untuk {symbol}")

    return df.reset_index(drop=True)


# =====================
# HTF TREND CACHE
# =====================
# 4H trend only changes once per HTF candle, so cache it per symbol and only
# refetch when a new HTF candle has actually closed instead of every loop tick.
_htf_trend_cache = {}


def get_htf_bull_trend(symbol):
    tf_ms = exchange.parse_timeframe(HTF_TIMEFRAME) * 1000
    now = int(time.time() * 1000) - (CANDLE_CONFIRM_OFFSET_SEC * 1000)

    cached = _htf_trend_cache.get(symbol)
    if cached is not None and now < cached["expires_at"]:
        return cached["bull_trend"]

    df4h = fetch_closed_ohlcv(symbol, HTF_TIMEFRAME, 100)
    df4h["ema20"] = ema(df4h["close"], 20)
    df4h["ema60"] = ema(df4h["close"], 60)
    df4h["rsi14"] = rsi(df4h["close"], RSI_LENGTH)
    htf = df4h.iloc[-1]

    if pd.isna(htf["ema20"]) or pd.isna(htf["ema60"]) or pd.isna(htf["rsi14"]):
        return None

    bull_trend = bool(htf["ema20"] > htf["ema60"] and htf["rsi14"] > 50)
    bar_ts = int(htf["ts"])
    # Valid until the NEXT HTF candle closes (current bar closes at bar_ts+tf_ms,
    # the one after that at bar_ts+2*tf_ms -- that's when a fresher value exists).
    expires_at = bar_ts + (2 * tf_ms)

    _htf_trend_cache[symbol] = {"bull_trend": bull_trend, "expires_at": expires_at}
    return bull_trend


# =====================
# SIGNAL (Candle Close) - Pine breakoutTrigger
# =====================
def calculate_signal(symbol):
    df1h = fetch_closed_ohlcv(symbol, TIMEFRAME, 300)

    if len(df1h) < 100:
        log.info(f"{symbol}: data candle belum cukup.")
        return None

    # [PATCH AUDIT] rsi()/adx() melakukan .fillna(50.0)/.fillna(0.0) di dalam
    # fungsinya sendiri, sehingga guard NaN di bawah (pada indikator turunan)
    # tidak akan pernah menangkap kasus data candle mentah yang bolong (gap
    # akibat gangguan exchange, pair baru listing, dll) -- nilainya akan
    # terlanjur "disamarkan" jadi netral sebelum sempat dicek. Guard di sini
    # mengecek data mentah dulu, sebelum smoothing indikator terjadi.
    recent_raw = df1h[["close", "high", "low", "volume"]].tail(max(RSI_LENGTH, ADX_LENGTH) + 5)
    if recent_raw.isnull().values.any():
        log.warning(f"{symbol}: ada data candle mentah (close/high/low/volume) yang kosong/NaN, skip sinyal.")
        return None

    df1h["ema20"] = ema(df1h["close"], 20)
    df1h["rsi14"] = rsi(df1h["close"], RSI_LENGTH)
    df1h["hh20_prev"] = df1h["high"].rolling(20).max().shift(1)
    df1h["atr14"] = atr(df1h, ATR_LENGTH)
    if USE_ADX_FILTER:
        df1h["adx"] = adx(df1h, ADX_LENGTH)
    df1h["volume_ma"] = df1h["volume"].rolling(VOLUME_MA_LENGTH).mean()
    bull_trend = get_htf_bull_trend(symbol)
    if bull_trend is None:
        log.info(f"{symbol}: data HTF belum cukup.")
        return None

    row = df1h.iloc[-1]

    tf_ms = exchange.parse_timeframe(TIMEFRAME) * 1000

    required = [
        row["ema20"], row["rsi14"], row["hh20_prev"], row["atr14"],
    ]
    if USE_VOLUME_FILTER:
        required.append(row["volume_ma"])
    if USE_ADX_FILTER:
        required.append(row["adx"])
    if any(pd.isna(x) for x in required):
        log.info(f"{symbol}: indikator masih NaN.")
        return None

    close = float(row["close"])
    atr_val = float(row["atr14"])

    last_pivot_high, last_pivot_low = find_last_pivots(df1h, SR_LEFT_BARS, SR_RIGHT_BARS)

    # breakoutTrigger di Pine: close > ema20 AND rsi14 > rsiEntryLv AND close > hhN
    higher_low_ok = True
    pb_vol_ok = True
    buy_trigger = bool(
    close > row["ema20"]
    and row["rsi14"] > RSI_ENTRY
    and close > row["hh20_prev"]
    )

    room_to_resistance = None
    if last_pivot_high is not None and last_pivot_high > close:
        room_to_resistance = last_pivot_high - close

    res_room_ok = (
        not USE_RES_FILTER
        or room_to_resistance is None
        or room_to_resistance > MIN_ROOM_ATR * atr_val
    )

    volume_ok = True
    volume_ratio = None
    adx_ok = True
    adx_val = None

    if USE_VOLUME_FILTER:
        vol_ma = float(row["volume_ma"])
        if vol_ma > 0:
            volume_ratio = float(row["volume"]) / vol_ma
            volume_ok = volume_ratio > VOLUME_MULT

    if USE_ADX_FILTER:
        adx_val = float(row["adx"])
        adx_ok = adx_val >= ADX_THRESHOLD

