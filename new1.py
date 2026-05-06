import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
from datetime import datetime, timedelta

# 1. 頁面基礎設定
st.set_page_config(page_title="Capsir 專業監控看板", layout="wide")
st.title("📊 Capsir 股票策略看板（專業穩定版）")

# 2. 側邊欄：動態參數調整 (讓你的策略更有彈性)
with st.sidebar:
    st.header("⚙️ 策略參數設定")
    ratio = st.slider("黃金分割係數", 0.0, 1.0, 0.618, 0.001)
    heat_threshold = st.slider("乖離率過熱警戒 (%)", 5, 20, 10) / 100
    st.info(f"當前支撐邏輯：基於 {ratio} 進行計算")

# 3. 使用者持股資料
stocks = [
    {"股票代碼": "0050", "入手價格": 68.7},
    {"股票代碼": "0052", "入手價格": 40.67},
    {"股票 Ledger": "006208", "入手價格": 109.08}, # 修正名稱以符合邏輯
    {"股票代碼": "00888", "入手價格": 68.7},
]
# 統一欄位名稱
df = pd.DataFrame([
    {"股票代碼": "0050", "入手價格": 68.7},
    {"股票代碼": "0052", "入手價格": 40.67},
    {"股票代碼": "006208", "入手價格": 109.08},
    {"股票代碼": "00888", "入手價格": 68.7},
])

# 4. 資料抓取邏輯 (含盤後容錯與自動後退機制)
@st.cache_data(ttl=300)
def get_stock_data_pro(code):
    # 自動嘗試上市 (.TW) 或 上櫃 (.TWO)
    for suffix in [".TW", ".TWO"]:
        symbol = f"{code}{suffix}"
        try:
            stock = yf.Ticker(symbol)
            # 抓取 3 個月的資料以確保有足夠樣本計算 MA20
            hist = stock.history(period="3mo")
            
            # 🔥 關鍵優化：移除所有空行，確保 iloc[-1] 抓到的是有交易的最近一天
            hist = hist.dropna()
            
            if not hist.empty:
                price = hist["Close"].iloc[-1]
                ma20 = hist["Close"].rolling(20).mean().iloc[-1]
                
                # 取得 52 週高點 (優先從 info 拿，拿不到就從歷史紀錄找最大值)
                high52 = stock.info.get("fiftyTwoWeekHigh")
                if pd.isna(high52):
                    high52 = hist["Close"].max()
                
                return price, ma20, high52
        except:
            continue
    return None, None, None

# 5. 執行批次抓取
with st.spinner('正在獲取最新市場數據...'):
    results = [get_stock_data_pro(c) for c in df["股票代碼"]]
    df[["現價", "MA20", "52週高點"]] = pd.DataFrame(results, index=df.index)
    # 模擬稍微停頓防止 API 鎖定
    time.sleep(0.1)

# 6. 策略計算邏輯
# 避免除以零的錯誤
df["現價_temp"] = df["現價"].replace(0, 1).fillna(1) 
df["支撐下限"] = df["現價"] * (1 - (1 - ratio) * ((df["現價"] - df["入手價格"]) / df["現價_temp"]))
df["獲利績效"] = (df["現價"] - df["入手價格"]) / df["入手價格"]
df["K線乖離率"] = (df["現價"] - df["MA20"]) / df["MA20"]

# 7. 狀態判定與顏色定義
def judge_status(row):
    if pd.isna(row["現價"]): return "⚠️ 無資料"
    if row["現價"] < row["支撐下限"]: return "🚨 結構破壞：減碼"
    if row["K線乖離率"] > heat_threshold: return "🔥 過熱警戒"
    if row["現價"] > row["MA20"]: return "🚀 強勢續抱"
    return "👀 觀察"

df["目前狀態判斷"] = df.apply(judge_status, axis=1)

def color_status(val):
    if not isinstance(val, str): return ""
    color = 'transparent'
    if '🚨' in val: color = '#FF4B4B' # 紅色
    elif '🚀' in val: color = '#28A745' # 綠色
    elif '🔥' in val: color = '#FFA500' # 橘色
    return f'background-color: {color}; color: white' if color != 'transparent' else ''

# 8. 視覺化輸出 (含 None 值安全格式化)
st.subheader("📋 即時監控清單")

# 安全格式化字典：若為 None 則顯示 "-"
format_dict = {}
for col in ["現價", "MA20", "52週高點", "支撐下限", "入手價格"]:
    format_dict[col] = lambda x: f"{x:.2f}" if pd.notnull(x) else "-"
for col in ["獲利績效", "K線乖離率"]:
    format_dict[col] = lambda x: f"{x:.2%}" if pd.notnull(x) else "-"

st.dataframe(
    df.drop(columns=["現價_temp"]).style.map(color_status, subset=['目前狀態判斷'])
    .format(format_dict),
    use_container_width=True,
    height=450
)

st.caption(f"系統狀態：運行正常 | 最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
