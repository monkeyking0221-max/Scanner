import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os

# --- 页面设置 ---
st.set_page_config(page_title="ASX 价值投研中心", layout="wide")

# --- 核心函数：获取3年财报数据 ---
def get_historical_analysis(ticker):
    try:
        symbol = ticker.strip().upper()
        if not (symbol.endswith(".AX") or "." in symbol):
            symbol += ".AX"
        
        stock = yf.Ticker(symbol)
        
        # 获取年度损益表和资产负债表
        financials = stock.financials  # 损益表
        balance_sheet = stock.balance_sheet # 资产负债表
        cashflow = stock.cashflow # 现金流量表
        
        if financials.empty or balance_sheet.empty:
            return None, "无法获取财务报表数据"

        # 截取最近3个财年
        years = financials.columns[:3]
        history_data = []

        for year in years:
            try:
                net_income = financials.loc['Net Income', year]
                revenue = financials.loc['Total Revenue', year]
                equity = balance_sheet.loc['Stockholders Equity', year]
                fcf = cashflow.loc['Free Cash Flow', year] if 'Free Cash Flow' in cashflow.index else 0
                
                roe = net_income / equity if equity != 0 else 0
                margin = net_income / revenue if revenue != 0 else 0
                
                history_data.append({
                    "财年": year.strftime('%Y'),
                    "营收 (M)": f"{revenue/1e6:.1f}",
                    "净利 (M)": f"{net_income/1e6:.1f}",
                    "ROE": f"{roe*100:.2f}%",
                    "利润率": f"{margin*100:.2f}%",
                    "自由现金流 (M)": f"{fcf/1e6:.1f}"
                })
            except: continue
            
        return pd.DataFrame(history_data), symbol
    except Exception as e:
        return None, str(e)

# --- 页面排版 ---
st.title("🐱 ASX 价值投资研究中心")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🎯 单股 3 年深度体检", "📊 长期关注池概览", "⚙️ 列表管理"])

# --- TAB 1: 单股深度分析 ---
with tab1:
    col_l, col_r = st.columns([1, 2])
    with col_l:
        target = st.text_input("输入代码 (如: CBA, BHP)", key="single_t")
        analyze_btn = st.button("生成深度报告")
    
    if analyze_btn and target:
        with st.spinner("正在提取过去 3 年财报..."):
            df_hist, full_symbol = get_historical_analysis(target)
            if df_hist is not None:
                st.success(f"已分析: {full_symbol}")
                # 使用大字报展示最新 ROE
                latest_roe = df_hist.iloc[0]['ROE']
                st.metric("最新财年 ROE", latest_roe)
                
                st.write("#### 📅 过去 3 个财年财务摘要")
                st.table(df_hist) # 使用 table 显示更清晰
                
                # 可视化趋势
                st.write("#### 📈 业绩趋势")
                chart_data = df_hist.set_index("财年")[["营收 (M)", "净利 (M)"]].astype(float)
                st.bar_chart(chart_data)
            else:
                st.error(f"分析失败: {full_symbol}")

# --- TAB 2: 长期关注池 (保持简版扫描) ---
with tab2:
    # 这里复用之前的扫描逻辑，但建议加上 time.sleep(1) 防止被封
    st.info("此页面展示长期关注池的最新实时评分。")
    # (此处插入你之前的批量分析代码...)

# --- TAB 3: 列表管理 ---
with tab3:
    st.subheader("管理长期清单")
    # (此处插入你之前的 json 读写和 data_editor 代码...)
