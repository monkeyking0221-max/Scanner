import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os

st.set_page_config(page_title="ASX 投研中心", layout="wide")

# --- 1. 数据持久化逻辑 ---
CONFIG_FILE = "long_term_list.json"

def load_list():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: return ["CBA", "BHP", "CSL"]
    return ["CBA", "BHP", "CSL"]

def save_list(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

# --- 2. 核心分析函数 ---
def analyze_stock(ticker):
    try:
        symbol = ticker.strip().upper()
        if not (symbol.endswith(".AX") or "." in symbol):
            symbol += ".AX"
        
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # 提取财务指标
        roe = info.get('returnOnEquity', 0) or 0
        op_margin = info.get('operatingMargins', 0) or 0
        fcf = info.get('freeCashflow', 0) or 0
        debt_to_equity = info.get('debtToEquity', 0) or 0
        pe = info.get('trailingPE', None)
        div_yield = info.get('dividendYield', 0) or 0
        rev_growth = info.get('revenueGrowth', 0) or 0

        # 评分
        score = sum([roe > 0.15, op_margin > 0.10, fcf > 0, 0 < debt_to_equity < 100])

        return {
            "代码": symbol,
            "综合评分": score,
            "ROE": f"{roe*100:.1f}%",
            "利润率": f"{op_margin*100:.1f}%",
            "负债权益比": f"{debt_to_equity:.1f}%",
            "自由现金流": f"${fcf/1e6:.1f}M" if fcf != 0 else "N/A",
            "PE": round(pe, 1) if pe else "N/A",
            "股息率": f"{div_yield*100:.1f}%",
            "营收增长": f"{rev_growth*100:.1f}%"
        }
    except: return None

# --- 3. 页面导航 ---
st.title("🛡️ ASX 投资研究中心")
tab1, tab2, tab3 = st.tabs(["🎯 临时单股体检", "表 长期关注清单", "⚙️ 列表管理"])

# --- Tab 1: 临时单股分析 (隐掉其他干扰) ---
with tab1:
    st.subheader("输入代码进行快速分析")
    manual_input = st.text_input("输入股票代码 (如: TLS, RIO, NVDA)", key="manual")
    if st.button("开始分析", key="run_manual"):
        if manual_input:
            tickers = [x.strip() for x in manual_input.split(",")]
            results = [analyze_stock(t) for t in tickers]
            df = pd.DataFrame([r for r in results if r])
            if not df.empty:
                st.dataframe(df, use_container_width=True)
            else:
                st.error("未能获取数据，请检查代码。")
        else:
            st.info("请先输入股票代码")

# --- Tab 2: 长期关注清单 (只看结果) ---
with tab2:
    st.subheader("我的长期关注池体检表")
    fav_list = load_list()
    if st.button("刷新并运行长期池分析"):
        progress = st.progress(0)
        results = []
        for i, t in enumerate(fav_list):
            res = analyze_stock(t)
            if res: results.append(res)
            progress.progress((i+1)/len(fav_list))
        
        df_fav = pd.DataFrame(results)
        if not df_fav.empty:
            st.dataframe(df_fav.sort_values("综合评分", ascending=False), use_container_width=True)
        else:
            st.warning("列表为空或无法获取数据")

# --- Tab 3: 列表管理 (增删改) ---
with tab3:
    st.subheader("管理你的长期关注列表")
    fav_list = load_list()
    # 编辑器
    df_editor = pd.DataFrame({"代码": fav_list})
    edited_df = st.data_editor(df_editor, num_rows="dynamic", use_container_width=True)
    
    if st.button("同步修改到云端"):
        new_list = edited_df["代码"].dropna().str.upper().str.strip().tolist()
        save_list(new_list)
        st.success("列表更新成功！请前往“长期关注清单”标签运行分析。")
