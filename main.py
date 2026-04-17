import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime, timedelta

# --- ページ設定 ---
st.set_page_config(
    page_title="Extreme Market Intelligence - Sovereign Edition",
    page_icon="🛡️",
    layout="wide",
)

# 極限デザイン
st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .news-card {
        background-color: #1e2130;
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 5px solid #00D4FF;
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }
    .sentiment-pos { color: #00ff88; font-weight: bold; }
    .sentiment-neg { color: #ff3366; font-weight: bold; }
    .sentiment-neu { color: #888888; font-weight: bold; }
    .metric-card {
        background: #161b22;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
</style>
""", unsafe_allow_html=True)

# --- 基本設定 ---
TICKERS_MAP = {
    "WTI原油": "CL=F",
    "北海ブレント原油": "BZ=F",
    "金": "GC=F",
    "銅": "HG=F",
    "USD/JPY": "JPY=X",
    "S&P 500": "^GSPC",
    "日経225": "^N225",
    "米国10年国債利回り": "^TNX",
    "VIX指数": "^VIX"
}

# --- テクニカル指標計算 ---
def calculate_indicators(df, col):
    # RSI
    delta = df[col].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # ATR (Simplified on Close)
    df['ATR'] = df[col].diff().abs().rolling(14).mean()
    
    # MA
    df['SMA20'] = df[col].rolling(20).mean()
    df['SMA50'] = df[col].rolling(50).mean()
    
    return df

# --- 予測ロジック ---
def generate_forecast(df, col, days=10):
    last_val = df[col].iloc[-1]
    last_date = df.index[-1]
    
    # 単純な線形回帰トレンド (直近30日)
    y = df[col].iloc[-30:].values
    x = np.arange(len(y))
    slope, intercept = np.polyfit(x, y, 1)
    
    # 予測日の生成
    forecast_dates = [last_date + timedelta(days=i) for i in range(1, days + 1)]
    forecast_vals = [last_val + (slope * i) for i in range(1, days + 1)]
    
    # ボラティリティに基づいた信頼区間 (2*STD)
    std = df[col].rolling(20).std().iloc[-1]
    upper_bound = [v + (std * np.sqrt(i) * 0.5) for i, v in enumerate(forecast_vals, 1)]
    lower_bound = [v - (std * np.sqrt(i) * 0.5) for i, v in enumerate(forecast_vals, 1)]
    
    return forecast_dates, forecast_vals, upper_bound, lower_bound

# --- バックテストエンジン ---
def run_backtest(df, col, short_w, long_w):
    temp = df[[col]].copy()
    temp['SMA_S'] = temp[col].rolling(short_w).mean()
    temp['SMA_L'] = temp[col].rolling(long_w).mean()
    
    # シグナル: S > L なら 1(保持), Else 0
    temp['Signal'] = np.where(temp['SMA_S'] > temp['SMA_L'], 1, 0)
    temp['Returns'] = temp[col].pct_change()
    temp['Strategy_Returns'] = temp['Signal'].shift(1) * temp['Returns']
    
    # 累積利益
    temp['Cumulative_Market'] = (1 + temp['Returns']).cumprod()
    temp['Cumulative_Strategy'] = (1 + temp['Strategy_Returns']).cumprod()
    
    return temp

# --- データ取得・キャッシュ ---
@st.cache_data(ttl=3600)
def load_all_data(tickers_dict, period):
    tickers_list = list(tickers_dict.values())
    df_raw = yf.download(tickers_list, period=period)
    df = df_raw["Close"].copy()
    reverse_map = {v: k for k, v in tickers_dict.items()}
    df.rename(columns=reverse_map, inplace=True)
    if "WTI原油" in df.columns and "USD/JPY" in df.columns:
        df["WTI原油(円)"] = df["WTI原油"] * df["USD/JPY"]
    return df.ffill().dropna()

@st.cache_data(ttl=86400)
def fetch_news_cached(ticker_name):
    symbol = TICKERS_MAP.get(ticker_name, "CL=F")
    try: return yf.Ticker(symbol).news[:10]
    except: return []

@st.cache_data(ttl=86400)
def get_seasonal_stats_cached(ticker_name):
    symbol = TICKERS_MAP.get(ticker_name, "CL=F")
    df_long = yf.download(symbol, period="20y")
    if df_long.empty: return None
    df_long['Month'] = df_long.index.month
    df_long['Return'] = df_long['Close'].pct_change()
    monthly = df_long.groupby('Month')['Return'].agg(['mean', 'std']).reset_index()
    win_rates = [(df_long[df_long['Month']==m]['Return'] > 0).mean() for m in range(1, 13)]
    monthly['win_rate'] = win_rates
    return monthly

# --- メインコンテンツ ---
st.sidebar.title("🛡️ Sovereign Hub")
period = st.sidebar.selectbox("分析期間", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)
selected_tickers = st.sidebar.multiselect("ウォッチリスト", list(TICKERS_MAP.keys()), ["WTI原油", "金", "日経225", "S&P 500"])

df_core = load_all_data(TICKERS_MAP, period)

st.title("🛡️ Extreme Sovereign Intelligence")
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📰 Intelligence", "📅 Seasonality", "🔬 Strategy & Forecast"])

# --- Tab 1 & 2 & 3 (既存機能を維持しつつ最適化) ---
with tab1:
    cols = st.columns(len(selected_tickers[:4]))
    for i, t in enumerate(selected_tickers[:4]):
        if t in df_core.columns:
            cur, prev = df_core[t].iloc[-1], df_core[t].iloc[-2]
            cols[i].metric(t, f"{cur:,.2f}", f"{((cur-prev)/prev)*100:.2f}%")
    st.markdown("---")
    main_t = st.selectbox("トレンド分析対象", selected_tickers)
    df_ta = calculate_indicators(df_core[[main_t]].copy(), main_t)
    fig_m = go.Figure()
    fig_m.add_trace(go.Scatter(x=df_ta.index, y=df_ta[main_t], name="価格", line=dict(color='#00D4FF', width=2)))
    fig_m.add_trace(go.Scatter(x=df_ta.index, y=df_ta['SMA20'], name="20MA", line=dict(dash='dash', color='orange')))
    fig_m.update_layout(template="plotly_dark", height=400)
    st.plotly_chart(fig_m, use_container_width=True)

with tab2:
    news_t = st.selectbox("ニュース", selected_tickers, key="nt")
    items = fetch_news_cached(news_t)
    for it in items:
        st.markdown(f'<div class="news-card"><strong>{it.get("publisher")}</strong><br><a href="{it.get("link")}" style="color:white;">{it.get("title")}</a></div>', unsafe_allow_html=True)

with tab3:
    sea_t = st.selectbox("季節性", list(TICKERS_MAP.keys()), key="st")
    stats = get_seasonal_stats_cached(sea_t)
    if stats is not None:
        fig_s = px.bar(stats, x='Month', y='mean', color='mean', color_continuous_scale="RdBu_r", template="plotly_dark")
        st.plotly_chart(fig_s, use_container_width=True)

# --- Tab 4: Strategy & Forecast (NEW) ---
with tab4:
    st.subheader("🔬 未来予測 & 戦略バックテスト")
    strat_t = st.selectbox("検証铭柄", selected_tickers, key="strat_t")
    
    c_f1, c_f2 = st.columns([2, 1])
    
    with c_f1:
        st.markdown("##### 🚀 トレンドプロジェクション (10日予測)")
        df_f = df_core[[strat_t]].copy()
        f_dates, f_vals, f_upper, f_lower = generate_forecast(df_f, strat_t)
        
        fig_f = go.Figure()
        # 過去データ
        fig_f.add_trace(go.Scatter(x=df_f.index[-60:], y=df_f[strat_t].iloc[-60:], name="実績", line=dict(color="#00D4FF")))
        # 予測エリア
        fig_f.add_trace(go.Scatter(x=f_dates, y=f_upper, line=dict(width=0), showlegend=False))
        fig_f.add_trace(go.Scatter(x=f_dates, y=f_lower, fill='tonexty', fillcolor='rgba(0,212,255,0.1)', line=dict(width=0), showlegend=False))
        # 予測線
        fig_f.add_trace(go.Scatter(x=f_dates, y=f_vals, name="予測トレンド", line=dict(color="#00D4FF", dash='dot')))
        
        fig_f.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_f, use_container_width=True)
        st.caption("※統計的トレンドに基づく予測であり、実際の値動きを保証するものではありません。")

    with c_f2:
        st.markdown("##### 🛡️ リスク・センチネル")
        # RSI表示
        df_ind = calculate_indicators(df_core[[strat_t]].copy(), strat_t)
        rsi = df_ind['RSI'].iloc[-1]
        st.metric("RSI (14日)", f"{rsi:.1f}", 
                  "買われすぎ" if rsi > 70 else "売られすぎ" if rsi < 30 else "ニュートラル")
        
        # ボラティリティ (ATR)
        atr = df_ind['ATR'].iloc[-1]
        st.metric("ATR (直近ボラティリティ)", f"{atr:.2f}")
        
        # VIX診断
        if "VIX指数" in df_core.columns:
            vix = df_core["VIX指数"].iloc[-1]
            risk_status = "Risk OFF (警戒)" if vix > 25 else "Risk ON (強気)" if vix < 15 else "Normal"
            st.info(f"現在の市場環境: **{risk_status}** (VIX: {vix:.2f})")

    st.markdown("---")
    st.subheader("🧪 売買戦略シミュレーター (MA Crossover)")
    
    col_s1, col_s2 = st.columns([1, 3])
    with col_s1:
        s_win = st.slider("短期MA", 5, 25, 10)
        l_win = st.slider("長期MA", 25, 75, 20)
        if s_win >= l_win: st.error("短期MAは長期MAより小さくしてください")
        
    res = run_backtest(df_core, strat_t, s_win, l_win)
    
    with col_s2:
        fig_res = go.Figure()
        fig_res.add_trace(go.Scatter(x=res.index, y=res['Cumulative_Market'], name="バイ・アンド・ホールド", line=dict(color="gray")))
        fig_res.add_trace(go.Scatter(x=res.index, y=res['Cumulative_Strategy'], name="MAクロス戦略", line=dict(color="#00D4FF", width=2)))
        fig_res.update_layout(template="plotly_dark", height=350, title="累積リターン比較")
        st.plotly_chart(fig_res, use_container_width=True)
        
    # パフォーマンスサマリー
    p1, p2, p3 = st.columns(3)
    final_ret = (res['Cumulative_Strategy'].iloc[-1] - 1) * 100
    win_rate = (res['Strategy_Returns'] > 0).mean() * 100
    p1.markdown(f'<div class="metric-card">総利益<br><span style="font-size:1.5rem; color:#00D4FF;">{final_ret:.1f}%</span></div>', unsafe_allow_html=True)
    p2.markdown(f'<div class="metric-card">勝率<br><span style="font-size:1.5rem; color:#00D4FF;">{win_rate:.1f}%</span></div>', unsafe_allow_html=True)
    p3.markdown(f'<div class="metric-card">対市場優位性<br><span style="font-size:1.5rem; color:#00D4FF;">{final_ret - (res["Cumulative_Market"].iloc[-1]-1)*100:.1;f}%</span></div>', unsafe_allow_html=True)

st.sidebar.markdown("---")
if st.sidebar.button("キャッシュクリア"):
    st.cache_data.clear()
    st.rerun()