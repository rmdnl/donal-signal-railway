import json
import os
import time
from pathlib import Path

import ccxt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh

load_dotenv()

st.set_page_config(
    page_title="DONAL // TRADING TERMINAL",
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st_autorefresh(interval=5000, key="terminal_refresh")

STATE_FILE = Path(os.getenv("STATE_FILE", "state_signals.json"))
HISTORY_FILE = Path(os.getenv("HISTORY_FILE", "trade_history.json"))
TRADING_MODE = os.getenv("TRADING_MODE", "off").strip().lower()
QUOTE_ASSET = os.getenv("QUOTE_ASSET", "USDT").upper()

st.markdown(
    r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root{--bg:#0a0d0e;--panel:#101416;--panel2:#14191b;--line:#293236;--soft:#1c2427;--text:#d9dfdc;--muted:#71807b;--amber:#e6b85c;--mint:#79ddb1;--cyan:#79cde0;--red:#df7777;--purple:#aa9be0}
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif}.stApp{background:radial-gradient(circle at 55% -15%,rgba(230,184,92,.06),transparent 34%),linear-gradient(rgba(255,255,255,.014) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.014) 1px,transparent 1px),var(--bg);background-size:auto,24px 24px,24px 24px;color:var(--text)}
.block-container{max-width:1600px;padding:.75rem 1rem 4rem}#MainMenu,footer,header{visibility:hidden}
.terminal-bar{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:10px 13px;margin-bottom:9px;border:1px solid var(--line);background:#0c1011;font:12px 'IBM Plex Mono',monospace;box-shadow:inset 0 1px 0 rgba(255,255,255,.025)}
.brand{display:flex;align-items:center;gap:10px;letter-spacing:1.4px;font-weight:600}.brand-mark{color:var(--amber);font-size:16px}.brand small{color:var(--muted);font-weight:400}.top-right{display:flex;align-items:center;gap:12px;color:var(--muted)}.status{color:var(--mint)}.status.off{color:var(--red)}
.nav-shell{border:1px solid var(--line);background:#0d1112;margin-bottom:10px;padding:3px}.nav-shell [data-testid="stHorizontalBlock"]{gap:2px}.nav-shell label{display:none}.nav-shell div[role="radiogroup"]{gap:2px;flex-wrap:nowrap}.nav-shell div[role="radiogroup"]>label{display:flex!important;align-items:center;justify-content:center;min-width:100px;padding:7px 11px;border:1px solid transparent;background:transparent;color:#75817d;font:500 10px 'IBM Plex Mono',monospace;letter-spacing:1px;cursor:pointer}.nav-shell div[role="radiogroup"]>label:has(input:checked){color:var(--amber);border-color:var(--line);background:#151a1c;box-shadow:inset 0 -1px 0 var(--amber)}.nav-shell input{display:none}
.section-title{margin:12px 0 7px;color:#aeb8b4;font:500 10px 'IBM Plex Mono',monospace;letter-spacing:1.4px;text-transform:uppercase}.pane{position:relative;background:linear-gradient(180deg,rgba(255,255,255,.024),rgba(255,255,255,.008));border:1px solid var(--line);border-radius:3px;padding:11px;box-shadow:0 8px 26px rgba(0,0,0,.16),inset 0 1px 0 rgba(255,255,255,.02)}.pane:after{content:'⋮⋮';position:absolute;right:5px;top:4px;color:#394447;font:9px 'IBM Plex Mono',monospace;letter-spacing:-2px;transform:rotate(90deg);opacity:.7}.pane-head{display:flex;justify-content:space-between;align-items:center;margin:-1px 0 8px;padding-bottom:7px;border-bottom:1px solid var(--soft);font:500 9px 'IBM Plex Mono',monospace;letter-spacing:1px;color:#66736f}.pane-head span:last-child{color:#4d5a56}
.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.metric{min-height:76px;padding:10px 11px;border:1px solid var(--line);background:#0f1315}.metric-label{font:500 9px 'IBM Plex Mono',monospace;color:var(--muted);letter-spacing:1px;text-transform:uppercase}.metric-value{margin-top:7px;font:600 23px 'IBM Plex Mono',monospace;color:#e3e9e5}.metric-sub{margin-top:3px;font:9px 'IBM Plex Mono',monospace;color:#596561}.pos{color:var(--mint)!important}.neg{color:var(--red)!important}.amber{color:var(--amber)!important}.cyan{color:var(--cyan)!important}.purple{color:var(--purple)!important}
.terminal-table{width:100%;border-collapse:collapse;font:10px 'IBM Plex Mono',monospace}.terminal-table th{color:#62706b;text-align:left;font-weight:500;padding:6px 5px;border-bottom:1px solid var(--line);letter-spacing:.7px}.terminal-table td{padding:7px 5px;border-bottom:1px solid var(--soft);color:#c8d0cc}.terminal-table tr:last-child td{border-bottom:0}.pair{color:#e0e7e3;font-weight:600}.badge{display:inline-block;padding:2px 4px;border:1px solid currentColor;border-radius:2px;font:600 8px 'IBM Plex Mono',monospace;letter-spacing:.5px}.quote{border-left:2px solid var(--amber);padding:9px 11px;margin-top:8px;background:#0f1315;font:500 10px 'IBM Plex Mono',monospace;color:#9aa6a1}.log-row{display:grid;grid-template-columns:70px 10px 1fr;gap:7px;padding:6px 0;border-bottom:1px solid var(--soft);font:9px 'IBM Plex Mono',monospace}.log-row:last-child{border-bottom:0}.log-time{color:#56625e}.log-dot{width:6px;height:6px;margin-top:3px;border-radius:50%;background:#5d6965}.log-dot.ok{background:var(--mint)}.log-dot.warn{background:var(--amber)}.log-dot.err{background:var(--red)}
.chart-shell{padding:4px 5px 0;background:#0c1011;border:1px solid var(--line)}.terminal-footer{margin-top:13px;padding-top:9px;border-top:1px solid var(--line);display:flex;justify-content:space-between;color:#53605c;font:9px 'IBM Plex Mono',monospace}
.stButton button{border:1px solid var(--line)!important;background:#111618!important;color:#cdd5d1!important;border-radius:2px!important;font:500 10px 'IBM Plex Mono',monospace!important}.stButton button:hover{border-color:#697671!important;color:#fff!important}.stDataFrame{border:1px solid var(--line)}
[data-testid="stPlotlyChart"]{margin:0!important}.stPlotlyChart>div{border:0!important}
.mobile-spacer{display:none}
@media(max-width:900px){.block-container{padding:.55rem .55rem 5rem}.terminal-bar{align-items:flex-start}.top-right{flex-direction:column;align-items:flex-end;gap:2px}.metric-grid{grid-template-columns:repeat(2,1fr)}.metric-value{font-size:19px}.nav-shell{position:fixed;left:8px;right:8px;bottom:8px;z-index:9999;margin:0;border:1px solid #3a4446;background:rgba(13,17,18,.97);box-shadow:0 10px 30px rgba(0,0,0,.55);padding:3px}.nav-shell div[role="radiogroup"]>label{min-width:0;flex:1;padding:8px 4px;font-size:8px}.nav-shell div[role="radiogroup"]>label span{white-space:nowrap}.pane:after{display:none}}
@media(max-width:520px){.brand{font-size:10px}.brand small{display:none}.terminal-bar{padding:9px}.top-right{font-size:8px}.metric{min-height:69px;padding:8px}.metric-value{font-size:16px}.metric-label{font-size:8px}.metric-sub{font-size:7px}.section-title{margin-top:10px}.terminal-footer{font-size:8px;gap:8px}.terminal-footer span:last-child{text-align:right}}
.stApp:after{content:"";position:fixed;inset:0;pointer-events:none;background:linear-gradient(rgba(255,255,255,.009) 50%,transparent 50%);background-size:100% 4px;opacity:.13;mix-blend-mode:screen}

/* NAV VISIBILITY FIX */
.nav-shell div[role="radiogroup"]>label{color:#c8d0cc!important}
.nav-shell div[role="radiogroup"]>label p{color:inherit!important}
.nav-shell div[role="radiogroup"]>label:has(input:checked){color:var(--amber)!important}
.nav-shell input{display:none!important}
.nav-shell div[role="radiogroup"]>label>div:first-child{display:none!important}

/* NAV FIX GLOBAL V2 */
div[role="radiogroup"]{display:flex;flex-direction:row;gap:4px;flex-wrap:wrap}
div[role="radiogroup"] label{display:flex!important;align-items:center;justify-content:center;min-width:90px;padding:8px 12px;border:1px solid var(--line);background:#0f1315;color:#c8d0cc!important;font:500 10px 'IBM Plex Mono',monospace;letter-spacing:1px;cursor:pointer;border-radius:3px}
div[role="radiogroup"] label p{color:#c8d0cc!important;margin:0!important;font:500 10px 'IBM Plex Mono',monospace!important;letter-spacing:1px}
div[role="radiogroup"] label:has(input:checked){color:var(--amber)!important;border-color:var(--line);background:#151a1c;box-shadow:inset 0 -2px 0 var(--amber)}
div[role="radiogroup"] label:has(input:checked) p{color:var(--amber)!important}
div[role="radiogroup"] input[type="radio"]{display:none!important}
div[role="radiogroup"] label div:has(> input[type="radio"]){display:none!important}
</style>
""",
    unsafe_allow_html=True,
)


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return default


def bot_status():
    if not STATE_FILE.exists():
        return False, None
    try:
        age = max(0, time.time() - STATE_FILE.stat().st_mtime)
        return age < 120, age
    except OSError:
        return False, None


@st.cache_resource
def get_exchange():
    return ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}})


@st.cache_data(ttl=8)
def fetch_prices(symbols):
    out = {}
    if not symbols:
        return out
    ex = get_exchange()
    for symbol in symbols:
        try:
            out[symbol] = float(ex.fetch_ticker(symbol).get("last") or 0)
        except Exception:
            out[symbol] = None
    return out


@st.cache_data(ttl=20)
def fetch_ohlcv(symbol, timeframe="1h", limit=72):
    try:
        return get_exchange().fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except Exception:
        return []


def fetch_balance():
    if TRADING_MODE not in {"live", "testnet"}:
        return float(os.getenv("VIRTUAL_BALANCE", "1000")), "VIRTUAL"
    api_key = os.getenv("BINANCE_TESTNET_API_KEY" if TRADING_MODE == "testnet" else "BINANCE_LIVE_API_KEY")
    api_secret = os.getenv("BINANCE_TESTNET_API_SECRET" if TRADING_MODE == "testnet" else "BINANCE_LIVE_API_SECRET")
    if not api_key or not api_secret:
        return 0.0, "NO API"
    try:
        ex = ccxt.binance({"apiKey": api_key, "secret": api_secret, "enableRateLimit": True, "options": {"defaultType": "spot"}})
        if TRADING_MODE == "testnet":
            ex.set_sandbox_mode(True)
        bal = ex.fetch_balance()
        total = bal.get(QUOTE_ASSET, {}).get("total")
        if total is None:
            total = (bal.get("total") or {}).get(QUOTE_ASSET, 0)
        return float(total or 0), "BINANCE"
    except Exception:
        return 0.0, "API ERROR"


def fmt_price(value):
    try:
        v = float(value)
        if v >= 1000:
            return f"{v:,.2f}"
        if v >= 1:
            return f"{v:,.4f}"
        return f"{v:.6f}"
    except Exception:
        return "-"


def fmt_money(value):
    try:
        return f"{float(value):+,.2f} {QUOTE_ASSET}"
    except Exception:
        return f"0.00 {QUOTE_ASSET}"


def history_rows(history):
    rows = []
    for t in history[-16:][::-1]:
        pnl = float(t.get("pnl_net", t.get("pnl", 0)) or 0)
        exit_ts = t.get("exit_ts")
        stamp = pd.to_datetime(exit_ts, unit="ms", errors="coerce") if exit_ts else pd.NaT
        rows.append({"TIME": stamp.strftime("%m-%d %H:%M") if not pd.isna(stamp) else "-", "PAIR": t.get("symbol", "-"), "SIDE": "SELL", "EXIT": fmt_price(t.get("exit")), "PNL": pnl, "REASON": str(t.get("reason", "-"))[:24]})
    return rows


def make_candles(raw):
    if not raw:
        return None
    df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
    df["time"] = pd.to_datetime(df["ts"], unit="ms")
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema60"] = df["close"].ewm(span=60, adjust=False).mean()
    return df


def terminal_chart(df, height=470):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df["time"], open=df["open"], high=df["high"], low=df["low"], close=df["close"], name="OHLC", increasing_line_color="#79ddb1", decreasing_line_color="#df7777", increasing_fillcolor="#79ddb1", decreasing_fillcolor="#df7777"))
    fig.add_trace(go.Scatter(x=df["time"], y=df["ema20"], mode="lines", name="EMA20", line=dict(color="#e6b85c", width=1.2)))
    fig.add_trace(go.Scatter(x=df["time"], y=df["ema60"], mode="lines", name="EMA60", line=dict(color="#79cde0", width=1.2)))
    fig.update_layout(height=height, margin=dict(l=4,r=4,t=8,b=4), paper_bgcolor="#0c1011", plot_bgcolor="#0c1011", font=dict(family="IBM Plex Mono", size=9, color="#8b9893"), hovermode="x unified", showlegend=True, legend=dict(orientation="h", y=1.02, x=0, font=dict(size=8)), xaxis_rangeslider_visible=False, dragmode="pan")
    fig.update_xaxes(showgrid=True, gridcolor="#1b2326", linecolor="#293236", zeroline=False, rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor="#1b2326", linecolor="#293236", zeroline=False, side="right")
    return fig


def volume_chart(df, height=120):
    up = df["close"] >= df["open"]
    fig = go.Figure(go.Bar(x=df["time"], y=df["volume"], marker_color=["#79ddb1" if x else "#df7777" for x in up], opacity=.62, name="Volume"))
    fig.update_layout(height=height, margin=dict(l=4,r=4,t=0,b=4), paper_bgcolor="#0c1011", plot_bgcolor="#0c1011", showlegend=False)
    fig.update_xaxes(showgrid=True, gridcolor="#1b2326", linecolor="#293236", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#1b2326", linecolor="#293236", zeroline=False, side="right")
    return fig


state = load_json(STATE_FILE, {})
history = load_json(HISTORY_FILE, [])
if not isinstance(history, list):
    history = []
positions = state.get("virtual_positions", {}) if isinstance(state, dict) else {}
if not isinstance(positions, dict):
    positions = {}
symbols = list(positions.keys())
prices = fetch_prices(symbols)
balance, balance_source = fetch_balance()

open_rows=[]; unrealized=0.0; open_value=0.0
for symbol, pos in positions.items():
    entry = float(pos.get("entry", 0) or 0)
    qty = float(pos.get("filled_qty") or pos.get("qty") or 0)
    if qty == 0 and TRADING_MODE == "off":
        qty = 1.0
    live = float(prices.get(symbol) or entry or 0)
    pnl = (live - entry) * qty
    pnl_pct = ((live - entry) / entry * 100) if entry else 0
    unrealized += pnl
    if TRADING_MODE != "off":
        open_value += live * qty
    open_rows.append({"PAIR":symbol,"STATUS":str(pos.get("status","open")).upper(),"ENTRY":fmt_price(entry),"LAST":fmt_price(live),"QTY":f"{qty:.6f}".rstrip("0").rstrip("."),"P&L":pnl,"P&L %":pnl_pct,"TP":fmt_price(pos.get("tp")),"SL":fmt_price(pos.get("sl"))})
equity=balance+open_value
realized=sum(float(t.get("pnl_net",t.get("pnl",0)) or 0) for t in history)
wins=sum(1 for t in history if float(t.get("pnl_net",t.get("pnl",0)) or 0)>0)
win_rate=wins/len(history)*100 if history else 0
online,age=bot_status(); mode_label=TRADING_MODE.upper() if TRADING_MODE else "OFF"; mode_cls="status" if online else "status off"; age_label=f"STATE {int(age)}s" if age is not None else "NO STATE"

st.markdown(f'<div class="terminal-bar"><div class="brand"><span class="brand-mark">▣</span> DONAL // TRADING TERMINAL <small>v2.1 · VPS</small></div><div class="top-right"><span class="{mode_cls}">● {"ONLINE" if online else "OFFLINE"}</span><span>{mode_label}</span><span>{age_label}</span><span>{time.strftime("%H:%M:%S WIB")}</span></div></div>', unsafe_allow_html=True)

st.markdown('<div class="nav-shell">', unsafe_allow_html=True)
nav=st.radio("Terminal navigation", ["OVERVIEW","MARKET","POSITIONS","HISTORY","SYSTEM"], horizontal=True, label_visibility="collapsed", key="terminal_nav")
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">// ACCOUNT OVERVIEW</div>', unsafe_allow_html=True)
st.markdown(f'<div class="metric-grid"><div class="metric"><div class="metric-label">Bot Equity</div><div class="metric-value amber">{equity:,.2f}</div><div class="metric-sub">{QUOTE_ASSET} · ESTIMATED</div></div><div class="metric"><div class="metric-label">Realized P&L</div><div class="metric-value {"pos" if realized>=0 else "neg"}">{realized:+,.2f}</div><div class="metric-sub">NET · {len(history)} CLOSED</div></div><div class="metric"><div class="metric-label">Open P&L</div><div class="metric-value {"pos" if unrealized>=0 else "neg"}">{unrealized:+,.2f}</div><div class="metric-sub">{len(open_rows)} ACTIVE</div></div><div class="metric"><div class="metric-label">Win Rate</div><div class="metric-value cyan">{win_rate:.1f}%</div><div class="metric-sub">{wins} WINS / {len(history)} TRADES</div></div></div>', unsafe_allow_html=True)

if nav in {"OVERVIEW","MARKET"}:
    left,center,right=st.columns([1.0,2.45,1.0],gap="small")
    with left:
        st.markdown('<div class="section-title">// WATCHLIST</div>',unsafe_allow_html=True)
        watch=symbols or ["BTC/USDT","ETH/USDT","BNB/USDT","SOL/USDT"]
        rows=[]
        for s in watch[:10]:
            p=prices.get(s)
            rows.append(f'<tr><td class="pair">{s.replace("/","")}</td><td>{fmt_price(p) if p else "--"}</td><td>{"OPEN" if s in positions else "-"}</td></tr>')
        st.markdown('<div class="pane"><div class="pane-head"><span>MARKET WATCH</span><span>LIVE</span></div><table class="terminal-table"><thead><tr><th>PAIR</th><th>LAST</th><th>STATE</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>',unsafe_allow_html=True)
        st.markdown('<div class="section-title">// RISK SNAPSHOT</div>',unsafe_allow_html=True)
        st.markdown(f'<div class="pane"><table class="terminal-table"><tbody><tr><td>MODE</td><td>{mode_label}</td></tr><tr><td>POSITIONS</td><td>{len(open_rows)}</td></tr><tr><td>RISK/TRD</td><td>{os.getenv("RISK_PCT_PER_TRADE","-")}%</td></tr><tr><td>MAX POS</td><td>{os.getenv("MAX_CONCURRENT_POSITIONS","-")}</td></tr><tr><td>DAILY LIMIT</td><td>{os.getenv("DAILY_LOSS_LIMIT_PCT","-")}%</td></tr></tbody></table></div>',unsafe_allow_html=True)
    with center:
        selected=st.selectbox("Market", symbols or ["BTC/USDT","ETH/USDT","BNB/USDT","SOL/USDT"], label_visibility="collapsed", key="chart_symbol")
        st.markdown(f'<div class="section-title">// MARKET · {selected.replace("/","")} · 1H</div>',unsafe_allow_html=True)
        df=make_candles(fetch_ohlcv(selected,"1h",96))
        if df is not None and len(df)>=2:
            last=float(df.close.iloc[-1]); prev=float(df.close.iloc[-2]); change=(last-prev)/prev*100 if prev else 0
            st.markdown(f'<div class="pane chart-shell"><div class="pane-head"><span>OHLC / EMA20 / EMA60</span><span>{fmt_price(last)} · <span class="{"pos" if change>=0 else "neg"}">{change:+.2f}%</span></span></div>',unsafe_allow_html=True)
            st.plotly_chart(terminal_chart(df), width='stretch', config={"displaylogo":False,"scrollZoom":True,"modeBarButtonsToRemove":["lasso2d","select2d","autoScale2d"]})
            st.plotly_chart(volume_chart(df), width='stretch', config={"displaylogo":False,"displayModeBar":False})
            st.markdown('</div>',unsafe_allow_html=True)
        else:
            st.markdown('<div class="pane"><div class="quote">MARKET FEED UNAVAILABLE · TERMINAL FALLBACK ACTIVE</div></div>',unsafe_allow_html=True)
        st.markdown('<div class="section-title">// ACTIVE POSITIONS</div>',unsafe_allow_html=True)
        if open_rows:
            html='<div class="pane"><table class="terminal-table"><thead><tr><th>PAIR</th><th>ENTRY</th><th>LAST</th><th>P&L</th><th>TP</th><th>SL</th></tr></thead><tbody>'
            for r in open_rows:
                html+=f'<tr><td class="pair">{r["PAIR"]}</td><td>{r["ENTRY"]}</td><td>{r["LAST"]}</td><td class="{"pos" if r["P&L"]>=0 else "neg"}">{r["P&L"]:+,.2f}</td><td>{r["TP"]}</td><td>{r["SL"]}</td></tr>'
            st.markdown(html+'</tbody></table></div>',unsafe_allow_html=True)
        else: st.markdown('<div class="pane"><div class="quote">NO ACTIVE POSITION · CASH IS PATIENT.</div></div>',unsafe_allow_html=True)
    with right:
        st.markdown('<div class="section-title">// SYSTEM</div>',unsafe_allow_html=True)
        st.markdown(f'<div class="pane"><div class="pane-head"><span>ENGINE STATUS</span><span>{age_label}</span></div><table class="terminal-table"><tbody><tr><td>ENGINE</td><td class="{mode_cls}">{"RUNNING" if online else "STOPPED"}</td></tr><tr><td>EXCHANGE</td><td>BINANCE SPOT</td></tr><tr><td>QUOTE</td><td>{QUOTE_ASSET}</td></tr><tr><td>REFRESH</td><td>5 SEC</td></tr></tbody></table><div class="quote">DISCIPLINE &gt; EMOTION<br>PROTECT CAPITAL FIRST.</div></div>',unsafe_allow_html=True)
        st.markdown('<div class="section-title">// RECENT TAPE</div>',unsafe_allow_html=True)
        tape=history_rows(history)[:7]
        if tape:
            html='<div class="pane">'
            for r in tape: html+=f'<div class="log-row"><div class="log-time">{r["TIME"]}</div><div class="log-dot {"ok" if r["PNL"]>=0 else "err"}"></div><div><span class="pair">{r["PAIR"]}</span> {r["REASON"]} <span class="{"pos" if r["PNL"]>=0 else "neg"}">{r["PNL"]:+.2f}</span></div></div>'
            st.markdown(html+'</div>',unsafe_allow_html=True)
        else: st.markdown('<div class="pane"><div class="quote">NO CLOSED TRADES YET.</div></div>',unsafe_allow_html=True)

elif nav=="POSITIONS":
    st.markdown('<div class="section-title">// OPEN POSITIONS</div>',unsafe_allow_html=True)
    if open_rows:
        st.dataframe(pd.DataFrame(open_rows),width='stretch',hide_index=True,column_config={"P&L":st.column_config.NumberColumn(format="%.2f"),"P&L %":st.column_config.NumberColumn(format="%.2f%%")})
    else: st.info("No open positions.")

elif nav=="HISTORY":
    st.markdown('<div class="section-title">// EXECUTION HISTORY · NET OF FEES</div>',unsafe_allow_html=True)
    if history:
        st.dataframe(pd.DataFrame(history_rows(history)),width='stretch',hide_index=True,column_config={"PNL":st.column_config.NumberColumn(format="%+.2f")})
        curve=[0.0]
        for t in history: curve.append(curve[-1]+float(t.get("pnl_net",t.get("pnl",0)) or 0))
        st.markdown('<div class="section-title">// EQUITY TRACE</div>',unsafe_allow_html=True)
        st.line_chart(pd.DataFrame({"Cumulative PnL":curve}),height=260,width='stretch')
    else: st.info("No closed trades yet.")

elif nav=="SYSTEM":
    st.markdown('<div class="section-title">// SYSTEM / EXECUTION TELEMETRY</div>',unsafe_allow_html=True)
    logs=[]
    for key in ("entry_intents","oco_intents","exit_intents","risk_tracking"):
        value=state.get(key,{}) if isinstance(state,dict) else {}; count=len(value) if isinstance(value,dict) else 0; logs.append((key.upper(),count))
    html='<div class="pane">'
    for label,count in logs: html+=f'<div class="log-row"><div class="log-time">STATE</div><div class="log-dot {"warn" if count else "ok"}"></div><div>{label} <span>{count} ITEM(S)</span></div></div>'
    st.markdown(html+'</div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">// CONFIG</div>',unsafe_allow_html=True)
    cfg={"STATE FILE":str(STATE_FILE),"HISTORY FILE":str(HISTORY_FILE),"MODE":mode_label,"QUOTE":QUOTE_ASSET,"REFRESH":"5 SEC","BOT STATE":age_label}
    st.markdown('<div class="pane"><table class="terminal-table">'+''.join(f'<tr><td>{k}</td><td>{v}</td></tr>' for k,v in cfg.items())+'</table></div>',unsafe_allow_html=True)


# =====================
# STRATEGY LAB: BREAKOUT vs PULLBACK (A/B TEST)
# =====================
PULLBACK_HISTORY = Path(os.getenv("PULLBACK_HISTORY_FILE", "/home/ubuntu/donal-pullback/history_pullback.json"))
PULLBACK_STATE = Path(os.getenv("PULLBACK_STATE_FILE", "/home/ubuntu/donal-pullback/state_pullback.json"))

def strategy_stats(hist):
    if not hist:
        return None
    pnls = [float(t.get("pnl_net", t.get("pnl", 0)) or 0) for t in hist]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    eq = 0.0; peak = 0.0; mdd = 0.0
    for p in pnls:
        eq += p
        peak = max(peak, eq)
        mdd = min(mdd, eq - peak)
    return {"trades": len(pnls), "wins": len(wins), "win_rate": (len(wins)/len(pnls)*100) if pnls else 0.0, "net": sum(pnls), "pf": pf, "mdd": mdd}

pb_history = load_json(PULLBACK_HISTORY, [])
if not isinstance(pb_history, list):
    pb_history = []
pb_state = load_json(PULLBACK_STATE, {})
pb_positions = pb_state.get("virtual_positions", {}) if isinstance(pb_state, dict) else {}

st_a = strategy_stats(history)
st_b = strategy_stats(pb_history)

def _fmt_pf(v):
    return "inf" if v == float("inf") else f"{v:.2f}"

a_tr = st_a["trades"] if st_a else 0
b_tr = st_b["trades"] if st_b else 0
a_wr = st_a["win_rate"] if st_a else 0.0
b_wr = st_b["win_rate"] if st_b else 0.0
a_net = st_a["net"] if st_a else 0.0
b_net = st_b["net"] if st_b else 0.0
a_pf = _fmt_pf(st_a["pf"] if st_a else 0.0)
b_pf = _fmt_pf(st_b["pf"] if st_b else 0.0)
a_mdd = st_a["mdd"] if st_a else 0.0
b_mdd = st_b["mdd"] if st_b else 0.0
a_cls = "pos" if a_net >= 0 else "neg"
b_cls = "pos" if b_net >= 0 else "neg"

st.markdown('<div class="section-title">// STRATEGY LAB · A/B TEST</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="pane"><div class="pane-head"><span>BREAKOUT vs PULLBACK · TESTNET RACE</span><span>LIVE</span></div>'
    '<table class="terminal-table"><thead><tr><th>METRIC</th><th>BREAKOUT</th><th>PULLBACK</th></tr></thead><tbody>'
    f'<tr><td>OPEN POSITIONS</td><td>{len(open_rows)}</td><td>{len(pb_positions)}</td></tr>'
    f'<tr><td>CLOSED TRADES</td><td>{a_tr}</td><td>{b_tr}</td></tr>'
    f'<tr><td>WIN RATE</td><td>{a_wr:.1f}%</td><td>{b_wr:.1f}%</td></tr>'
    f'<tr><td>NET PNL</td><td class="{a_cls}">{a_net:+,.2f}</td><td class="{b_cls}">{b_net:+,.2f}</td></tr>'
    f'<tr><td>PROFIT FACTOR</td><td>{a_pf}</td><td>{b_pf}</td></tr>'
    f'<tr><td>MAX DRAWDOWN</td><td class="neg">{a_mdd:,.2f}</td><td class="neg">{b_mdd:,.2f}</td></tr>'
    '</tbody></table></div>',
    unsafe_allow_html=True,
)

st.markdown(f'<div class="terminal-footer"><span>DONAL // TRADING TERMINAL · RETRO MODERN v2.1</span><span>{"● BINANCE LINKED" if balance_source=="BINANCE" else "○ "+balance_source} · {time.strftime("%Y-%m-%d")}</span></div>',unsafe_allow_html=True)
