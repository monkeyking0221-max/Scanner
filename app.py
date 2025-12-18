import streamlit as st
import yfinance as yf
import pandas as pd
import os
import json

st.set_page_config(page_title="ASX 投研中心", layout="wide")

# --- 获取所有可用年份的财务数据 ---
def get_extended_analysis(ticker):
    try:
        symbol = ticker.strip().upper()
        if not (symbol.endswith(".AX") or "." in symbol):
            symbol += ".AX"
        
        stock = yf.Ticker(symbol)
        
        # 获取年度报表
        fin = stock.financials
        bs = stock.balance_sheet
        cf = stock.cashflow
        
        if fin.empty:
            return None, "未找到财报数据"

        # 自动识别所有可用财年 (yfinance 通常提供 4 年)
        available_years = fin.columns
        history_data = []

        for year in available_years:
            try:
                # 使用 .get() 或 index 检查防止崩溃
                net_income = fin.loc['Net Income', year]
                revenue = fin.loc['Total Revenue', year]
                equity = bs.loc['Stockholders Equity', year]
                fcf = cf.loc['Free Cash Flow', year] if 'Free Cash Flow' in cf.index else 0
                
                roe = net_income / equity if equity != 0 else 0
                margin = net_income / revenue if revenue != 0 else 0
                
                history_data.append({
                    "财年": year.strftime('%Y'),
                    "营收 (M)": round(revenue/1e6, 2),
                    "净利 (M)": round(net_income/1e6, 2),
                    "ROE": f"{roe*100:.2f}%",
                    "利润率": f"{margin*100:.2f}%",
                    "自由现金流 (M)": round(fcf/1e6, 2)
                })
            except Exception as e:
                continue
            
        return pd.DataFrame(history_data), symbol
    except Exception as e:
        return None, str(e)

# --- 页面排版 ---
st.title("🛡️ ASX 深度投研中心")

# 侧边栏：管理长期列表 (保持你喜欢的排版)
st.sidebar.title("⚙️ 设置")
if 'long_list' not in st.session_state:
    st.session_state.long_list = ["CBA.AX", "BHP.AX", "CSL.AX"]

# --- 主界面标签页 ---
tab1, tab2 = st.tabs(["🎯 单股深度体检 (多年度)", "📊 长期关注池概览"])

with tab1:
    target = st.text_input("输入代码 (如: CBA, REA, XRO)", key="single_search")
    if st.button("生成多年份对比报告") and target:
        with st.spinner("正在提取所有可用财报..."):
            df, full_name = get_extended_analysis(target)
            
            if df is not None:
                st.subheader(f"📊 {full_name} 历年财务表现")
                
                # 核心指标卡片
                c1, c2, c3 = st.columns(3)
                latest = df.iloc[0]
                c1.metric("最新 ROE", latest["ROE"])
                c2.metric("最新利润率", latest["利润率"])
                c3.metric("最新营收", f"${latest['营收 (M)']}M")
                
                # 数据表格
                st.dataframe(df, use_container_width=True)
                
                # 趋势图
                st.write("#### 📈 业绩增长趋势")
                chart_df = df.set_index("财年")[["营收 (M)", "净利 (M)"]].sort_index()
                st.line_chart(chart_df)
                
                
            else:
                st.error(f"无法获取数据。原因: {full_name}")

with tab2:
    st.write("此处展示你的长期关注列表最新简报...")
    # 之前批量分析的代码可以放在这里
