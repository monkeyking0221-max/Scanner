import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os

# --- 页面基础配置 ---
st.set_page_config(
    page_title="ASX 价值投资雷达",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 文件路径配置 ---
CONFIG_FILE = "long_term_list.json"

# --- 核心功能 1: 数据持久化 (保存你的关注列表) ---
def load_list():
    """加载关注列表，如果文件不存在则返回默认值"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                # 兼容旧格式，确保返回的是列表
                if isinstance(data, list): return data
                return ["CBA.AX", "BHP.AX", "CSL.AX"]
        except:
            return ["CBA.AX", "BHP.AX", "CSL.AX"]
    return ["CBA.AX", "BHP.AX", "CSL.AX"] # 默认初始股

def save_list(data_list):
    """保存列表到 JSON 文件"""
    # 简单的清洗：去重、去空、转大写
    clean_list = list(set([x.strip().upper() for x in data_list if x.strip()]))
    with open(CONFIG_FILE, "w") as f:
        json.dump(clean_list, f)

# 初始化 Session State
if 'fav_list' not in st.session_state:
    st.session_state.fav_list = load_list()

# --- 核心功能 2: 辅助函数 ---
def format_ticker(ticker):
    """自动补全 .AX 后缀"""
    ticker = ticker.strip().upper()
    # 如果没有后缀且没有点，默认为澳股
    if "." not in ticker:
        ticker += ".AX"
    return ticker

def safe_get(df, row_name, col_name):
    """安全地从 DataFrame 获取数据，防止报错"""
    try:
        if row_name in df.index:
            return df.loc[row_name, col_name]
    except:
        pass
    return 0

# --- 核心功能 3: 数据抓取引擎 ---

@st.cache_data(ttl=3600) # 缓存1小时，加快手机访问速度
def get_single_stock_deep_dive(ticker):
    """获取单只股票的深度历史数据（年报+半年报分开）"""
    symbol = format_ticker(ticker)
    stock = yf.Ticker(symbol)
    
    try:
        # 1. 获取基础信息 (用于实时价格和估值)
        info = stock.info
        
        # 2. 获取报表
        fin_annual = stock.financials
        fin_quarterly = stock.quarterly_financials
        
        # 内部函数：处理报表数据格式
        def process_financials(df_raw):
            if df_raw.empty: return None
            data = []
            # yfinance 的列名是时间戳，我们需要遍历它们
            for date_col in df_raw.columns:
                revenue = safe_get(df_raw, "Total Revenue", date_col)
                net_income = safe_get(df_raw, "Net Income", date_col)
                
                # 简单计算
                margin = (net_income / revenue * 100) if revenue else 0
                
                data.append({
                    "日期": date_col.strftime('%Y-%m-%d'),
                    "营收 (M)": f"{revenue/1e6:,.1f}", # 千分位格式化
                    "净利 (M)": f"{net_income/1e6:,.1f}",
                    "净利率": f"{margin:.2f}%",
                    # 原始数值用于画图
                    "_revenue_raw": revenue,
                    "_income_raw": net_income
                })
            return pd.DataFrame(data)

        df_ann = process_financials(fin_annual)
        df_qrt = process_financials(fin_quarterly)
        
        # 提取当前关键指标
        overview = {
            "当前价": info.get('currentPrice', 'N/A'),
            "PE (TTM)": info.get('trailingPE', 'N/A'),
            "股息率": f"{info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "N/A",
            "ROE": f"{info.get('returnOnEquity', 0)*100:.2f}%" if info.get('returnOnEquity') else "N/A",
            "行业": info.get('industry', 'N/A')
        }
        
        return overview, df_ann, df_qrt, symbol

    except Exception as e:
        return None, None, None, str(e)

def get_batch_scan_snapshot(ticker_list):
    """批量扫描列表的健康度（仅获取最新快照）"""
    results = []
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(ticker_list):
        try:
            symbol = format_ticker(ticker)
            stock = yf.Ticker(symbol)
            info = stock.info
            
            # 提取核心长线指标
            roe = info.get('returnOnEquity', 0) or 0
            debt_ratio = info.get('debtToEquity', 0) or 0
            fcf = info.get('freeCashflow', 0) or 0
            pe = info.get('trailingPE', 0)
            
            # 简单的巴菲特评分逻辑 (满分4分)
            score = 0
            if roe > 0.15: score += 1      # 赚钱效率高
            if fcf > 0: score += 1         # 真金白银入账
            if 0 < debt_ratio < 80: score += 1 # 负债可控
            if 0 < pe < 25: score += 1     # 估值不过分

            results.append({
                "代码": symbol,
                "评分": f"{score}/4",
                "ROE": f"{roe*100:.1f}%",
                "负债比": f"{debt_ratio:.1f}%",
                "PE": round(pe, 1) if pe else "N/A",
                "现金流": "正" if fcf > 0 else "负",
                "_score_raw": score # 用于排序
            })
        except:
            pass # 跳过获取失败的股票
        progress_bar.progress((i + 1) / len(ticker_list))
        
    return pd.DataFrame(results)

# --- 侧边栏：列表管理 ---
st.sidebar.title("⚙️ 投资池管理")
st.sidebar.info("在此编辑你的长期关注列表，数据会自动同步到云端。")

# 使用 Data Editor 进行增删改
current_df = pd.DataFrame(st.session_state.fav_list, columns=["股票代码"])
edited_df = st.sidebar.data_editor(current_df, num_rows="dynamic", use_container_width=True)

if st.sidebar.button("💾 保存列表修改"):
    new_list = edited_df["股票代码"].dropna().tolist()
    st.session_state.fav_list = new_list
    save_list(new_list)
    st.sidebar.success(f"已保存 {len(new_list)} 只股票！")

# --- 主界面 ---
st.title("🛡️ ASX 价值投资雷达")

# 两个主要功能区的标签页
tab1, tab2 = st.tabs(["🔍 单股深度体检 (含历史)", "📋 长期关注池监控"])

# --- TAB 1: 单股分析 ---
with tab1:
    st.markdown("#### 输入代码查看过去 4 年财务趋势")
    col1, col2 = st.columns([3, 1])
    with col1:
        search_input = st.text_input("股票代码 (如 CBA, FMG)", value="", placeholder="输入代码...")
    with col2:
        st.write("") 
        st.write("") 
        run_btn = st.button("开始体检", type="primary")

    if run_btn and search_input:
        with st.spinner(f"正在深入分析 {search_input} ..."):
            overview, df_ann, df_qrt, full_symbol = get_single_stock_deep_dive(search_input)
            
            if overview:
                st.subheader(f"📊 {full_symbol} - {overview['行业']}")
                
                # 1. 顶部核心指标卡片
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("当前价格", f"${overview['当前价']}")
                m2.metric("ROE (净资产收益)", overview['ROE'])
                m3.metric("股息率 (Yield)", overview['股息率'])
                m4.metric("PE (市盈率)", overview['PE (TTM)'])
                
                st.divider()
                
                # 2. 报表分栏显示 (年报 vs 半年报)
                sub_t1, sub_t2 = st.tabs(["📅 年度报告 (Annual)", "⏱️ 半年/季度报告 (Interim)"])
                
                with sub_t1:
                    if df_ann is not None:
                        st.caption("反映公司长期盈利能力的稳定性")
                        # 绘制图表
                        st.bar_chart(df_ann.set_index("日期")[["_revenue_raw", "_income_raw"]])
                        # 显示表格 (去掉原始绘图数据列)
                        display_cols = ["日期", "营收 (M)", "净利 (M)", "净利率"]
                        st.table(df_ann[display_cols])
                    else:
                        st.warning("暂无年度数据")

                with sub_t2:
                    if df_qrt is not None:
                        st.caption("反映近期（最近4期）的业绩拐点与季节性变化")
                        st.bar_chart(df_qrt.set_index("日期")[["_revenue_raw", "_income_raw"]])
                        display_cols = ["日期", "营收 (M)", "净利 (M)", "净利率"]
                        st.table(df_qrt[display_cols])
                    else:
                        st.info("该股票未提供详细的季度/半年报数据 (Common for some ASX small caps).")
            else:
                st.error(f"无法获取数据: {full_symbol}。请检查代码拼写或网络。")

# --- TAB 2: 列表扫描 ---
with tab2:
    st.markdown(f"#### 正在监控 {len(st.session_state.fav_list)} 只核心资产")
    st.caption("评分标准 (满分4分)：ROE>15%, 现金流为正, 负债<80%, PE<25")
    
    if st.button("🔄 运行全量扫描"):
        if not st.session_state.fav_list:
            st.warning("列表为空，请先在左侧侧边栏添加股票。")
        else:
            with st.spinner("正在逐一分析基本面，请稍候..."):
                scan_df = get_batch_scan_snapshot(st.session_state.fav_list)
                
            if not scan_df.empty:
                # 按照评分和ROE排序
                scan_df = scan_df.sort_values(by=["_score_raw", "ROE"], ascending=[False, False])
                # 移除用于排序的辅助列
                display_df = scan_df.drop(columns=["_score_raw"])
                
                # 高亮显示评分 (使用 Pandas Styler)
                st.dataframe(
                    display_df.style.highlight_max(subset=["评分"], color='#d4edda', axis=0),
                    use_container_width=True,
                    height=500
                )
            else:
                st.error("扫描未返回结果，请检查网络连接。")
