import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import json
import os
from datetime import datetime

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Stock Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Base */
  html, body, [data-testid="stAppViewContainer"] {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: 'Inter', sans-serif;
  }
  [data-testid="stHeader"] { background-color: #0d1117; }
  [data-testid="block-container"] { padding-top: 1.5rem; }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 16px 20px;
  }
  [data-testid="stMetricLabel"]  { color: #8b949e; font-size: 0.78rem; letter-spacing: .05em; text-transform: uppercase; }
  [data-testid="stMetricValue"]  { color: #e6edf3; font-size: 1.55rem; font-weight: 700; }
  [data-testid="stMetricDelta"]  { font-size: 0.82rem; }

  /* Section headers */
  .section-title {
    color: #8b949e;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: .12em;
    text-transform: uppercase;
    margin-bottom: 0.6rem;
  }

  /* AI card */
  .ai-card {
    background: linear-gradient(135deg, #161b22 0%, #1c2333 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 22px 26px;
    position: relative;
    overflow: hidden;
  }
  .ai-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 12px 12px 0 0;
  }
  .ai-card-buy::before   { background: linear-gradient(90deg, #238636, #2ea043); }
  .ai-card-sell::before  { background: linear-gradient(90deg, #da3633, #f85149); }
  .ai-card-hold::before  { background: linear-gradient(90deg, #9e6a03, #d29922); }
  .ai-card-wait::before  { background: linear-gradient(90deg, #30363d, #484f58); }

  .signal-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: .06em;
    margin-bottom: 12px;
  }
  .badge-buy  { background: #1a4429; color: #3fb950; border: 1px solid #238636; }
  .badge-sell { background: #3d1a1a; color: #f85149; border: 1px solid #da3633; }
  .badge-hold { background: #3a2d0a; color: #d29922; border: 1px solid #9e6a03; }

  .confidence-bar-bg {
    background: #21262d;
    border-radius: 6px;
    height: 8px;
    margin: 6px 0 14px 0;
    overflow: hidden;
  }
  .confidence-bar-fill {
    height: 100%;
    border-radius: 6px;
    transition: width .4s ease;
  }
  .fill-buy  { background: linear-gradient(90deg, #238636, #2ea043); }
  .fill-sell { background: linear-gradient(90deg, #da3633, #f85149); }
  .fill-hold { background: linear-gradient(90deg, #9e6a03, #d29922); }

  .ai-summary {
    color: #8b949e;
    font-size: 0.88rem;
    line-height: 1.65;
    margin-top: 4px;
  }
  .ai-label { color: #8b949e; font-size: 0.72rem; letter-spacing: .08em; text-transform: uppercase; margin-bottom: 2px; }
  .ai-wait  { color: #484f58; font-style: italic; font-size: 0.9rem; padding: 8px 0; }

  /* Divider */
  hr { border-color: #21262d; margin: 1.2rem 0; }

  /* Ticker header */
  .ticker-header { display: flex; align-items: baseline; gap: 14px; margin-bottom: 0.2rem; }
  .ticker-name   { font-size: 2rem; font-weight: 800; color: #e6edf3; }
  .ticker-sub    { font-size: 0.9rem; color: #8b949e; }

  /* Last updated */
  .last-updated  { color: #484f58; font-size: 0.75rem; text-align: right; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)  # Increased TTL to 1 hour to avoid Yahoo Finance rate limits
def fetch_ticker_data(symbol: str):
    ticker = yf.Ticker(symbol)
    info = ticker.info
    hist = ticker.history(period="6mo", interval="1d")
    return info, hist


def load_ai_analysis(symbol: str):
    # Simplify the filename: remove the ^ for GSPC
    clean_sym = symbol.replace("^", "")
    path = f"ai_analysis_{clean_sym}.json"
    
    # Fallback to the original filename if the specific one doesn't exist yet
    if not os.path.exists(path) and os.path.exists("ai_analysis.json"):
        path = "ai_analysis.json"
        
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_sync_enabled(enabled: bool, symbol: str):
    """Write only the sync_enabled field; preserve all other keys."""
    clean_sym = symbol.replace("^", "")
    path = f"ai_analysis_{clean_sym}.json"
    
    data = load_ai_analysis(symbol) or {}
    data["sync_enabled"] = enabled
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def color_for_signal(signal: str):
    s = signal.upper()
    if s == "BUY":
        return "buy"
    elif s == "SELL":
        return "sell"
    return "hold"


def build_candlestick(hist: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    # Volume bars
    vol_colors = [
        "#238636" if c >= o else "#da3633"
        for c, o in zip(hist["Close"], hist["Open"])
    ]
    fig.add_trace(go.Bar(
        x=hist.index, y=hist["Volume"],
        marker_color=vol_colors,
        opacity=0.35,
        name="Volume",
        yaxis="y2",
        showlegend=False,
    ))

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=hist.index,
        open=hist["Open"],
        high=hist["High"],
        low=hist["Low"],
        close=hist["Close"],
        name="Price",
        increasing=dict(line=dict(color="#2ea043", width=1), fillcolor="#238636"),
        decreasing=dict(line=dict(color="#f85149", width=1), fillcolor="#da3633"),
    ))

    # 20-day SMA
    sma20 = hist["Close"].rolling(20).mean()
    fig.add_trace(go.Scatter(
        x=hist.index, y=sma20,
        line=dict(color="#d29922", width=1.5, dash="dot"),
        name="SMA 20",
    ))

    # 50-day SMA
    sma50 = hist["Close"].rolling(50).mean()
    fig.add_trace(go.Scatter(
        x=hist.index, y=sma50,
        line=dict(color="#58a6ff", width=1.5, dash="dot"),
        name="SMA 50",
    ))

    fig.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font=dict(color="#8b949e", size=11),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            rangeslider=dict(visible=False),
            gridcolor="#21262d",
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor="#21262d",
            showgrid=True,
            zeroline=False,
            tickprefix="$",
            side="right",
        ),
        yaxis2=dict(
            overlaying="y",
            side="left",
            showgrid=False,
            showticklabels=False,
        ),
        legend=dict(
            bgcolor="#161b22",
            bordercolor="#30363d",
            borderwidth=1,
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#161b22", bordercolor="#30363d", font_color="#e6edf3"),
    )
    return fig


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <style>
      [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
      }
      [data-testid="stSidebar"] * { color: #e6edf3; }
      .sidebar-title {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: .14em;
        text-transform: uppercase;
        color: #8b949e;
        margin-bottom: 14px;
      }
      .sync-paused-banner {
        background: #3a2d0a;
        border: 1px solid #9e6a03;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 0.82rem;
        color: #d29922;
        margin-top: 10px;
        line-height: 1.5;
      }
      .sync-active-banner {
        background: #1a4429;
        border: 1px solid #238636;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 0.82rem;
        color: #3fb950;
        margin-top: 10px;
        line-height: 1.5;
      }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<p class="sidebar-title">Asset Selection</p>', unsafe_allow_html=True)
    
    # Stock selector dictionary (Symbol -> Display Name)
    STOCKS = {
        "^GSPC": "S&P 500 Index",
        "NVDA": "NVIDIA Corp.",
        "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corp."
    }
    
    selected_symbol = st.selectbox(
        "Choose an asset to view:",
        options=list(STOCKS.keys()),
        format_func=lambda x: STOCKS[x],
        index=0 # ^GSPC is the default
    )
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="sidebar-title">System Control</p>', unsafe_allow_html=True)

    # Read current persisted state (default True if key missing)
    _current_data = load_ai_analysis(selected_symbol) or {}
    _persisted = bool(_current_data.get("sync_enabled", True))

    sync_enabled = st.toggle("Enable Daily AI Analysis", value=_persisted)

    # Persist whenever the user flips the toggle
    if sync_enabled != _persisted:
        save_sync_enabled(sync_enabled, selected_symbol)

    if sync_enabled:
        st.markdown(
            '<div class="sync-active-banner">AI Sync is <strong>ACTIVE</strong><br>'
            'Daily analysis will run as scheduled.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="sync-paused-banner">AI Sync is currently <strong>PAUSED</strong> '
            'to save tokens.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<p class="sidebar-title">About</p>', unsafe_allow_html=True)
    st.caption("AI Stock Dashboard · Data via Yahoo Finance · Signals via AI analysis")


# ── Main ───────────────────────────────────────────────────────────────────────
with st.spinner(f"Fetching live data for {selected_symbol}…"):
    try:
        info, hist = fetch_ticker_data(selected_symbol)
    except Exception as e:
        st.error(f"Could not fetch data from Yahoo Finance: {e}")
        st.stop()

short_name = info.get("shortName", STOCKS[selected_symbol])
exchange = info.get("exchange", "INDEX" if selected_symbol.startswith("^") else "NASDAQ")
currency = info.get("currency", "USD")

st.markdown(f"""
<div class="ticker-header">
  <span class="ticker-name">{short_name} <span style="color:#58a6ff">{selected_symbol}</span></span>
  <span class="ticker-sub">{exchange} · {currency}</span>
</div>
""", unsafe_allow_html=True)

# ── Key Metrics Row ────────────────────────────────────────────────────────────
price        = info.get("currentPrice") or info.get("regularMarketPrice", 0)
prev_close   = info.get("previousClose", price)
change       = price - prev_close
pct_change   = (change / prev_close * 100) if prev_close else 0
delta_str    = f"{change:+.2f}  ({pct_change:+.2f}%)"

market_cap   = info.get("marketCap", 0)
mc_str       = f"${market_cap/1e12:.2f}T" if market_cap >= 1e12 else f"${market_cap/1e9:.1f}B"

vol_today    = info.get("volume", 0)
avg_vol      = info.get("averageVolume", 1)
vol_str      = f"{vol_today/1e6:.1f}M"
avg_vol_str  = f"{avg_vol/1e6:.1f}M"

wk52_high    = info.get("fiftyTwoWeekHigh", 0)
wk52_low     = info.get("fiftyTwoWeekLow", 0)
pe_ratio     = info.get("trailingPE", 0)
eps          = info.get("trailingEps", 0)
beta         = info.get("beta", 0)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Current Price",    f"${price:,.2f}",   delta_str)
col2.metric("Market Cap",       mc_str)
col3.metric("Volume",           vol_str,            f"Avg {avg_vol_str}")
col4.metric("52-Week Range",    f"${wk52_low:.0f} – ${wk52_high:.0f}")
col5.metric("P/E  |  EPS",      f"{pe_ratio:.1f}  |  ${eps:.2f}",  f"Beta {beta:.2f}")

st.markdown('<hr>', unsafe_allow_html=True)

# ── Chart + AI Card ────────────────────────────────────────────────────────────
chart_col, ai_col = st.columns([3, 1], gap="large")

with chart_col:
    st.markdown('<p class="section-title">6-Month Candlestick Chart</p>', unsafe_allow_html=True)
    if hist.empty:
        st.warning("No historical data available.")
    else:
        st.plotly_chart(build_candlestick(hist), use_container_width=True, config={"displayModeBar": False})

with ai_col:
    st.markdown('<p class="section-title">AI Market Analysis</p>', unsafe_allow_html=True)
    analysis = load_ai_analysis(selected_symbol)

    if not sync_enabled:
        st.markdown("""
        <div class="ai-card ai-card-wait">
          <div class="ai-label">Status</div>
          <div class="ai-wait" style="color:#d29922">AI Sync is currently PAUSED to save tokens.</div>
          <div class="ai-summary" style="margin-top:10px">
            Re-enable <em>Daily AI Analysis</em> in the sidebar to resume automatic signals.
          </div>
        </div>
        """, unsafe_allow_html=True)
    elif analysis:
        # Handle title case or lowercase from the updated prompt
        signal_raw = analysis.get("Signal", analysis.get("signal", "HOLD"))
        signal = str(signal_raw).upper()
        
        # Handle decimal (0.8) or string ("8/10")
        conf_raw = analysis.get("Confidence Score", analysis.get("confidence", 0.5))
        if isinstance(conf_raw, str) and "/" in conf_raw:
            try:
                confidence = float(conf_raw.split("/")[0]) / 10.0
            except:
                confidence = 0.5
        elif isinstance(conf_raw, str):
            try:
                confidence = float(conf_raw.replace("%", ""))
                if confidence > 1: confidence /= 100
            except:
                confidence = 0.5
        else:
            confidence = float(conf_raw)

        summary    = analysis.get("Summary", analysis.get("summary", "No summary provided."))
        expected_move = analysis.get("expected_move", "")
        timestamp  = analysis.get("timestamp", "")
        
        color      = color_for_signal(signal)
        pct        = int(confidence * 100) if confidence <= 1 else int(confidence)

        move_html = f'<div style="text-align:right"><div class="ai-label">Exp. Move</div><div style="font-size:1.15rem;font-weight:800;color:#e6edf3;">{expected_move}</div></div>' if expected_move else ""
        time_html = f'<div style="color:#484f58;font-size:0.7rem;margin-top:12px;text-align:right">Updated: {timestamp}</div>' if timestamp else ""

        st.markdown(f"""
        <div class="ai-card ai-card-{color}">
          <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
              <div class="ai-label">Signal</div>
              <span class="signal-badge badge-{color}">{signal}</span>
            </div>
            {move_html}
          </div>

          <div class="ai-label">Confidence</div>
          <div style="font-size:1.4rem;font-weight:700;color:#e6edf3">{pct}%</div>
          <div class="confidence-bar-bg">
            <div class="confidence-bar-fill fill-{color}" style="width:{pct}%"></div>
          </div>

          <div class="ai-label">Summary</div>
          <div class="ai-summary">{summary}</div>
          {time_html}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="ai-card ai-card-wait">
          <div class="ai-label">Signal</div>
          <div class="ai-wait">Waiting for daily AI market analysis…</div>
          <div class="ai-summary" style="margin-top:12px">
            The background script will generate insights for <strong>{selected_symbol}</strong> on its next scheduled run.
          </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<hr>', unsafe_allow_html=True)

# ── Additional Stats Row ───────────────────────────────────────────────────────
st.markdown('<p class="section-title">Fundamentals</p>', unsafe_allow_html=True)

f1, f2, f3, f4, f5, f6 = st.columns(6)
f1.metric("Open",           f"${info.get('open', 0):,.2f}")
f2.metric("Day High",       f"${info.get('dayHigh', 0):,.2f}")
f3.metric("Day Low",        f"${info.get('dayLow',  0):,.2f}")
f4.metric("Prev Close",     f"${prev_close:,.2f}")
f5.metric("Dividend Yield", f"{(info.get('dividendYield') or 0)*100:.2f}%")
f6.metric("Analyst Target", f"${info.get('targetMeanPrice', 0):,.2f}")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<p class="last-updated">Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  ·  Data via Yahoo Finance</p>',
    unsafe_allow_html=True,
)
