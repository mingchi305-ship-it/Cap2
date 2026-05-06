import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
from datetime import datetime, timedelta

# 1. 頁面設定與標題
st.set_page_config(page_title="Capsir 策略看板", layout="wide")
st.title("📊 Capsir +350W capacity（Improve version）")

# 2. 側邊欄：讓你的策略可以動態調整 (不需要改程式碼)
with st.sidebar:
    st.header("⚙️ 策略參數設定")
    ratio = st.slider("黃金分割係數", 0.0, 1.0, 0.618, 0.001)
    heat_threshold = st.slider("乖離率過熱警戒 (%)", 5, 20, 10) / 100
    st.info(f"當前支撐邏輯：基於 {ratio} 進行計算")

# 3. 使用者持股資料 (建議未來可改為讀取 CSV 或 Excel)
stocks = [
    {"股票代碼": "0050", "入手價格": 68.7},
    {"股票代碼": "0052", "入手價格": 40.67},
    {"股票代碼": "006208", "入手價格": 109.08},
    {"股票代碼": "00888", "入手價格": 68.7},
]
df = pd.DataFrame(stocks)

# 4. 資料抓取邏輯 (優化 yfinance 判斷)
@st.cache_data(ttl=300)
def get_clean_data(code):
    # 自動判斷上市 (.TW) 或 上櫃 (.TWO)
    # 簡單邏輯：5碼(含)以上通常為權證或特定標的，這裡以一般台股為主
    for suffix in [".TW", ".TWO"]:
        symbol = f"{code}{suffix}"
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="3mo")
            if not hist.empty:
                price = hist["Close"].iloc[-1]
                ma20 = hist["Close"].rolling(20).mean().iloc[-1]
                high52 = stock.info.get("fiftyTwoWeekHigh", price)
                return price, ma20, high52
        except:
            continue
    return None, None, None

# 5. 執行數據抓取
with st.spinner('正在獲取最新市場報價...'):
    results = [get_clean_data(c) for c in df["股票代碼"]]
    df[["現價", "MA20", "52週高點"]] = pd.DataFrame(results, index=df.index)

# 6. 策略計算 (套用側邊欄參數)
df["支撐下限"] = df["現價"] * (1 - (1 - ratio) * ((df["現價"] - df["入手價格"]) / df["現價"].replace(0, 1)))
df["獲利績效"] = (df["現價"] - df["入手價格"]) / df["入手價格"]
df["K線乖離率"] = (df["現價"] - df["MA20"]) / df["MA20"]

# 7. 狀態判定邏輯
def judge_status(row):
    if pd.isna(row["現價"]): return "⚠️ 無資料"
    if row["現價"] < row["支撐下限"]: return "🚨 結構破壞：減碼"
    if row["K線乖離率"] > heat_threshold: return "🔥 過熱警戒"
    if row["現價"] > row["MA20"]: return "🚀 強勢續抱"
    return "👀 觀察"

df["目前狀態判斷"] = df.apply(judge_status, axis=1)

# 8. 視覺化顯示 (加上顏色標記)
def color_status(val):
    color = 'white'
    if '🚨' in val: color = '#FF4B4B' # 紅色
    elif '🚀' in val: color = '#28A745' # 綠色
    elif '🔥' in val: color = '#FFA500' # 橘色
    return f'background-color: {color}; color: white'

st.subheader("📋 即時監控清單")

# 8. 視覺化顯示 (優化後的顯示邏輯，防止 None 導致當機)
def color_status(val):
    color = 'white'
    if '🚨' in val: color = '#FF4B4B'
    elif '🚀' in val: color = '#28A745'
    elif '🔥' in val: color = '#FFA500'
    return f'background-color: {color}; color: white'

st.subheader("📋 即時監控清單")

# 先建立一個格式化字典，只有數值不是 None 的才套用
# 這樣可以避免 TypeError
format_dict = {}
for col in ["現價", "MA20", "52週高點", "支撐下限"]:
    format_dict[col] = lambda x: f"{x:.2f}" if pd.notnull(x) else "-"

for col in ["獲利績效", "K線乖離率"]:
    format_dict[col] = lambda x: f"{x:.2%}" if pd.notnull(x) else "-"

st.dataframe(
    df.style.map(color_status, subset=['目前狀態判斷'])
    .format(format_dict),
    use_container_width=True,
    height=400
)
