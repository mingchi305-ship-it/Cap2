import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 1. 頁面設定
st.set_page_config(page_title="Capsir 穩定監控版", layout="wide")
st.title("📊 Capsir 股票策略看板 (FinMind 穩定版)")

# 2. 側邊欄
with st.sidebar:
    st.header("⚙️ 策略參數")
    ratio = st.slider("黃金分割係數", 0.0, 1.0, 0.618, 0.001)
    heat_threshold = st.slider("過熱警戒 (%)", 5, 20, 10) / 100

# 3. 持股資料
df = pd.DataFrame([
    {"股票代碼": "0050", "入手價格": 68.7},
    {"股票代碼": "0052", "入手價格": 40.67},
    {"股票代碼": "006208", "入手價格": 109.08},
    {"股票代碼": "00888", "入手價格": 68.7},
])

# 4. 備援數據源：FinMind API (抓取台股最穩定)
@st.cache_data(ttl=3600)
def get_taiwan_stock(code):
    try:
        url = "https://api.finmindtrade.com/api/v4/data"
        # 抓取過去 120 天資料確保 MA20 計算
        start_date = (datetime.today() - timedelta(days=120)).strftime("%Y-%m-%d")
        params = {
            "dataset": "TaiwanStockPrice",
            "data_id": code,
            "start_date": start_date
        }
        res = requests.get(url, params=params, timeout=15).json()
        data = res.get("data", [])
        
        if not data:
            return None, None, None
            
        temp_df = pd.DataFrame(data)
        temp_df["close"] = temp_df["close"].astype(float)
        
        price = temp_df["close"].iloc[-1]
        ma20 = temp_df["close"].rolling(20).mean().iloc[-1]
        high52 = temp_df["close"].max()
        
        return price, ma20, high52
    except:
        return None, None, None

# 5. 抓取資料
with st.spinner('切換至 FinMind 備援線路中...'):
    results = [get_taiwan_stock(c) for c in df["股票代碼"]]
    df[["現價", "MA20", "52週高點"]] = pd.DataFrame(results, index=df.index)

# 6. 策略計算 (加入空值檢查)
df["支撐下限"] = df.apply(lambda r: r["現價"] * (1 - (1 - ratio) * ((r["現價"] - r["入手價格"]) / r["現價"])) if pd.notnull(r["現價"]) else None, axis=1)
df["獲利績效"] = (df["現價"] - df["入手價格"]) / df["入手價格"]
df["K線乖離率"] = (df["現價"] - df["MA20"]) / df["MA20"]

# 7. 狀態與顏色
def judge_status(row):
    if pd.isna(row["現價"]): return "⚠️ 供應商異常"
    if row["現價"] < row["支撐下限"]: return "🚨 結構破壞"
    if row["K線乖離率"] > heat_threshold: return "🔥 過熱警戒"
    if row["現價"] > row["MA20"]: return "🚀 強勢續抱"
    return "👀 觀察"

df["目前狀態判斷"] = df.apply(judge_status, axis=1)

def color_status(val):
    color = 'transparent'
    if '🚨' in val: color = '#FF4B4B'
    elif '🚀' in val: color = '#28A745'
    elif '🔥' in val: color = '#FFA500'
    return f'background-color: {color}; color: white' if color != 'transparent' else ''

# 8. 顯示表格
st.subheader("📋 即時監控清單")
format_dict = {
    "現價": "{:.2f}", "MA20": "{:.2f}", "52週高點": "{:.2f}",
    "支撐下限": "{:.2f}", "獲利績效": "{:.2%}", "K線乖離率": "{:.2%}"
}

st.dataframe(
    df.style.map(color_status, subset=['目前狀態判斷']).format(format_dict, na_rep="-"),
    use_container_width=True
)

st.caption(f"數據源：FinMind API | 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
