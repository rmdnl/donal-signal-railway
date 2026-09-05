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
MIN_RISK_REWARD = env_float("MIN_RISK_REWARD", 1.0)
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
STRATEGY_MODE = os.getenv("STRATEGY_MODE", "breakout").strip().lower()  # breakout | pullback
STOCH_RSI_LENGTH = env_int("STOCH_RSI_LENGTH", 14)
STOCH_RSI_OS = env_float("STOCH_RSI_OS", 20.0)
PULLBACK_EMA_FAST = env_int("PULLBACK_EMA_FAST", 13)
PULLBACK_EMA_SLOW = env_int("PULLBACK_EMA_SLOW", 34)
VOLUME_MA_LENGTH = env_int("VOLUME_MA_LENGTH", 20)
VOLUME_MULT = env_float("VOLUME_MULT", 1.0)

USE_VOL_SCALED_SLTP = env_bool("USE_VOL_SCALED_SLTP", True)
ATR_MA_LENGTH = env_int("ATR_MA_LENGTH", 50)
VOL_SCALE_MIN = env_float("VOL_SCALE_MIN", 0.8)
VOL_SCALE_MAX = env_float("VOL_SCALE_MAX", 1.5)

MAX_CONCURRENT_POSITIONS = env_int("MAX_CONCURRENT_POSITIONS", 2)
MAX_POSITIONS_PER_GROUP = env_int("MAX_POSITIONS_PER_GROUP", 1)
CORRELATED_GROUPS_RAW = os.getenv("CORRELATED_GROUPS", "BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT")

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

# --- SESSION FILTER (enhancement) ---
SESSION_FILTER_ENABLED = env_bool("SESSION_FILTER_ENABLED", True)
SESSION_START_HOUR = env_int("SESSION_START_HOUR", 8)
SESSION_END_HOUR = env_int("SESSION_END_HOUR", 22)

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

# Risk-based position sizing: qty = (equity * RISK_PCT_PER_TRADE%) / (entry - SL)
RISK_PCT_PER_TRADE = env_float("RISK_PCT_PER_TRADE", 1.0)

# Entry & exit (SL/TP/trend exit) pakai MARKET order -- prioritas kepastian eksekusi
# di atas presisi harga. Karena market order langsung fill (bukan menunggu seperti
# limit order), tidak ada lagi konsep timeout/cancel untuk entry maupun exit.
#
# Konsekuensinya: harga fill bisa meleset dari harga referensi saat sinyal muncul
# (slippage). MAX_ENTRY_SLIPPAGE_PCT adalah guard PRE-TRADE khusus entry -- kalau
# estimasi slippage (bid/ask saat ini vs harga referensi) sudah melebihi batas ini,
# entry DIBATALKAN sebelum order dikirim (0 = nonaktif, selalu entry berapa pun
# slippage-nya). Untuk exit TIDAK ada guard semacam ini -- exit harus selalu jalan
# demi risk management, jadi cuma dilaporkan (bukan dibatalkan) berapa pun besarnya.
MAX_ENTRY_SLIPPAGE_PCT = env_float("MAX_ENTRY_SLIPPAGE_PCT", 0.5)
MAX_ACTUAL_RISK_PCT = env_float("MAX_ACTUAL_RISK_PCT", max(RISK_PCT_PER_TRADE * 1.25, RISK_PCT_PER_TRADE))
RISK_OVERSHOOT_ACTION = os.getenv("RISK_OVERSHOOT_ACTION", "reduce").strip().lower()  # reduce | exit | hold

# Native Binance OCO (One-Cancels-the-Other): SL/TP disimpan DI EXCHANGE, tetap
# aktif walau bot mati/koneksi putus. Kalau gagal terpasang (versi ccxt beda, dll),
# bot otomatis fallback ke polling-based SL/TP (mekanisme lama) supaya posisi
# tidak pernah dibiarkan tanpa proteksi sama sekali.
USE_NATIVE_OCO_SLTP = env_bool("USE_NATIVE_OCO_SLTP", True)

# --- Break-Even (BE) Protection ---
USE_BREAK_EVEN = env_bool("USE_BREAK_EVEN", True)
BE_TRIGGER_PCT = env_float("BE_TRIGGER_PCT", 1.0)   # Geser SL ke BE jika profit >= 1%
BE_OFFSET_PCT = env_float("BE_OFFSET_PCT", 0.15)  # SL baru = Entry + 0.15% (menutupi fee trading)

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

RUNNING = True
_telegram_warned = False
_notify_last_time = {}
NOTIFY_COOLDOWN_SEC = 300  # 5 menit cooldown buat notifikasi yang sama




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


def parse_correlated_groups(raw):
    groups = []
    for chunk in raw.split(";"):
        members = {s.strip().upper() for s in chunk.split(",") if s.strip()}
        if members:
            groups.append(members)
    return groups


CORRELATED_GROUPS = parse_correlated_groups(CORRELATED_GROUPS_RAW)


def symbol_group_index(symbol):
    for idx, group in enumerate(CORRELATED_GROUPS):
        if symbol in group:
            return idx
    return None


# =====================
# HEALTH SERVER
# =====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"DONAL Signal Bot OK")

    def log_message(self, format, *args):
        pass


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


def is_allowed_session(ts_ms):
    if not SESSION_FILTER_ENABLED:
        return True
    dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
    hour = dt.hour
    if SESSION_START_HOUR <= SESSION_END_HOUR:
        return SESSION_START_HOUR <= hour < SESSION_END_HOUR
    else:
        return hour >= SESSION_START_HOUR or hour < SESSION_END_HOUR


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
    return out.fillna(50.0)

def stochastic_rsi(close, length=14, k_smooth=3, d_smooth=3):
    rsi_vals = rsi(close, length)
    lo = rsi_vals.rolling(length).min()
    hi = rsi_vals.rolling(length).max()
    stoch = 100 * (rsi_vals - lo) / (hi - lo).replace(0, np.nan)
    k = stoch.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return k, d


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
    
    return adx_val.fillna(0.0)

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
    df4h["ema13"] = ema(df4h["close"], PULLBACK_EMA_FAST)
    df4h["ema34"] = ema(df4h["close"], PULLBACK_EMA_SLOW)
    df4h["rsi14"] = rsi(df4h["close"], RSI_LENGTH)
    htf = df4h.iloc[-1]

    if pd.isna(htf["ema20"]) or pd.isna(htf["ema60"]) or pd.isna(htf["ema13"]) or pd.isna(htf["ema34"]) or pd.isna(htf["rsi14"]):
        return None

    if STRATEGY_MODE == "pullback":
        bull_trend = bool(htf["ema13"] > htf["ema34"] and htf["rsi14"] > 50)
    else:
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

    df1h["ema20"] = ema(df1h["close"], 20)
    df1h["rsi14"] = rsi(df1h["close"], RSI_LENGTH)
    df1h["hh20_prev"] = df1h["high"].rolling(20).max().shift(1)
    df1h["atr14"] = atr(df1h, ATR_LENGTH)
    if USE_ADX_FILTER:
        df1h["adx"] = adx(df1h, ADX_LENGTH)
    df1h["volume_ma"] = df1h["volume"].rolling(VOLUME_MA_LENGTH).mean()
    df1h["atr_ma"] = df1h["atr14"].rolling(ATR_MA_LENGTH).mean()
    if STRATEGY_MODE == "pullback":
        stoch_k, stoch_d = stochastic_rsi(df1h["close"], STOCH_RSI_LENGTH)
        df1h["stoch_k"] = stoch_k
        df1h["stoch_d"] = stoch_d

    bull_trend = get_htf_bull_trend(symbol)
    if bull_trend is None:
        log.info(f"{symbol}: data HTF belum cukup.")
        return None

    row = df1h.iloc[-1]

    tf_ms = exchange.parse_timeframe(TIMEFRAME) * 1000
    candle_close_ts = int(row["ts"]) + tf_ms
    session_ok = is_allowed_session(candle_close_ts)

    required = [
        row["ema20"], row["rsi14"], row["hh20_prev"], row["atr14"],
    ]
    if USE_VOLUME_FILTER:
        required.append(row["volume_ma"])
    if USE_ADX_FILTER:
        required.append(row["adx"])
    if USE_VOL_SCALED_SLTP:
        required.append(row["atr_ma"])
    if STRATEGY_MODE == "pullback":
        required.append(row["stoch_k"])
        required.append(row["stoch_d"])
    if any(pd.isna(x) for x in required):
        log.info(f"{symbol}: indikator masih NaN.")
        return None

    close = float(row["close"])
    atr_val = float(row["atr14"])

    last_pivot_high, last_pivot_low = find_last_pivots(df1h, SR_LEFT_BARS, SR_RIGHT_BARS)

    if STRATEGY_MODE == "pullback":
        # Pullback: StochRSI cross-up keluar dari oversold = trigger
        prev_k = float(df1h["stoch_k"].iloc[-2])
        prev_d = float(df1h["stoch_d"].iloc[-2])
        cross_up = bool(prev_k <= prev_d and float(row["stoch_k"]) > float(row["stoch_d"]))
        was_oversold = bool(prev_k < STOCH_RSI_OS)
        recent_low = float(df1h["low"].iloc[-10:].min())
        higher_low_ok = (last_pivot_low is None) or (recent_low >= last_pivot_low * 0.995)
        pb_vol_ok = (not USE_VOLUME_FILTER) or bool(float(row["volume"]) > float(df1h["volume"].iloc[-2]))
        buy_trigger = bool(cross_up and was_oversold)
    else:
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

    sl_mult = SL_MULT
    tp_mult = TP_MULT
    vol_scale = 1.0
    if USE_VOL_SCALED_SLTP:
        atr_ma_val = float(row["atr_ma"])
        if atr_ma_val > 0:
            vol_scale = float(np.clip(atr_val / atr_ma_val, VOL_SCALE_MIN, VOL_SCALE_MAX))
            sl_mult = SL_MULT * vol_scale
            tp_mult = TP_MULT * vol_scale

    if STRATEGY_MODE == "pullback":
        buy_signal = bool(bull_trend and buy_trigger and higher_low_ok and pb_vol_ok and session_ok and adx_ok)
    else:
        buy_signal = bool(bull_trend and buy_trigger and res_room_ok and volume_ok and session_ok and adx_ok)

    exit_trend = bool(close < row["ema20"] or row["rsi14"] < RSI_EXIT)

    return {
        "bar_ts": int(row["ts"]),
        "close": close,
        "atr": atr_val,
        "bull_trend": bull_trend,
        "buy": buy_signal,
        "exit_trend": exit_trend,
        "last_pivot_high": last_pivot_high,
        "last_pivot_low": last_pivot_low,
        "room_to_resistance": room_to_resistance,
        "res_room_ok": res_room_ok,
        "volume_ok": volume_ok,
        "volume_ratio": volume_ratio,
        "adx_val": adx_val,
        "adx_ok": adx_ok,
        "sl_mult": sl_mult,
        "tp_mult": tp_mult,
        "vol_scale": vol_scale,
        "session_ok": session_ok,
    }


def should_check_signal(state, symbol):
    last = int(state.get("last_bar_ts", {}).get(symbol, 0) or 0)
    if last == 0:
        return True
    tf_ms = exchange.parse_timeframe(TIMEFRAME) * 1000
    now = int(time.time() * 1000) - (CANDLE_CONFIRM_OFFSET_SEC * 1000)
    return now >= last + tf_ms


def entry_too_old(bar_ts):
    if MAX_ENTRY_DELAY_MINUTES <= 0:
        return False
    tf_ms = exchange.parse_timeframe(TIMEFRAME) * 1000
    close_time = bar_ts + tf_ms
    now = int(time.time() * 1000)
    age_ms = now - close_time
    max_age_ms = MAX_ENTRY_DELAY_MINUTES * 60 * 1000
    return age_ms > max_age_ms


# =====================
# PRICE
# =====================
def get_ticker_price(symbol):
    t = exchange.fetch_ticker(symbol)
    for key in ("last", "bid", "ask"):
        if t.get(key):
            return float(t[key])
    raise RuntimeError(f"Harga ticker kosong untuk {symbol}")


def get_best_bid_ask(symbol):
    t = exchange.fetch_ticker(symbol)
    bid = t.get("bid") or t.get("last")
    ask = t.get("ask") or t.get("last")
    if not bid or not ask:
        raise RuntimeError(f"Bid/ask kosong untuk {symbol}")
    return float(bid), float(ask)


def _binance_symbol(symbol):
    return symbol.replace("/", "").replace(":USDT", "")


def _client_order_id(prefix, symbol, seed):
    # Binance client IDs must be short, deterministic for retries, and contain
    # only safe characters. Determinism is important: if a request times out
    # after Binance accepted it, retrying with the same ID lets reconciliation
    # find the original order instead of creating a second order.
    digest = hashlib.sha1(f"{symbol}|{seed}".encode()).hexdigest()[:24]
    return f"{prefix}{digest}"[:36]


def _raw_private(method_names, params):
    last_error = None
    for name in method_names:
        method = getattr(exchange, name, None)
        if method is None:
            continue
        try:
            return method(params)
        except Exception as exc:
            last_error = exc
            # If the endpoint exists but Binance rejected the request, do not
            # silently try another endpoint shape that could have side effects.
            if not isinstance(exc, (AttributeError, NotImplementedError)):
                raise
    raise RuntimeError(f"Binance raw method unavailable: {method_names}") from last_error


def _normalize_binance_order(order):
    if not isinstance(order, dict):
        return order
    # CCXT unified order fields
    if "filled" in order or "average" in order:
        return order
    return {
        **order,
        "id": str(order.get("orderId")) if order.get("orderId") is not None else order.get("id"),
        "clientOrderId": order.get("clientOrderId"),
        "status": {
            "NEW": "open", "PARTIALLY_FILLED": "open", "FILLED": "closed",
            "CANCELED": "canceled", "REJECTED": "rejected", "EXPIRED": "expired",
        }.get(order.get("status"), order.get("status")),
        "filled": float(order.get("executedQty") or 0.0),
        "remaining": max(float(order.get("origQty") or 0.0) - float(order.get("executedQty") or 0.0), 0.0),
        "average": (
            float(order.get("cummulativeQuoteQty")) / float(order.get("executedQty"))
            if float(order.get("executedQty") or 0.0) > 0 and float(order.get("cummulativeQuoteQty") or 0.0) > 0
            else float(order.get("price") or 0.0)
        ),
    }


def _is_definitive_not_found(exc):
    """True only when the exchange explicitly says the requested object is absent."""
    if isinstance(exc, ccxt.OrderNotFound):
        return True
    text = str(exc).lower()
    info = getattr(exc, "args", None)
    blob = f"{text} {info}".lower()
    return any(code in blob for code in ("-2011", "-2013", "-2018", "unknown order sent", "order does not exist", "order list does not exist", "order not found"))


def lookup_order_by_client_id(symbol, client_order_id):
    """Return (FOUND|NOT_FOUND|UNKNOWN, order).

    UNKNOWN is deliberately different from NOT_FOUND. A timeout/network error must
    never be interpreted as permission to submit a second order.
    """
    if not client_order_id:
        return "NOT_FOUND", None
    params = {"symbol": _binance_symbol(symbol), "origClientOrderId": client_order_id}
    saw_unknown = False
    for name in ("private_get_order", "privateGetOrder"):
        method = getattr(exchange, name, None)
        if method is None:
            continue
        try:
            return "FOUND", _normalize_binance_order(method(params))
        except Exception as exc:
            if _is_definitive_not_found(exc):
                return "NOT_FOUND", None
            saw_unknown = True
            log.warning(f"{symbol}: order lookup {client_order_id} via {name} unknown: {exc}")
            break

    # Only use open/closed order scans when the direct endpoint is unavailable,
    # not after a network failure. This avoids converting UNKNOWN into NOT_FOUND.
    if not saw_unknown:
        for fetch_name in ("fetch_open_orders", "fetch_closed_orders"):
            fetch = getattr(exchange, fetch_name, None)
            if fetch is None:
                continue
            try:
                for order in fetch(symbol):
                    if order.get("clientOrderId") == client_order_id or (order.get("info") or {}).get("clientOrderId") == client_order_id:
                        return "FOUND", _normalize_binance_order(order)
            except Exception as exc:
                saw_unknown = True
                log.warning(f"{symbol}: order scan {client_order_id} unknown: {exc}")
                break
    return ("UNKNOWN", None) if saw_unknown else ("NOT_FOUND", None)


def find_order_by_client_id(symbol, client_order_id):
    """Backward-compatible wrapper. Call lookup_order_by_client_id in safety-critical paths."""
    status, order = lookup_order_by_client_id(symbol, client_order_id)
    return order if status == "FOUND" else None


def lookup_oco_by_client_id(symbol, list_client_order_id):
    """Return (FOUND|NOT_FOUND|UNKNOWN, order-list response)."""
    if not list_client_order_id:
        return "NOT_FOUND", None
    params = {"origClientOrderId": list_client_order_id}  # FIX: endpoint orderList gak terima param symbol (-1104)
    saw_unknown = False
    direct_available = False
    for name in ("private_get_order_list", "privateGetOrderList"):
        method = getattr(exchange, name, None)
        if method is None:
            continue
        direct_available = True
        try:
            return "FOUND", method(params)
        except Exception as exc:
            if _is_definitive_not_found(exc):
                return "NOT_FOUND", None
            saw_unknown = True
            log.warning(f"{symbol}: OCO lookup {list_client_order_id} unknown: {exc}")
            break

    # If the direct endpoint isn't exposed by this CCXT build, scan open lists.
    # Do not scan after a transport/API error because absence cannot be proven.
    if not direct_available and not saw_unknown:
        for name in ("private_get_open_order_list", "privateGetOpenOrderList"):
            method = getattr(exchange, name, None)
            if method is None:
                continue
            try:
                result = method({}) or []
                for item in result:
                    if item.get("listClientOrderId") == list_client_order_id:
                        return "FOUND", item
                return "NOT_FOUND", None
            except Exception as exc:
                saw_unknown = True
                log.warning(f"{symbol}: open OCO list scan unknown: {exc}")
                break
    return ("UNKNOWN", None) if saw_unknown else ("NOT_FOUND", None)


def find_oco_by_client_id(symbol, list_client_order_id):
    status, item = lookup_oco_by_client_id(symbol, list_client_order_id)
    return item if status == "FOUND" else None


# =====================
# AUTO TRADING (Binance API) -- hanya dipakai kalau TRADING_MODE != "off"
# =====================
def get_available_quote(quote_asset=None):
    quote_asset = quote_asset or QUOTE_ASSET
    try:
        balance = exchange.fetch_balance()
        free = None
        if quote_asset in balance and isinstance(balance[quote_asset], dict):
            free = balance[quote_asset].get("free")
        if free is None:
            free = (balance.get("free") or {}).get(quote_asset)
        return float(free or 0.0)
    except Exception as e:
        log.warning(f"Gagal fetch available {quote_asset}: {e}")
        return 0.0


def get_equity(quote_asset=None):
    """Return total quote balance, not only free balance."""
    quote_asset = quote_asset or QUOTE_ASSET
    try:
        balance = exchange.fetch_balance()
        total = None
        if quote_asset in balance and isinstance(balance[quote_asset], dict):
            total = balance[quote_asset].get("total")
        if total is None:
            total = (balance.get("total") or {}).get(quote_asset)
        if total is None:
            return get_available_quote(quote_asset)
        return float(total or 0.0)
    except Exception as e:
        log.warning(f"Gagal fetch total balance {quote_asset}: {e}")
        return 0.0


def compute_sl_tp(signal_data, entry):
    """
    Shared SL/TP calc dipakai baik oleh alert signal-only maupun order auto-trading,
    supaya logikanya selalu sama persis di kedua mode.
    """
    atr_val = float(signal_data.get("atr", 0.0))
    sl_mult = float(signal_data.get("sl_mult", SL_MULT))
    tp_mult = float(signal_data.get("tp_mult", TP_MULT))

    sl = entry - atr_val * sl_mult
    tp = entry + atr_val * tp_mult

    last_pivot_high = signal_data.get("last_pivot_high")
    last_pivot_low = signal_data.get("last_pivot_low")
    structure_used = []

    if USE_STRUCTURE_SLTP:
        if last_pivot_low is not None and last_pivot_low < entry:
            candidate_sl = last_pivot_low - atr_val * SR_BUFFER_ATR
            if candidate_sl < entry:
                sl = candidate_sl
                structure_used.append("SL")
        if last_pivot_high is not None and last_pivot_high > entry:
            candidate_tp = last_pivot_high - atr_val * SR_BUFFER_ATR
            if candidate_tp > entry:
                tp = candidate_tp
                structure_used.append("TP")

    sltp_note = f"Struktur S/R: {', '.join(structure_used)}" if structure_used else "SL/TP: ATR"
    return sl, tp, sltp_note


def calculate_position_size(state, symbol, entry_price, sl_price):
    """
    Risk-based sizing: qty = (equity_quote * RISK_PCT_PER_TRADE%) / (entry - SL).
    Dibatasi presisi & minimum order exchange. Return None kalau tidak valid/tidak cukup.
    """
    if entry_price <= 0 or sl_price <= 0 or sl_price >= entry_price:
        log.warning(f"{symbol}: entry/SL tidak valid untuk sizing (entry={entry_price}, sl={sl_price}).")
        return None

    equity = get_total_equity_quote(state)
    available_quote = get_available_quote(QUOTE_ASSET)
    if equity <= 0 or available_quote <= 0:
        log.warning(f"{symbol}: saldo {QUOTE_ASSET} 0 atau gagal diambil, skip sizing.")
        return None

    risk_amount = equity * RISK_PCT_PER_TRADE / 100.0
    price_risk = entry_price - sl_price
    qty = risk_amount / price_risk

    # Jangan pernah coba belanja lebih dari saldo yang ada, walau risk_amount kecil
    # (bisa terjadi kalau SL sangat dekat ke entry -> qty jadi besar sekali).
    max_affordable_qty = available_quote / (entry_price * (1.0 + TAKER_FEE_PCT / 100.0))
    if qty > max_affordable_qty:
        qty = max_affordable_qty

    market = exchange.markets.get(symbol, {}) if exchange.markets else {}
    limits = market.get("limits", {}) if market else {}
    min_amount = (limits.get("amount") or {}).get("min")
    min_cost = (limits.get("cost") or {}).get("min")

    notional = qty * entry_price
    if min_cost and notional < min_cost:
        log.warning(
            f"{symbol}: notional order ({notional:.4f} {QUOTE_ASSET}) < minNotional exchange "
            f"({min_cost}). Naikkan RISK_PCT_PER_TRADE atau saldo, skip entry."
        )
        return None
    if min_amount and qty < min_amount:
        log.warning(f"{symbol}: qty ({qty}) < minQty exchange ({min_amount}), skip entry.")
        return None

    return qty


def place_entry_order(state, symbol, signal_data, market_price):
    """
    Execute a MARKET BUY with an idempotent client order ID.

    The order intent is persisted BEFORE the request. If the HTTP response is
    lost after Binance accepted the order, restart/retry can reconcile the same
    clientOrderId instead of sending a second BUY. SL/TP are calculated from the
    ACTUAL average fill, not the pre-trade ticker price.
    """
    if market_price is None or market_price <= 0:
        log.warning(f"{symbol}: harga tidak valid, skip entry order.")
        return

    entry_ref = float(signal_data.get("close", 0.0))
    atr_val = float(signal_data.get("atr", 0.0))
    if atr_val <= 0:
        log.warning(f"{symbol}: ATR tidak valid, skip entry order.")
        return

    # Use current ask as the sizing reference and keep a conservative slippage
    # allowance. The final risk is always recomputed from the actual fill below.
    try:
        _, ask = get_best_bid_ask(symbol)
    except Exception:
        ask = float(market_price)
    sl_ref, tp_ref, _ = compute_sl_tp(signal_data, ask)
    if sl_ref <= 0 or sl_ref >= ask or tp_ref <= ask:
        log.warning(f"{symbol}: SL/TP referensi tidak valid (SL={sl_ref}, TP={tp_ref}), skip entry order.")
        return
    ref_rr = (tp_ref - ask) / (ask - sl_ref) if ask > sl_ref else 0.0
    if MIN_RISK_REWARD > 0 and ref_rr < MIN_RISK_REWARD:
        log.info(f"{symbol}: skip entry, R:R referensi {ref_rr:.2f} < minimum {MIN_RISK_REWARD:.2f}.")
        return

    existing_intent_pre = state.get("entry_intents", {}).get(symbol)
    if existing_intent_pre and existing_intent_pre.get("qty_requested"):
        qty = float(existing_intent_pre["qty_requested"])
    else:
        qty = calculate_position_size(state, symbol, ask, sl_ref)
        if qty is None or qty <= 0:
            notify_error(f"{symbol}: gagal hitung position size (saldo/minimum order), BUY dibatalkan.")
            return

    if MAX_ENTRY_SLIPPAGE_PCT > 0:
        est_slippage_pct = (ask - market_price) / market_price * 100.0
        if est_slippage_pct > MAX_ENTRY_SLIPPAGE_PCT:
            notify_error(
                f"{symbol}: BUY dibatalkan -- estimasi slippage {est_slippage_pct:+.2f}% "
                f"melebihi batas {MAX_ENTRY_SLIPPAGE_PCT}% ."
            )
            return

    try:
        qty = float(exchange.amount_to_precision(symbol, qty))
    except Exception as e:
        log.warning(f"{symbol}: gagal apply precision qty entry: {e}")
    if qty <= 0:
        notify_error(f"{symbol}: qty entry menjadi 0 setelah precision, BUY dibatalkan.")
        return

    positions = state.setdefault("virtual_positions", {})
    intents = state.setdefault("entry_intents", {})
    bar_ts = int(signal_data.get("bar_ts", 0))
    client_id = _client_order_id("DONALB", symbol, bar_ts or int(time.time() * 1000))

    # Idempotency guard: if this signal already has an unresolved order intent,
    # reconcile it instead of creating another BUY.
    existing_intent = intents.get(symbol)
    if existing_intent:
        client_id = existing_intent.get("client_order_id") or client_id
        lookup_status, existing = lookup_order_by_client_id(symbol, client_id)
        if lookup_status == "FOUND":
            order = existing
        elif lookup_status == "UNKNOWN":
            log.warning(f"{symbol}: entry intent lookup UNKNOWN ({client_id}); skip duplicate BUY.")
            return
        else:
            # If the intent was persisted before the HTTP request, NOT_FOUND is
            # safe: the request was never sent. If it was already attempted, a
            # successful NOT_FOUND query proves Binance has no such order, so the
            # same deterministic client ID may be submitted again exactly once.
            order = None
    else:
        equity_for_plan = get_total_equity_quote(state)
        planned_risk_quote = max(ask - sl_ref, 0.0) * qty
        intents[symbol] = {
            "client_order_id": client_id,
            "symbol": symbol,
            "qty_requested": qty,
            "created_ts": int(time.time() * 1000),
            "signal_bar_ts": bar_ts,
            "reference_price": float(market_price),
            "planned_risk_quote": planned_risk_quote,
            "planned_risk_pct": (planned_risk_quote / equity_for_plan * 100.0) if equity_for_plan > 0 else None,
            "signal_data": {
                "close": entry_ref, "atr": atr_val,
                "sl_mult": float(signal_data.get("sl_mult", SL_MULT)),
                "tp_mult": float(signal_data.get("tp_mult", TP_MULT)),
                "last_pivot_high": signal_data.get("last_pivot_high"),
                "last_pivot_low": signal_data.get("last_pivot_low"),
                "bar_ts": bar_ts,
            },
        }
        save_state(state)
        order = None

    if order is None:
        # Mark the exact submission attempt before the network call. On a VPS
        # crash after this point, startup recovery knows this request was sent
        # and will reconcile instead of inventing a second order.
        intents[symbol]["attempted_ts"] = int(time.time() * 1000)
        intents[symbol]["state"] = "submitted"
        save_state(state)
        try:
            order = exchange.create_market_buy_order(symbol, qty, {"newClientOrderId": client_id})
        except Exception as e:
            # A timeout is ambiguous. Reconcile by client ID before deciding that
            # the order failed. This is the key duplicate-order protection.
            lookup_status, reconciled = lookup_order_by_client_id(symbol, client_id)
            if lookup_status == "FOUND" and reconciled:
                order = reconciled
                notify_event(f"🔄 {symbol}: BUY response gagal/timeout, tapi order ditemukan via clientOrderId {client_id}.")
            else:
                notify_error(
                    f"{symbol}: BUY gagal dan belum bisa direkonsiliasi [{TRADING_MODE.upper()}]: {e}. "
                    f"Tidak mengirim retry otomatis untuk mencegah duplicate BUY. Intent disimpan: {client_id}."
                )
                return

    avg_price = float(order.get("average") or order.get("price") or 0.0)
    filled_qty = float(order.get("filled") or 0.0)
    order_id = order.get("id")

    if avg_price <= 0 or filled_qty <= 0:
        try:
            if order_id:
                refreshed = exchange.fetch_order(order_id, symbol)
            else:
                refreshed = find_order_by_client_id(symbol, client_id)
            if refreshed:
                avg_price = float(refreshed.get("average") or refreshed.get("price") or avg_price)
                filled_qty = float(refreshed.get("filled") or filled_qty)
                order = refreshed
        except Exception as e:
            log.warning(f"{symbol}: gagal reconcile/fetch BUY {client_id}: {e}")

    requested_qty = float(intents.get(symbol, {}).get("qty_requested") or qty or 0.0)
    # A market order can theoretically be partially filled. Do not leave the
    # remainder as an unprotected live BUY. Cancel the remainder, then protect
    # only the quantity that is actually owned.
    if filled_qty > 0 and requested_qty > 0 and filled_qty < requested_qty * 0.999:
        try:
            if order_id:
                exchange.cancel_order(order_id, symbol)
        except Exception as e:
            log.warning(f"{symbol}: gagal cancel sisa partial BUY {client_id}: {e}")
        try:
            refreshed = exchange.fetch_order(order_id, symbol) if order_id else None
            if refreshed:
                avg_price = float(refreshed.get("average") or avg_price)
                filled_qty = float(refreshed.get("filled") or filled_qty)
                order = refreshed
        except Exception as e:
            log.warning(f"{symbol}: gagal refresh partial BUY {client_id}: {e}")
        notify_error(f"{symbol}: BUY partial fill {filled_qty}/{requested_qty}; sisa order dibatalkan/reconciled sebelum proteksi.")

    if avg_price <= 0 or filled_qty <= 0:
        notify_error(f"{symbol}: BUY order {client_id} belum confirmed FILLED. Intent tetap disimpan, tidak membuat posisi virtual.")
        return

    # IMPORTANT: protection levels use actual fill price.
    sl, tp, sltp_note = compute_sl_tp(signal_data, avg_price)
    if sl <= 0 or sl >= avg_price or tp <= avg_price:
        notify_error(f"{symbol}: SL/TP berdasarkan actual fill tidak valid (fill={avg_price}, SL={sl}, TP={tp}). EXIT SAFETY diperlukan.")
        return
    risk_per_unit = avg_price - sl
    reward_per_unit = tp - avg_price
    rr = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0.0
    if MIN_RISK_REWARD > 0 and rr < MIN_RISK_REWARD:
        # The market order is already filled, so a post-fill RR check must never
        # invent another order. Keep the filled position and protect it normally;
        # the RR value is retained for observability.
        log.warning(f"{symbol}: R:R aktual {rr:.2f} < minimum {MIN_RISK_REWARD:.2f}; posisi tetap diproteksi.")

    realized_slippage_pct = (avg_price - market_price) / market_price * 100.0
    risk_per_unit = max(avg_price - sl, 0.0)
    actual_risk_quote = risk_per_unit * filled_qty
    actual_equity = get_total_equity_quote(state) + (avg_price * filled_qty)
    actual_risk_pct = (actual_risk_quote / actual_equity * 100.0) if actual_equity > 0 else None

    # Enforce a post-fill risk ceiling. A market fill can move far enough from the
    # sizing reference that the intended 1% risk is no longer 1%. We never resize
    # by blindly buying more; if the fill is too risky, use a controlled reduction
    # or exit after the position has been protected.
    risk_breach = bool(actual_risk_pct is not None and MAX_ACTUAL_RISK_PCT > 0 and actual_risk_pct > MAX_ACTUAL_RISK_PCT)

    positions[symbol] = {
        "status": "open",
        "entry": avg_price,
        "entry_ref_close": entry_ref,
        "entry_reference_price": market_price,
        "entry_slippage_pct": realized_slippage_pct,
        "sl": sl,
        "tp": tp,
        "sltp_note": sltp_note,
        "atr": atr_val,
        "qty": filled_qty,
        "filled_qty": filled_qty,
        "entry_order_id": order_id,
        "entry_client_order_id": client_id,
        "entry_bar_ts": bar_ts,
        "created_ts": int(time.time() * 1000),
        "planned_risk_quote": float(intents.get(symbol, {}).get("planned_risk_quote", 0.0) or 0.0),
        "actual_risk_quote": actual_risk_quote,
        "actual_risk_pct": actual_risk_pct,
        "risk_reward": rr,
        "risk_breach": risk_breach,
        "max_actual_risk_pct": MAX_ACTUAL_RISK_PCT,
    }
    intents.pop(symbol, None)

    risk_line = f"Risk aktual: {fmt(actual_risk_quote)} {QUOTE_ASSET}"
    if actual_risk_pct is not None:
        risk_line += f" ({actual_risk_pct:+.3f}% equity)"
    msg = (
        f"🟢 ENTRY FILLED {symbol} [{TRADING_MODE.upper()}] (MARKET)\n"
        f"Harga fill: {fmt(avg_price)} (referensi: {fmt(market_price)})\n"
        f"Slippage entry: {realized_slippage_pct:+.3f}%\n"
        f"Qty: {fmt(filled_qty)}\n"
        f"{risk_line}\n"
    )
    notify_event(msg)

    save_state(state)
    try_place_native_protection(state, symbol)

    if risk_breach:
        pos_after = state.get("virtual_positions", {}).get(symbol)
        if pos_after:
            detail = f"actual risk {actual_risk_pct:.3f}% > max {MAX_ACTUAL_RISK_PCT:.3f}%"
            notify_error(f"{symbol}: POST-FILL RISK BREACH -- {detail}. Action={RISK_OVERSHOOT_ACTION}")
            if pos_after.get("status") == "open_oco" and RISK_OVERSHOOT_ACTION in ("exit", "reduce"):
                if RISK_OVERSHOOT_ACTION == "exit":
                    trigger_exit(state, symbol, "RISK LIMIT EXIT", get_ticker_price(symbol))
                else:
                    risk_per_unit = max(float(pos_after.get("entry", 0.0)) - float(pos_after.get("sl", 0.0)), 0.0)
                    equity_now = get_total_equity_quote(state)
                    max_risk_quote = equity_now * MAX_ACTUAL_RISK_PCT / 100.0 if equity_now > 0 else 0.0
                    target_qty = max_risk_quote / risk_per_unit if risk_per_unit > 0 else 0.0
                    reduce_qty = max(float(pos_after.get("filled_qty", 0.0)) - target_qty, 0.0)
                    if reduce_qty > 0:
                        trigger_exit(state, symbol, "RISK REDUCTION", get_ticker_price(symbol), qty_override=reduce_qty)
                    else:
                        pos_after["risk_breach"] = True
                        save_state(state)
            else:
                pos_after["risk_breach"] = True
                save_state(state)


# =====================
# NATIVE BINANCE OCO (SL/TP tersimpan di exchange, tahan bot restart/offline)
# =====================
def place_oco_exit(symbol, qty, tp_price, sl_stop_price, list_client_order_id=None):
    """Create a Binance Spot OCO using the current orderList/oco endpoint.

    We intentionally use Binance's native order-list endpoint instead of trying to
    emulate OCO with a normal LIMIT order carrying stopPrice. The response is
    validated to contain a list ID and both child order IDs.
    """
    list_client_order_id = list_client_order_id or _client_order_id(
        "DONALO", symbol, f"{qty}|{tp_price}|{sl_stop_price}"
    )
    above_client_id = _client_order_id("DONALT", symbol, list_client_order_id)
    below_client_id = _client_order_id("DONALS", symbol, f"{list_client_order_id}|SL")

    params = {
        "symbol": _binance_symbol(symbol),
        "side": "SELL",
        "quantity": str(qty),
        "aboveType": "LIMIT_MAKER",
        "abovePrice": str(tp_price),
        "aboveClientOrderId": above_client_id,
        "belowType": "STOP_LOSS",
        "belowStopPrice": str(sl_stop_price),
        "belowClientOrderId": below_client_id,
        "listClientOrderId": list_client_order_id,
        "newOrderRespType": "RESULT",
    }

    response = _raw_private(("private_post_order_list_oco", "privatePostOrderListOco"), params)
    info = response.get("info", response) if isinstance(response, dict) else {}
    order_list_id = info.get("orderListId") or response.get("orderListId")
    reports = info.get("orderReports") or response.get("orderReports") or []
    orders = info.get("orders") or response.get("orders") or []

    tp_order_id = None
    sl_order_id = None
    for leg in reports:
        leg_type = (leg.get("type") or "").upper()
        leg_id = leg.get("orderId") or leg.get("id")
        if leg_id is None:
            continue
        if "STOP" in leg_type:
            sl_order_id = leg_id
        else:
            tp_order_id = tp_order_id or leg_id
    if not tp_order_id or not sl_order_id:
        for leg in orders:
            leg_id = leg.get("orderId") or leg.get("id")
            client_id = leg.get("clientOrderId")
            if client_id == above_client_id:
                tp_order_id = tp_order_id or leg_id
            elif client_id == below_client_id:
                sl_order_id = sl_order_id or leg_id

    if not order_list_id or not tp_order_id or not sl_order_id:
        raise RuntimeError(
            f"OCO response tidak lengkap: list={order_list_id}, tp={tp_order_id}, sl={sl_order_id}"
        )

    return {
        "order_list_id": order_list_id,
        "tp_order_id": tp_order_id,
        "sl_order_id": sl_order_id,
        "list_client_order_id": list_client_order_id,
        "tp_client_order_id": above_client_id,
        "sl_client_order_id": below_client_id,
    }


def cancel_oco_exit(symbol, order_list_id):
    if not order_list_id:
        return None
    params = {"symbol": _binance_symbol(symbol), "orderListId": int(order_list_id)}
    return _raw_private(("private_delete_order_list", "privateDeleteOrderList"), params)


def _apply_oco_to_position(pos, oco):
    pos["status"] = "open_oco"
    pos["oco_order_list_id"] = oco["order_list_id"]
    pos["oco_tp_order_id"] = oco["tp_order_id"]
    pos["oco_sl_order_id"] = oco["sl_order_id"]
    pos["oco_list_client_order_id"] = oco.get("list_client_order_id")
    pos["oco_tp_client_order_id"] = oco.get("tp_client_order_id")
    pos["oco_sl_client_order_id"] = oco.get("sl_client_order_id")


def _extract_oco_child_ids(symbol, oco_response, intent=None):
    info = oco_response.get("info", oco_response) if isinstance(oco_response, dict) else {}
    reports = info.get("orderReports") or oco_response.get("orderReports") or []
    orders = info.get("orders") or oco_response.get("orders") or []
    legs = reports + orders
    tp_id = sl_id = None
    for leg in legs:
        leg_type = (leg.get("type") or "").upper()
        leg_id = leg.get("orderId") or leg.get("id")
        cid = leg.get("clientOrderId")
        is_stop_client = bool(intent and cid == intent.get("sl_client_order_id"))
        if "STOP" in leg_type or is_stop_client:
            sl_id = sl_id or leg_id
        elif leg_id:
            tp_id = tp_id or leg_id

    # Query each child when the order-list endpoint returns only IDs (which is
    # normal for orderList status queries). This makes restart reconciliation
    # independent of whether the response included orderReports.
    if (tp_id is None or sl_id is None) and orders:
        for leg in orders:
            leg_id = leg.get("orderId") or leg.get("id")
            if not leg_id:
                continue
            try:
                child = exchange.fetch_order(str(leg_id), symbol)
            except Exception:
                continue
            child_type = (child.get("type") or (child.get("info") or {}).get("type") or "").upper()
            if "STOP" in child_type:
                sl_id = sl_id or leg_id
            else:
                tp_id = tp_id or leg_id
    return info.get("orderListId") or oco_response.get("orderListId"), tp_id, sl_id


class OcoPreflightError(RuntimeError):
    pass


def validate_oco_prices(symbol, tp_price, sl_stop_price):
    """Preflight native SELL OCO against current book so crossed prices fail safely."""
    bid, ask = get_best_bid_ask(symbol)
    if tp_price <= ask:
        raise OcoPreflightError(f"TP {tp_price} sudah marketable/ter-crossed terhadap ask {ask}")
    if sl_stop_price >= bid:
        raise OcoPreflightError(f"SL {sl_stop_price} sudah terpicu/ter-crossed terhadap bid {bid}")
    return bid, ask


def mark_protection_unknown(state, symbol, reason):
    pos = state.get("virtual_positions", {}).get(symbol)
    if not pos:
        return
    pos["status"] = "protection_unknown"
    pos["protection_reconciliation_required"] = True
    pos["protection_unknown_since"] = pos.get("protection_unknown_since") or int(time.time() * 1000)
    save_state(state)
    notify_error(f"{symbol}: PROTECTION UNKNOWN: {reason}. Tidak ada blind retry/duplicate SELL.")


def try_place_native_protection(state, symbol):
    """
    Create/reconcile exactly one native OCO. The OCO intent is persisted before
    the API call. If the response is lost, the same listClientOrderId is queried
    before any retry, preventing duplicate protective orders.
    """
    positions = state.get("virtual_positions", {})
    pos = positions.get(symbol)
    if not pos:
        return

    if not USE_NATIVE_OCO_SLTP:
        pos["status"] = "open"
        state.setdefault("oco_intents", {}).pop(symbol, None)
        save_state(state)
        return

    qty = float(pos.get("filled_qty", 0.0))
    tp = float(pos.get("tp", 0.0))
    sl = float(pos.get("sl", 0.0))
    if qty <= 0 or tp <= 0 or sl <= 0:
        pos["status"] = "open"
        notify_error(f"{symbol}: qty/SL/TP tidak valid untuk OCO, fallback polling.")
        save_state(state)
        return

    intents = state.setdefault("oco_intents", {})
    intent = intents.get(symbol)
    created_new_intent = intent is None
    list_client_id = intent.get("list_client_order_id") if intent else None
    if not list_client_id:
        list_client_id = _client_order_id("DONALO", symbol, pos.get("entry_client_order_id") or pos.get("created_ts"))
        intent = {
            "list_client_order_id": list_client_id,
            "created_ts": int(time.time() * 1000),
            "qty": qty,
            "tp": tp,
            "sl": sl,
            "attempted_ts": None,
            "state": "prepared",
        }
        intents[symbol] = intent
        pos["status"] = "oco_pending"
        save_state(state)

    # First reconcile an already accepted OCO.
    oco_lookup_status, existing = lookup_oco_by_client_id(symbol, list_client_id)
    if oco_lookup_status == "UNKNOWN":
        pos["status"] = "protection_unknown"
        pos["protection_reconciliation_required"] = True
        save_state(state)
        notify_error(f"{symbol}: OCO lookup UNKNOWN untuk {list_client_id}; tidak membuat duplicate OCO.")
        return
    if existing:
        order_list_id, tp_id, sl_id = _extract_oco_child_ids(symbol, existing, intent)
        if order_list_id and tp_id and sl_id:
            _apply_oco_to_position(pos, {
                "order_list_id": order_list_id,
                "tp_order_id": tp_id,
                "sl_order_id": sl_id,
                "list_client_order_id": list_client_id,
                "tp_client_order_id": intent.get("tp_client_order_id") if intent else None,
                "sl_client_order_id": intent.get("sl_client_order_id") if intent else None,
            })
            intents.pop(symbol, None)
            save_state(state)
            return

    # If the exchange has definitively confirmed that this exact listClientId does
    # not exist, the previous attempt was not accepted (or is no longer a live
    # order-list). It is now safe to mint a NEW intent ID and try once again. This
    # is deliberately different from UNKNOWN, where no new OCO is ever submitted.
    if not created_new_intent and intent.get("attempted_ts") and oco_lookup_status == "NOT_FOUND":
        intents.pop(symbol, None)
        intent = None
        created_new_intent = True
        list_client_id = _client_order_id("DONALO", symbol, f"{pos.get('entry_client_order_id')}|rearm|{int(time.time()*1000)}")
        intent = {
            "list_client_order_id": list_client_id,
            "created_ts": int(time.time() * 1000),
            "qty": qty, "tp": tp, "sl": sl,
            "attempted_ts": None, "state": "prepared",
        }
        intents[symbol] = intent
        pos["status"] = "oco_pending"
        save_state(state)

    # An existing intent with a prior submission that is still unresolved is
    # never submitted again. UNKNOWN remains UNKNOWN until the exchange can be
    # queried successfully.
    if not created_new_intent and intent.get("attempted_ts"):
        mark_protection_unknown(state, symbol, f"previous OCO submission unresolved: {list_client_id}")
        return

    try:
        tp_p = float(exchange.price_to_precision(symbol, tp))
        sl_p = float(exchange.price_to_precision(symbol, sl))
        qty_p = float(exchange.amount_to_precision(symbol, qty))
        validate_oco_prices(symbol, tp_p, sl_p)
        intent["attempted_ts"] = int(time.time() * 1000)
        intent["state"] = "submitted"
        intent["qty"] = qty_p
        intent["tp"] = tp_p
        intent["sl"] = sl_p
        # Persist the exact submission intent BEFORE touching Binance.
        save_state(state)
        oco = place_oco_exit(symbol, qty_p, tp_p, sl_p, list_client_id)
        _apply_oco_to_position(pos, oco)
        intents.pop(symbol, None)
        save_state(state)
        notify_event(
            f"🛡️ OCO PROTECTION AKTIF {symbol} [{TRADING_MODE.upper()}]\n"
            f"TP: {fmt(tp_p)} | SL trigger: {fmt(sl_p)}\n"
            f"Order List ID: {oco['order_list_id']}\n"
            f"Proteksi aktif DI EXCHANGE."
        )
    except Exception as e:
        # Never blindly retry. The request may have succeeded even if the client
        # saw a timeout/error. Reconcile once more using the same client ID.
        oco_lookup_status, reconciled = lookup_oco_by_client_id(symbol, list_client_id)
        if oco_lookup_status == "UNKNOWN":
            mark_protection_unknown(state, symbol, f"OCO submission/reconciliation error: {e}")
            return
        if reconciled:
            log.warning(f"{symbol}: OCO request error tetapi order-list ditemukan; reconcile tanpa retry.")
            order_list_id, tp_id, sl_id = _extract_oco_child_ids(symbol, reconciled, intent)
            if order_list_id and tp_id and sl_id:
                _apply_oco_to_position(pos, {
                    "order_list_id": order_list_id,
                    "tp_order_id": tp_id,
                    "sl_order_id": sl_id,
                    "list_client_order_id": list_client_id,
                })
                intents.pop(symbol, None)
                save_state(state)
                return
            mark_protection_unknown(state, symbol, "OCO ditemukan tetapi child IDs tidak lengkap")
            return

        # At this point the exchange has explicitly confirmed the OCO list is
        # absent. For a deterministic preflight/invalid-order failure we can
        # safely abandon the intent and flatten the just-opened position instead
        # of leaving it naked. This is NOT used when lookup itself is UNKNOWN.
        if oco_lookup_status == "NOT_FOUND" and isinstance(e, (OcoPreflightError, ccxt.InvalidOrder)):
            intents.pop(symbol, None)
            pos["status"] = "open"
            pos["protection_reconciliation_required"] = False
            save_state(state)
            try:
                emergency_price = get_ticker_price(symbol)
                place_exit_order(state, symbol, "OCO PREFLIGHT/INVALID EXIT", emergency_price)
            except Exception as exit_error:
                mark_protection_unknown(state, symbol, f"OCO absent but emergency exit failed: {exit_error}")
            return

        # Definitively absent but unexpected exchange failure: keep the intent as
        # a recoverable protection problem. Do not blindly submit a new OCO.
        mark_protection_unknown(state, symbol, f"OCO request failed after confirmed absence: {e}")


def _is_dust_remainder(symbol, qty):
    """Return True only when a remainder is below the exchange minimum amount."""
    if qty <= 0:
        return True
    market = exchange.markets.get(symbol, {}) if getattr(exchange, "markets", None) else {}
    min_amount = ((market.get("limits", {}).get("amount") or {}).get("min")) if market else None
    if min_amount:
        return qty < float(min_amount) * 1.001
    return qty < 1e-12


def process_open_oco_position(state, symbol):
    """Reconcile child order fills and recover cleanly after bot/VPS restart."""
    positions = state.get("virtual_positions", {})
    pos = positions.get(symbol)
    if not pos:
        return

    sl_id = pos.get("oco_sl_order_id")
    tp_id = pos.get("oco_tp_order_id")
    qty_target = float(pos.get("filled_qty", 0.0))
    if not sl_id and not tp_id:
        try_place_native_protection(state, symbol)
        return

    try:
        sl_order = exchange.fetch_order(sl_id, symbol) if sl_id else None
        tp_order = exchange.fetch_order(tp_id, symbol) if tp_id else None
    except Exception as e:
        log.warning(f"{symbol}: gagal cek status OCO order: {e}")
        return

    sl_filled_qty = float(sl_order.get("filled") or 0.0) if sl_order else 0.0
    tp_filled_qty = float(tp_order.get("filled") or 0.0) if tp_order else 0.0
    sl_filled = bool(sl_order and sl_filled_qty > 0 and _is_dust_remainder(symbol, max(qty_target - sl_filled_qty, 0.0)))
    tp_filled = bool(tp_order and tp_filled_qty > 0 and _is_dust_remainder(symbol, max(qty_target - tp_filled_qty, 0.0)))

    if sl_filled:
        sl_ref = float(pos.get("sl", 0.0))
        avg_price = float(sl_order.get("average") or sl_order.get("price") or sl_ref)
        slippage_pct = (avg_price - sl_ref) / sl_ref * 100.0 if sl_ref else None
        finalize_exit(state, symbol, "SL HIT (native OCO)", avg_price, slippage_pct=slippage_pct)
        return
    if tp_filled:
        tp_ref = float(pos.get("tp", 0.0))
        avg_price = float(tp_order.get("average") or tp_order.get("price") or tp_ref)
        slippage_pct = (avg_price - tp_ref) / tp_ref * 100.0 if tp_ref else None
        finalize_exit(state, symbol, "TP HIT (native OCO)", avg_price, slippage_pct=slippage_pct)
        return

    partial_filled = max(sl_filled_qty, tp_filled_qty)
    if partial_filled > 0 and not _is_dust_remainder(symbol, max(qty_target - partial_filled, 0.0)):
        # If one leg has filled, Binance normally cancels the other leg. Only
        # cancel the list when it is still non-terminal. A transport error during
        # cancellation is UNKNOWN and therefore blocks replacement.
        terminal_statuses = {"canceled", "expired", "rejected", "closed"}
        sl_terminal = bool(sl_order and sl_order.get("status") in terminal_statuses)
        tp_terminal = bool(tp_order and tp_order.get("status") in terminal_statuses)
        old_list_id = pos.get("oco_order_list_id")
        if not (sl_terminal and tp_terminal):
            try:
                if old_list_id:
                    cancel_oco_exit(symbol, old_list_id)
            except ccxt.OrderNotFound:
                pass
            except Exception as e:
                mark_protection_unknown(state, symbol, f"partial OCO fill tetapi cancel order-list lama UNKNOWN: {e}")
                return
        remaining = max(qty_target - partial_filled, 0.0)
        pos["filled_qty"] = remaining
        pos["qty"] = remaining
        for key in ("oco_order_list_id", "oco_tp_order_id", "oco_sl_order_id",
                    "oco_list_client_order_id", "oco_tp_client_order_id", "oco_sl_client_order_id"):
            pos.pop(key, None)
        pos["status"] = "open"
        pos["protection_reconciliation_required"] = False
        state.setdefault("oco_intents", {}).pop(symbol, None)
        save_state(state)
        notify_error(f"{symbol}: OCO partial fill {partial_filled}/{qty_target}. Sisa {remaining} direkonsiliasi dan diproteksi ulang.")
        try_place_native_protection(state, symbol)
        return

    # If both child orders are canceled/expired without a fill, the OCO is no
    # longer protecting the position. Clear stale IDs and create a new intent on
    # the next protection pass instead of treating the old OCO as active.
    terminal = {"canceled", "expired", "rejected"}
    if sl_order and tp_order and sl_order.get("status") in terminal and tp_order.get("status") in terminal:
        for key in ("oco_order_list_id", "oco_tp_order_id", "oco_sl_order_id",
                    "oco_list_client_order_id", "oco_tp_client_order_id", "oco_sl_client_order_id"):
            pos.pop(key, None)
        pos["status"] = "open"
        pos["protection_reconciliation_required"] = False
        state.setdefault("oco_intents", {}).pop(symbol, None)
        save_state(state)
        try_place_native_protection(state, symbol)


def place_exit_order(state, symbol, reason, price, qty_override=None):
    """Idempotent MARKET SELL with persisted clientOrderId + reconciliation.

    qty_override is used only for a controlled risk reduction. A full close keeps
    the same semantics as before. Every exit quantity gets its own deterministic
    client ID so a timeout can never cause a second SELL.
    """
    positions = state.get("virtual_positions", {})
    pos = positions.get(symbol)
    if not pos or pos.get("status") != "open":
        return

    position_qty = float(pos.get("filled_qty") or pos.get("qty") or 0.0)
    if position_qty <= 0:
        log.warning(f"{symbol}: qty exit tidak valid ({position_qty}), skip exit order.")
        return

    requested_qty = position_qty if qty_override is None else min(float(qty_override), position_qty)
    if requested_qty <= 0:
        return
    try:
        qty_p = float(exchange.amount_to_precision(symbol, requested_qty))
    except Exception as e:
        log.warning(f"{symbol}: gagal apply precision qty exit: {e}")
        qty_p = requested_qty
    if qty_p <= 0:
        notify_error(f"{symbol}: qty exit menjadi 0 setelah precision, SELL dibatalkan.")
        return

    full_close = qty_p >= position_qty * 0.999
    intents = state.setdefault("exit_intents", {})
    intent = intents.get(symbol)
    if intent:
        client_id = intent.get("client_order_id")
        requested_qty = float(intent.get("qty") or qty_p)
        full_close = bool(intent.get("full_close", full_close))
    else:
        client_id = _client_order_id(
            "DONALX", symbol, f"{pos.get('entry_client_order_id')}|{reason}|{qty_p}"
        )
        intents[symbol] = {
            "client_order_id": client_id,
            "reason": reason,
            "qty": qty_p,
            "full_close": full_close,
            "created_ts": int(time.time() * 1000),
        }
        save_state(state)

    lookup_status, existing = lookup_order_by_client_id(symbol, client_id)
    if lookup_status == "UNKNOWN":
        notify_error(f"{symbol}: existing SELL intent lookup UNKNOWN; tidak membuat duplicate SELL.")
        return
    order = existing
    if order is None:
        try:
            order = exchange.create_market_sell_order(symbol, qty_p, {"newClientOrderId": client_id})
        except Exception as e:
            lookup_status, reconciled = lookup_order_by_client_id(symbol, client_id)
            if lookup_status == "FOUND" and reconciled:
                order = reconciled
                notify_event(f"🔄 {symbol}: SELL response gagal/timeout, order ditemukan via clientOrderId {client_id}.")
            elif lookup_status == "UNKNOWN":
                notify_error(f"{symbol}: SELL response ambiguous dan reconciliation UNKNOWN. Intent disimpan; tidak retry.")
                return
            else:
                notify_error(
                    f"{symbol}: GAGAL SELL [{TRADING_MODE.upper()}]: {e}. "
                    f"Tidak retry otomatis. Intent={client_id}."
                )
                return

    avg_price = float(order.get("average") or order.get("price") or 0.0)
    filled_qty = float(order.get("filled") or 0.0)
    order_id = order.get("id")
    if avg_price <= 0 or filled_qty <= 0:
        try:
            refreshed = exchange.fetch_order(order_id, symbol) if order_id else None
            if refreshed:
                avg_price = float(refreshed.get("average") or refreshed.get("price") or avg_price)
                filled_qty = float(refreshed.get("filled") or filled_qty)
                order = refreshed
        except Exception as e:
            log.warning(f"{symbol}: gagal fetch ulang exit order {client_id}: {e}")

    if filled_qty <= 0 or avg_price <= 0:
        notify_error(f"{symbol}: SELL {client_id} belum confirmed FILLED. Posisi tetap tercatat; tidak membuat exit kedua.")
        return

    # For partial exits, the PnL of the executed slice must be recorded now, and
    # the remaining position stays open with the same original entry.
    remaining = max(position_qty - filled_qty, 0.0)
    requested_filled = _is_dust_remainder(symbol, max(requested_qty - filled_qty, 0.0))
    if full_close and requested_filled:
        reference_price = float(price) if price else avg_price
        slippage_pct = (avg_price - reference_price) / reference_price * 100.0 if reference_price else 0.0
        intents.pop(symbol, None)
        finalize_exit(state, symbol, reason, avg_price, exit_qty=filled_qty, slippage_pct=slippage_pct)
        return

    # Partial execution or intentional risk reduction. The executed slice is a
    # closed trade fragment, while the remaining asset stays protected.
    partial_pos = dict(pos)
    partial_pos["qty"] = filled_qty
    partial_pos["filled_qty"] = filled_qty
    reference_price = float(price) if price else avg_price
    slippage_pct = (avg_price - reference_price) / reference_price * 100.0 if reference_price else 0.0
    record_partial_exit(state, symbol, partial_pos, avg_price, reason, slippage_pct=slippage_pct)

    intents.pop(symbol, None)
    if _is_dust_remainder(symbol, remaining):
        positions.pop(symbol, None)
        save_state(state)
        return

    pos["filled_qty"] = remaining
    pos["qty"] = remaining
    remaining_entry = float(pos.get("entry", 0.0))
    remaining_sl = float(pos.get("sl", 0.0))
    remaining_risk = max(remaining_entry - remaining_sl, 0.0) * remaining
    remaining_equity = get_total_equity_quote(state)
    pos["actual_risk_quote"] = remaining_risk
    pos["actual_risk_pct"] = (remaining_risk / remaining_equity * 100.0) if remaining_equity > 0 else None
    pos["risk_breach"] = bool(pos["actual_risk_pct"] is not None and MAX_ACTUAL_RISK_PCT > 0 and pos["actual_risk_pct"] > MAX_ACTUAL_RISK_PCT)
    # The old OCO was canceled before this manual exit. Re-arm protection for the
    # remainder with a fresh deterministic OCO intent.
    save_state(state)
    try_place_native_protection(state, symbol)
    notify_event(
        f"↪️ {symbol}: SELL partial {fmt(filled_qty)}/{fmt(position_qty)}. "
        f"Sisa posisi {fmt(remaining)} diproteksi ulang."
    )


def record_partial_exit(state, symbol, pos_slice, exit_price, reason, slippage_pct=None):
    """Record one executed exit slice without deleting the remaining position."""
    entry = float(pos_slice.get("entry", 0.0))
    qty = float(pos_slice.get("filled_qty") or pos_slice.get("qty") or 0.0)
    exit_price = float(exit_price)
    if entry <= 0 or qty <= 0:
        return
    pnl_gross = (exit_price - entry) * qty
    fees_quote = (entry * qty + exit_price * qty) * TAKER_FEE_PCT / 100.0
    pnl_net = pnl_gross - fees_quote
    pnl_pct_net = (pnl_net / (entry * qty) * 100.0) if entry > 0 else 0.0
    save_trade_history(
        symbol, pos_slice, exit_price, reason,
        pnl_quote_gross=pnl_gross, pnl_quote_net=pnl_net, fees_quote=fees_quote,
    )
    record_realized_pnl(state, pnl_pct_net, pnl_quote=pnl_net)
    save_state(state)


def finalize_exit(state, symbol, reason, exit_price, exit_qty=None, slippage_pct=None):
    positions = state.get("virtual_positions", {})
    pos = positions.get(symbol)
    if not pos:
        return

    entry = float(pos.get("entry", 0.0))
    qty = float(exit_qty if exit_qty is not None else (pos.get("filled_qty") or pos.get("qty") or 0.0))
    exit_price = float(exit_price)
    pnl = (exit_price - entry) * qty
    pnl_pct_gross = ((exit_price - entry) / entry * 100.0) if entry > 0 else 0.0
    # Fee is calculated on both executed legs, so net PnL is quote-accurate rather
    # than an approximation of gross percentage minus a fixed round-trip rate.
    fees_quote = (entry * qty + exit_price * qty) * TAKER_FEE_PCT / 100.0 if entry > 0 and qty > 0 else 0.0
    pnl_quote_net = pnl - fees_quote
    pnl_pct_net = (pnl_quote_net / (entry * qty) * 100.0) if entry > 0 and qty > 0 else 0.0

    # Simpan ke trade history dengan gross/net dan fee yang konsisten.
    save_trade_history(
        symbol, pos, exit_price, reason,
        pnl_quote_gross=pnl,
        pnl_quote_net=pnl_quote_net,
        fees_quote=fees_quote,
    )
    
    positions.pop(symbol, None)
    record_realized_pnl(state, pnl_pct_net, pnl_quote=pnl_quote_net)
    
    # --- PATCH KEAMANAN: Simpan state segera setelah exit ---
    save_state(state)
    # -------------------------------------------------------

    result_emoji = "🟢" if pnl_pct_net >= 0 else "🔴"
    mode_note = f" [{TRADING_MODE.upper()}]" if TRADING_MODE != "off" else ""
    slippage_line = f"\nSlippage exit: {slippage_pct:+.3f}%" if slippage_pct is not None else ""

    msg = (
        f"{result_emoji} {reason} {symbol}{mode_note}\n"
        f"Strategy: DONAL 4H Trend 1H Breakout\n"
        f"Entry: {fmt(entry)}\n"
        f"Exit: {fmt(exit_price)}"
        f"{slippage_line}\n"
        f"Selisih: {fmt(pnl)}\n"
        f"PnL gross: {pnl_pct_gross:+.2f}%\n"
        f"PnL net (setelah fee {ROUND_TRIP_FEE_PCT:.2f}%): {pnl_pct_net:+.2f}%"
    )
    notify_event(msg)


def trigger_entry(state, symbol, signal_data, market_price):
    if TRADING_MODE == "off":
        send_buy_alert(state, symbol, signal_data, market_price)
    else:
        place_entry_order(state, symbol, signal_data, market_price)


def trigger_exit(state, symbol, reason, price, qty_override=None):
    positions = state.get("virtual_positions", {})
    pos = positions.get(symbol)

    if TRADING_MODE == "off" or not pos or "status" not in pos:
        send_exit_alert(state, symbol, reason, price)
        return

    if pos.get("status") in ("oco_pending", "protection_unknown") or pos.get("protection_reconciliation_required") or symbol in state.get("oco_intents", {}):
        # An OCO submission may have reached Binance even if the client did not
        # receive the response. Never market-sell until the contingent order is
        # proven absent/canceled or proven filled.
        try_place_native_protection(state, symbol)
        pos = state.get("virtual_positions", {}).get(symbol)
        if not pos:
            return
        if pos.get("status") in ("oco_pending", "protection_unknown"):
            notify_error(f"{symbol}: exit {reason} ditahan karena status OCO belum pasti. Tidak ada duplicate SELL.")
            return

    if pos.get("status") == "open_oco":
        order_list_id = pos.get("oco_order_list_id")
        cancel_ok = False
        try:
            if order_list_id:
                cancel_oco_exit(symbol, order_list_id)
            cancel_ok = True
        except Exception as e:
            # Cancellation can race with an OCO fill. Reconcile BEFORE sending a
            # market SELL, otherwise a filled SL/TP could be followed by a duplicate SELL.
            log.warning(f"{symbol}: cancel OCO returned error, reconciling before manual exit: {e}")
            process_open_oco_position(state, symbol)
            if symbol not in state.get("virtual_positions", {}):
                return

        if not cancel_ok:
            pos = state.get("virtual_positions", {}).get(symbol)
            if pos and pos.get("status") == "open_oco":
                notify_error(
                    f"{symbol}: OCO masih aktif/tidak pasti setelah cancel failure; manual exit dibatalkan "
                    f"untuk mencegah duplicate SELL. OrderList={pos.get('oco_order_list_id')}"
                )
                return

        # Binance confirmed the order-list cancellation, so it is now safe to
        # replace the contingent exit with a single idempotent market SELL.
        pos = state.get("virtual_positions", {}).get(symbol)
        if not pos:
            return
        pos["status"] = "open"
        for key in ("oco_order_list_id", "oco_tp_order_id", "oco_sl_order_id",
                    "oco_list_client_order_id", "oco_tp_client_order_id", "oco_sl_client_order_id"):
            pos.pop(key, None)
        state.setdefault("oco_intents", {}).pop(symbol, None)
        save_state(state)

    place_exit_order(state, symbol, reason, price, qty_override=qty_override)


# =====================
# ALERTS
# =====================
def send_buy_alert(state, symbol, signal_data, market_price=None):
    entry_ref = float(signal_data.get("close", 0.0))
    if market_price is None:
        try:
            market_price = get_ticker_price(symbol)
        except Exception:
            market_price = entry_ref

    entry = float(market_price)
    atr_val = float(signal_data.get("atr", 0.0))

    if entry <= 0 or atr_val <= 0:
        log.warning(f"{symbol}: entry atau ATR tidak valid, skip BUY alert.")
        return

    vol_scale = float(signal_data.get("vol_scale", 1.0))
    sl, tp, sltp_note = compute_sl_tp(signal_data, entry)

    state.setdefault("virtual_positions", {})[symbol] = {
        "status": "open",
        "entry": entry,
        "entry_ref_close": entry_ref,
        "sl": sl,
        "tp": tp,
        "atr": atr_val,
        "entry_bar_ts": int(signal_data.get("bar_ts", 0)),
        "created_ts": int(time.time() * 1000),
    }

    vol_note = f" (vol scale {vol_scale:.2f}x)" if USE_VOL_SCALED_SLTP and "ATR" in sltp_note else ""

    volume_ratio = signal_data.get("volume_ratio")
    volume_note = f"\nVolume: {volume_ratio:.2f}x MA" if volume_ratio is not None else ""
    
    adx_val = signal_data.get("adx_val")
    adx_note = f"\nADX: {adx_val:.2f} (Trend Strength)" if adx_val is not None else ""

    session_ok = signal_data.get("session_ok", True)
    session_note = "\nSesi: Aktif (UTC)" if session_ok else ""

    # Breakeven price after round-trip fee (entry fee + exit fee), so TP that
    # looks profitable gross may barely clear fees net -- worth seeing upfront.
    breakeven = entry * (1 + TAKER_FEE_PCT / 100.0) / (1 - TAKER_FEE_PCT / 100.0)
    fee_note = f"\nBreakeven (fee {ROUND_TRIP_FEE_PCT:.2f}%): {fmt(breakeven)}"

    msg = (
        f"🟢 BUY SIGNAL {symbol}\n"
        f"Strategy: DONAL 4H Trend 1H Breakout\n"
        f"Status: SIGNAL ONLY (tanpa auto order)\n"
        f"Entry ideal close 1H: {fmt(entry_ref)}\n"
        f"Harga saat alert: {fmt(entry)}\n"
        f"SL: {fmt(sl)}\n"
        f"TP: {fmt(tp)}\n"
        f"ATR: {fmt(atr_val)}\n"
        f"{sltp_note}{vol_note}"
        f"{volume_note}"
        f"{adx_note}"
        f"{session_note}"
        f"{fee_note}\n"
        f"Catatan: Eksekusi manual, gunakan risiko kecil."
    )
    notify_event(msg)


def send_exit_alert(state, symbol, reason, price=None):
    positions = state.setdefault("virtual_positions", {})
    pos = positions.get(symbol)
    if not pos:
        return

    if price is None:
        try:
            price = get_ticker_price(symbol)
        except Exception:
            price = pos.get("entry", 0.0)

    entry = float(pos.get("entry", 0.0))
    exit_price = float(price)
    pnl = exit_price - entry
    pnl_pct_gross = (pnl / entry * 100.0) if entry > 0 else 0.0
    pnl_pct_net = pnl_pct_gross - ROUND_TRIP_FEE_PCT

    # Signal-only tidak punya fill/qty riil, jadi history hanya menyimpan % net.
    save_trade_history(symbol, pos, exit_price, reason)
    
    positions.pop(symbol, None)
    record_realized_pnl(state, pnl_pct_net)  # tidak ada qty riil di signal-only, cuma %

    # Emoji reflects NET result -- a "win" that doesn't clear round-trip fees
    # isn't actually a win.
    result_emoji = "🟢" if pnl_pct_net >= 0 else "🔴"

    msg = (
        f"{result_emoji} {reason} {symbol}\n"
        f"Strategy: DONAL 4H Trend 1H Breakout\n"
        f"Status: SIGNAL ONLY (tanpa auto order)\n"
        f"Entry virtual: {fmt(entry)}\n"
        f"Exit: {fmt(exit_price)}\n"
        f"Selisih: {fmt(pnl)}\n"
        f"PnL gross: {pnl_pct_gross:+.2f}%\n"
        f"PnL net (setelah fee {ROUND_TRIP_FEE_PCT:.2f}%): {pnl_pct_net:+.2f}%"
    )
    notify_event(msg)


# =====================
# DAILY / WEEKLY LOSS LIMIT (circuit breaker)
# =====================
def get_day_key():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_week_key():
    iso = datetime.now(timezone.utc).isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def ensure_risk_tracking(state):
    """
    Reset counter harian/mingguan begitu periode (UTC) berganti. Untuk mode
    testnet/live juga mengambil snapshot equity di awal periode sebagai acuan %.
    """
    rt = state.setdefault("risk_tracking", {})
    day_key = get_day_key()
    week_key = get_week_key()

    if rt.get("day_key") != day_key:
        was_halted = rt.get("day_halted", False)
        rt["day_key"] = day_key
        rt["day_realized_pnl_quote"] = 0.0
        rt["day_realized_pnl_pct"] = 0.0
        rt["day_start_equity"] = get_total_equity_quote(state) if TRADING_MODE != "off" else None
        rt["day_halted"] = False
        if was_halted:
            notify_event("▶️ Hari baru (UTC) dimulai, limit rugi harian direset. Entry baru diizinkan lagi.")

    if rt.get("week_key") != week_key:
        was_halted = rt.get("week_halted", False)
        rt["week_key"] = week_key
        rt["week_realized_pnl_quote"] = 0.0
        rt["week_realized_pnl_pct"] = 0.0
        rt["week_start_equity"] = get_total_equity_quote(state) if TRADING_MODE != "off" else None
        rt["week_halted"] = False
        if was_halted:
            notify_event("▶️ Minggu baru (UTC) dimulai, limit rugi mingguan direset. Entry baru diizinkan lagi.")

    return rt


def record_realized_pnl(state, pnl_pct_net, pnl_quote=None):
    """
    Dipanggil setiap posisi closed (signal-only maupun auto-trading) untuk
    mengakumulasi rugi/untung ke counter harian & mingguan.
    """
    rt = ensure_risk_tracking(state)
    rt["day_realized_pnl_pct"] = rt.get("day_realized_pnl_pct", 0.0) + pnl_pct_net
    rt["week_realized_pnl_pct"] = rt.get("week_realized_pnl_pct", 0.0) + pnl_pct_net
    if pnl_quote is not None:
        rt["day_realized_pnl_quote"] = rt.get("day_realized_pnl_quote", 0.0) + pnl_quote
        rt["week_realized_pnl_quote"] = rt.get("week_realized_pnl_quote", 0.0) + pnl_quote


def _loss_limit_breached(rt, period, limit_pct):
    if limit_pct <= 0:
        return False, ""

    start_equity = rt.get(f"{period}_start_equity")
    realized_quote = rt.get(f"{period}_realized_pnl_quote", 0.0)
    realized_pct = rt.get(f"{period}_realized_pnl_pct", 0.0)

    if TRADING_MODE != "off" and start_equity:
        loss_quote = -realized_quote
        threshold_quote = start_equity * limit_pct / 100.0
        if threshold_quote > 0 and loss_quote >= threshold_quote:
            return True, f"{loss_quote:.2f} {QUOTE_ASSET} ({realized_pct:+.2f}%)"
        return False, ""

    loss_pct = -realized_pct
    if loss_pct >= limit_pct:
        return True, f"{realized_pct:+.2f}% (akumulasi sinyal, bukan saldo riil)"
    return False, ""


def check_loss_limits_and_maybe_halt(state):
    """
    Return True kalau entry BARU harus diblokir. Mengirim notifikasi SEKALI saja
    tiap kali limit baru terlampaui (tidak spam tiap loop).
    """
    rt = ensure_risk_tracking(state)
    halted = False

    breached, detail = _loss_limit_breached(rt, "day", DAILY_LOSS_LIMIT_PCT)
    if breached:
        halted = True
        if not rt.get("day_halted"):
            rt["day_halted"] = True
            notify_error(
                f"🛑 TRADING DIHENTIKAN SEMENTARA -- limit rugi HARIAN tercapai: {detail}. "
                f"Entry baru diblokir sampai hari berikutnya (00:00 UTC). "
                f"Posisi yang sudah terbuka tetap dipantau & dieksekusi normal."
            )

    breached, detail = _loss_limit_breached(rt, "week", WEEKLY_LOSS_LIMIT_PCT)
    if breached:
        halted = True
        if not rt.get("week_halted"):
            rt["week_halted"] = True
            notify_error(
                f"🛑 TRADING DIHENTIKAN SEMENTARA -- limit rugi MINGGUAN tercapai: {detail}. "
                f"Entry baru diblokir sampai minggu berikutnya (Senin 00:00 UTC). "
                f"Posisi yang sudah terbuka tetap dipantau & dieksekusi normal."
            )

    return halted


# =====================
# EXPOSURE / CORRELATION GUARD
# =====================
def exposure_ok(state, symbol):
    positions = state.get("virtual_positions", {})
    open_symbols = list(positions.keys())

    if MAX_CONCURRENT_POSITIONS > 0 and len(open_symbols) >= MAX_CONCURRENT_POSITIONS:
        log.info(
            f"{symbol}: skip BUY, sudah {len(open_symbols)} posisi terbuka "
            f"(limit {MAX_CONCURRENT_POSITIONS})."
        )
        return False

    if MAX_POSITIONS_PER_GROUP > 0:
        group_idx = symbol_group_index(symbol)
        if group_idx is not None:
            group = CORRELATED_GROUPS[group_idx]
            open_in_group = sum(1 for s in open_symbols if s in group)
            if open_in_group >= MAX_POSITIONS_PER_GROUP:
                log.info(
                    f"{symbol}: skip BUY, grup korelasi {sorted(group)} sudah "
                    f"{open_in_group} posisi (limit {MAX_POSITIONS_PER_GROUP})."
                )
                return False

    return True


# =====================
# PROCESS SYMBOL (dengan cache harga)
# =====================
def update_stop_loss(state, symbol, new_sl, reason=""):
    positions = state.get("virtual_positions", {})
    pos = positions.get(symbol)
    if not pos:
        return
        
    old_sl = float(pos.get("sl", 0.0))
    if new_sl <= old_sl:
        return  # Jangan pernah menurunkan SL
        
    # State SL harus selalu mencerminkan stop yang benar-benar aktif di exchange.
    if pos.get("status") == "open_oco":
        order_list_id = pos.get("oco_order_list_id")
        try:
            if order_list_id:
                cancel_oco_exit(symbol, order_list_id)
            pos["status"] = "open"
            for key in ("oco_order_list_id", "oco_tp_order_id", "oco_sl_order_id",
                        "oco_list_client_order_id", "oco_tp_client_order_id", "oco_sl_client_order_id"):
                pos.pop(key, None)
            state.setdefault("oco_intents", {}).pop(symbol, None)
            pos["sl"] = new_sl
            # Commit the cancellation + new SL before attempting the replacement
            # OCO, so a VPS crash cannot resurrect the old protection on restart.
            save_state(state)
        except Exception as e:
            log.warning(f"{symbol}: Gagal cancel OCO lama untuk update SL: {e}")
            return

        try_place_native_protection(state, symbol)
    else:
        pos["sl"] = new_sl
        save_state(state)
    
    # Remove duplicate save_state - only save once
    notify_event(f"🛡️ SL DI-UPDATE {symbol} ({reason})\nSL Lama: {fmt(old_sl)}\nSL Baru: {fmt(new_sl)}")

def reconcile_pending_orders(state):
    """Recover ambiguous BUY/SELL intents after a process/VPS restart."""
    if TRADING_MODE == "off":
        return

    for symbol, intent in list(state.get("entry_intents", {}).items()):
        client_id = intent.get("client_order_id")
        if not client_id:
            continue
        lookup_status, order = lookup_order_by_client_id(symbol, client_id)
        if lookup_status == "UNKNOWN":
            log.warning(f"{symbol}: pending BUY intent {client_id} lookup UNKNOWN; recovery ditahan.")
            continue
        if not order:
            log.warning(f"{symbol}: pending BUY intent {client_id} tidak ditemukan di exchange; dihapus dari state.")
            state.setdefault("entry_intents", {}).pop(symbol, None)
            continue
        signal_data = intent.get("signal_data") or {}
        reference_price = float(intent.get("reference_price") or signal_data.get("close") or 0.0)
        if reference_price <= 0 or float(signal_data.get("atr", 0.0)) <= 0:
            notify_error(f"{symbol}: pending BUY {client_id} ditemukan tapi metadata signal tidak lengkap. Stop automatic recovery.")
            continue
        place_entry_order(state, symbol, signal_data, reference_price)

    # OCO: reconcile any protection intent left behind by a timeout/crash. The
    # same listClientOrderId is reused, so this cannot create a second OCO.
    for symbol in list(state.get("oco_intents", {})):
        if symbol in state.get("virtual_positions", {}):
            try_place_native_protection(state, symbol)
        else:
            state.setdefault("oco_intents", {}).pop(symbol, None)
            log.info(f"{symbol}: orphaned OCO intent dibersihkan (posisi sudah tidak ada).")

    for symbol, intent in list(state.get("exit_intents", {}).items()):
        client_id = intent.get("client_order_id")
        lookup_status, order = lookup_order_by_client_id(symbol, client_id) if client_id else ("NOT_FOUND", None)
        if lookup_status == "UNKNOWN":
            log.warning(f"{symbol}: pending SELL intent {client_id} lookup UNKNOWN; recovery ditahan.")
            continue
        if not order:
            log.warning(f"{symbol}: pending SELL intent {client_id} tidak ditemukan di exchange; dihapus dari state.")
            state.setdefault("exit_intents", {}).pop(symbol, None)
            continue
        pos = state.get("virtual_positions", {}).get(symbol)
        if pos:
            # Re-enter the idempotent exit path. It reads the persisted client ID
            # and handles both full and partial fills without creating a second SELL.
            place_exit_order(
                state, symbol, intent.get("reason", "RECOVERED EXIT"),
                float(order.get("average") or order.get("price") or 0.0),
                qty_override=float(intent.get("qty") or 0.0) if not intent.get("full_close", True) else None,
            )


def process_symbol(state, symbol, price_cache):
    if symbol not in exchange.markets:
        log.warning(f"{symbol}: tidak ditemukan di exchange.")
        return

    positions = state.setdefault("virtual_positions", {})

    def get_cached_price():
        if symbol not in price_cache:
            try:
                price_cache[symbol] = get_ticker_price(symbol)
            except Exception as e:
                log.warning(f"{symbol}: gagal fetch harga: {e}")
                price_cache[symbol] = None
        return price_cache[symbol]

    # Reconcile an active native OCO first. It may have filled while the bot/VPS
    # was offline. If still open, continue to evaluate trend exit on closed candles.
    if TRADING_MODE != "off" and symbol in positions:
        status = positions[symbol].get("status", "open")
        if status == "open_oco":
            process_open_oco_position(state, symbol)
            if symbol not in positions:
                return
        elif status in ("oco_pending", "protection_unknown") or positions[symbol].get("protection_reconciliation_required") or symbol in state.get("oco_intents", {}):
            try_place_native_protection(state, symbol)
            if symbol not in positions:
                return

    # If protection is UNKNOWN, first try to prove whether the exact OCO exists.
    # NOT_FOUND is safe to replace with a new protection or emergency exit; UNKNOWN
    # remains blocked to prevent a duplicate SELL against a possibly-live OCO.
    if TRADING_MODE != "off" and symbol in positions and positions[symbol].get("status") == "protection_unknown":
        try:
            intent = state.get("oco_intents", {}).get(symbol) or {}
            list_client_id = intent.get("list_client_order_id") or positions[symbol].get("oco_list_client_order_id")
            if list_client_id:
                lookup_status, oco = lookup_oco_by_client_id(symbol, list_client_id)
                if lookup_status == "FOUND":
                    order_list_id, tp_id, sl_id = _extract_oco_child_ids(symbol, oco, intent)
                    if order_list_id and tp_id and sl_id:
                        _apply_oco_to_position(positions[symbol], {
                            "order_list_id": order_list_id, "tp_order_id": tp_id, "sl_order_id": sl_id,
                            "list_client_order_id": list_client_id,
                            "tp_client_order_id": intent.get("tp_client_order_id"),
                            "sl_client_order_id": intent.get("sl_client_order_id"),
                        })
                        state.setdefault("oco_intents", {}).pop(symbol, None)
                        save_state(state)
                    else:
                        mark_protection_unknown(state, symbol, "OCO ditemukan tetapi child order ID belum lengkap")
                elif lookup_status == "NOT_FOUND":
                    state.setdefault("oco_intents", {}).pop(symbol, None)
                    positions[symbol]["status"] = "open"
                    positions[symbol]["protection_reconciliation_required"] = False
                    save_state(state)
                else:
                    mark_protection_unknown(state, symbol, "exchange belum bisa memastikan OCO ada/tidak")
        except Exception as e:
            mark_protection_unknown(state, symbol, f"recovery error: {e}")

    if TRADING_MODE != "off" and USE_NATIVE_OCO_SLTP and symbol in positions:
        pos_now = positions[symbol]
        if pos_now.get("status") == "open" and not pos_now.get("oco_order_list_id") and symbol not in state.get("oco_intents", {}):
            try_place_native_protection(state, symbol)
            if symbol not in positions:
                return

    # Break-even can move a native OCO, or the local polling SL.
    if USE_BREAK_EVEN and symbol in positions and not positions[symbol].get("be_triggered", False):
        pos = positions[symbol]
        entry = float(pos.get("entry", 0.0))
        price = get_cached_price()
        if price is not None and entry > 0:
            profit_pct = (price - entry) / entry * 100.0
            if profit_pct >= BE_TRIGGER_PCT:
                new_sl = entry * (1 + BE_OFFSET_PCT / 100.0)
                update_stop_loss(state, symbol, new_sl, reason=f"Break-Even Triggered (Profit {profit_pct:.2f}%)")
                if symbol in positions:
                    positions[symbol]["be_triggered"] = True
                    save_state(state)  # Pastikan flag be_triggered ke-save

    # Polling protection applies only when no native OCO is active.
    if TRACK_SL_TP and symbol in positions and positions[symbol].get("status", "open") == "open":
        price = get_cached_price()
        if price is not None:
            pos = positions[symbol]
            if float(price) <= float(pos.get("sl", 0.0)):
                trigger_exit(state, symbol, "SL HIT", price)
                return
            if float(price) >= float(pos.get("tp", 0.0)):
                trigger_exit(state, symbol, "TP HIT", price)
                return

    # Evaluate the newest CLOSED candle regardless of whether a position exists.
    # This fixes the previous impossible TREND EXIT branch, which lived under
    # `symbol not in positions`.
    if not should_check_signal(state, symbol):
        return

    try:
        signal_data = calculate_signal(symbol)
    except Exception as e:
        log.warning(f"{symbol}: gagal hitung sinyal: {e}")
        return
    if not signal_data:
        return

    last_bar = int(state.get("last_bar_ts", {}).get(symbol, 0) or 0)
    signal_bar = int(signal_data.get("bar_ts", 0))
    if signal_bar == last_bar:
        return

    first_run = last_bar == 0
    state.setdefault("last_bar_ts", {})[symbol] = signal_bar
    save_state(state)

    if first_run and not ENTRY_ON_FIRST_RUN:
        log.info(f"{symbol}: first run, hanya menandai candle terakhir. Tidak mengirim sinyal lama.")
        return

    # Trend exit is evaluated for an EXISTING position on every new closed candle.
    if (
        SEND_TREND_EXIT
        and signal_data.get("exit_trend")
        and symbol in positions
        and positions[symbol].get("status", "open") in ("open", "open_oco")
    ):
        if state.get("last_exit_alert_bar", {}).get(symbol) != signal_bar:
            trigger_exit(state, symbol, "TREND EXIT", signal_data.get("close"))
            state.setdefault("last_exit_alert_bar", {})[symbol] = signal_bar
            save_state(state)
        return

    # BUY is only considered when there is no open position.
    if signal_data.get("buy") and symbol not in positions:
        if state.get("last_buy_alert_bar", {}).get(symbol) == signal_bar:
            return
        if entry_too_old(signal_bar):
            log.info(f"{symbol}: sinyal BUY terlalu lama, skip.")
        elif not exposure_ok(state, symbol):
            state.setdefault("last_buy_alert_bar", {})[symbol] = signal_bar
        elif check_loss_limits_and_maybe_halt(state):
            log.info(f"{symbol}: entry diblokir oleh daily/weekly loss limit.")
            state.setdefault("last_buy_alert_bar", {})[symbol] = signal_bar
        else:
            market_price = get_cached_price() or float(signal_data.get("close", 0.0))
            trigger_entry(state, symbol, signal_data, market_price)
            state.setdefault("last_buy_alert_bar", {})[symbol] = signal_bar


# =====================
# MAIN LOOP
# =====================
def run():
    global exchange, VALID_SYMBOLS

    if TRADING_MODE not in ("off", "testnet", "live"):
        notify_error(f"TRADING_MODE='{TRADING_MODE}' tidak dikenal (harus off/testnet/live). Bot berhenti.")
        return

    if TRADING_MODE == "testnet" and (not BINANCE_TESTNET_API_KEY or not BINANCE_TESTNET_API_SECRET):
        notify_error("TRADING_MODE=testnet tapi BINANCE_TESTNET_API_KEY/SECRET kosong. Bot berhenti.")
        return

    if TRADING_MODE == "live" and (not BINANCE_LIVE_API_KEY or not BINANCE_LIVE_API_SECRET):
        notify_error("TRADING_MODE=live tapi BINANCE_LIVE_API_KEY/SECRET kosong. Bot berhenti.")
        return

    if PORT > 0:
        health_thread = threading.Thread(target=start_health_server, daemon=True)
        health_thread.start()

    exchange = make_exchange()

    # --- LIVE SAFETY: withdrawal permission must be verified, never fail-open ---
    if TRADING_MODE == "live":
        try:
            restrictions = None
            for method_name in ("private_get_account_api_restrictions", "privateGetAccountApiRestrictions"):
                method = getattr(exchange, method_name, None)
                if method is not None:
                    restrictions = method({}) if method_name == "privateGetAccountApiRestrictions" else method()
                    break
            if not isinstance(restrictions, dict) or "enableWithdrawals" not in restrictions:
                raise RuntimeError("response account API restrictions tidak lengkap")
            if restrictions.get("enableWithdrawals"):
                notify_error("🚨 FATAL: API Key LIVE memiliki izin WITHDRAWAL! Bot dihentikan. Cabut izin withdrawal di Binance.")
                return
            log.info("✅ Validasi API Key LIVE: Izin Withdrawal NONAKTIF (Aman).")
        except Exception as e:
            notify_error(f"🚨 FATAL: tidak bisa memverifikasi izin withdrawal API LIVE: {e}. Bot dihentikan (fail-closed).")
            return
    # ------------------------------------------------------------

    for symbol in SYMBOLS:
        if symbol in exchange.markets:
            VALID_SYMBOLS.append(symbol)
        else:
            notify_error(f"Symbol {symbol} tidak ditemukan di exchange.")

    if not VALID_SYMBOLS:
        notify_error("Tidak ada symbol valid. Bot sinyal berhenti.")
        return

    state = load_state()

    reconcile_pending_orders(state)
    save_state(state)

    if TRADING_MODE == "off":
        mode_line = "Mode: SIGNAL ONLY (tanpa auto order)"
    elif TRADING_MODE == "testnet":
        mode_line = "Mode: AUTO TRADING -- BINANCE TESTNET (uang virtual)"
    else:
        mode_line = "Mode: 🔴🔴🔴 AUTO TRADING -- LIVE (UANG BENERAN) 🔴🔴🔴"

    startup_lines = [
        f"🤖 DONAL Signal Bot started",
        mode_line,
        f"Strategy variant: {STRATEGY_MODE.upper()}",
        f"Symbols: {', '.join(VALID_SYMBOLS)}",
        f"TF: {TIMEFRAME}",
        f"HTF: {HTF_TIMEFRAME}",
        f"Res filter: {USE_RES_FILTER} (min {MIN_ROOM_ATR}x ATR)",
        f"Structure SL/TP: {USE_STRUCTURE_SLTP} (buffer {SR_BUFFER_ATR}x ATR)",
        f"Volume filter: {USE_VOLUME_FILTER} (min {VOLUME_MULT}x MA{VOLUME_MA_LENGTH})",
        f"Vol-scaled SL/TP: {USE_VOL_SCALED_SLTP} (range {VOL_SCALE_MIN}x-{VOL_SCALE_MAX}x)",
        f"Max concurrent positions: {MAX_CONCURRENT_POSITIONS or 'unlimited'}",
        f"Max per correlated group: {MAX_POSITIONS_PER_GROUP or 'unlimited'}",
        f"Daily loss limit: {f'{DAILY_LOSS_LIMIT_PCT}%' if DAILY_LOSS_LIMIT_PCT > 0 else 'nonaktif'} | "
        f"Weekly loss limit: {f'{WEEKLY_LOSS_LIMIT_PCT}%' if WEEKLY_LOSS_LIMIT_PCT > 0 else 'nonaktif'}",
        f"Track SL/TP: {TRACK_SL_TP}",
        f"Send trend exit: {SEND_TREND_EXIT}",
        f"Session filter: {SESSION_FILTER_ENABLED} (UTC {SESSION_START_HOUR}:00-{SESSION_END_HOUR}:00)",
    ]

    if TRADING_MODE != "off":
        slippage_guard_note = (
            f"max {MAX_ENTRY_SLIPPAGE_PCT}%" if MAX_ENTRY_SLIPPAGE_PCT > 0 else "nonaktif"
        )
        startup_lines += [
            f"Risk per trade: {RISK_PCT_PER_TRADE}% dari saldo {QUOTE_ASSET}",
            f"Entry: MARKET (slippage guard: {slippage_guard_note})",
            f"Exit: MARKET (SL/TP/trend exit)",
            f"Native OCO SL/TP: {USE_NATIVE_OCO_SLTP} (UNKNOWN = no blind retry)",
        ]

    startup_lines.append(f"State file: {STATE_FILE}")

    notify_event("\n".join(startup_lines))

    while RUNNING:
        try:
            price_cache = {}

            for symbol in VALID_SYMBOLS:
                try:
                    process_symbol(state, symbol, price_cache)
                except ccxt.NetworkError as e:
                    log.warning(f"{symbol} network error: {e}")
                except ccxt.ExchangeError as e:
                    notify_error(f"{symbol} exchange error: {e}")
                except Exception as e:
                    notify_error(f"{symbol} unexpected error: {e}")

            save_state(state)
            sleep_interruptible(LOOP_INTERVAL_SECONDS)
        except Exception as e:
            notify_error_throttled("main_loop_error", f"Main loop error: {e}")
            sleep_interruptible(30)

    save_state(state)
    notify_event("🛑 DONAL Signal Bot berhenti/shutdown.")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        notify_error(f"Fatal error: {e}")
        raise
