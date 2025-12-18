import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os

st.set_page_config(page_title="ASX 长线投资体检", layout="wide")

# --- 1. 数据持久化 (存储你的长期关注列表) ---
CONFIG_FILE = "long_term_list.json"

def load_list():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return ["CBA", "BHP", "CSL", "MQG", "WES"] # 初始默认值

def save_list(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

if 'fav_list' not in st.session_state:
    st.session_state.fav_list = load_list()

# --- 2. 侧边栏：输入与管理 ---
st.sidebar.title("🔍 股票筛选池")

# 模式 A: 手动输入
st.sidebar.subheader("1. 临时手动输入")
manual_input = st.sidebar.text_input("输入代码 (逗号分隔, 如: AAPL, RIO)", "")

# 模式 B: 长期关注列表管理
st.sidebar.subheader("2. 长期关注列表")
new_favs = st.sidebar.data_editor(
    pd.DataFrame({"代码": st.session_state.fav_list}), 
    num_rows="dynamic"
)

if st.sidebar.button("保存长期列表"):
    updated_list = new_favs["代码"].dropna().str.upper().str.strip().tolist()
    st.session_state.fav_list = updated_list
    save_list(updated_list)
    st.sidebar.success("列表已同步至云端")

# --- 3. 核心分析引擎 (基本面体检) ---
def analyze_fundamental(ticker):
    try:
        # 补全 ASX 后缀逻辑
        symbol = ticker.strip().upper()
        if not (symbol.endswith(".AX") or "." in symbol):
            symbol += ".AX"
            
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # 提取你要求的指标
        # 1. 获利能力
        roe = info.get('returnOnEquity', 0) or 0
        op_margin = info.get('operatingMargins', 0) or 0
        
        # 2. 财务健康
        fcf = info.get('freeCashflow', 0) or 0
        debt_to_equity = info.get('debtToEquity', 0) or 0 # 通常为百分比 100 = 100%
        
        # 3. 估值与成长
        pe = info.get('trailingPE', None)
        div_yield = info.get('dividendYield', 0) or 0
        rev_growth = info.get('revenueGrowth', 0) or 0

        # 打分逻辑 (4分制)
        score = 0
        if roe > 0.15: score += 1
        if op_margin > 0.10: score += 1
        if fcf > 0: score += 1
        if 0 < debt_to_equity < 100: score += 1

        return {
            "代码": symbol,
            "综合评分": score,
            "ROE": f"{roe*100:.1f}%",
            "营业利润率": f"{op_margin*100:.1f}%",
            "负债权益比": f"{debt_to_equity:.1f}%",
            "自由现金流": f"${fcf/1e6:.1f}M" if fcf != 0 else "N/A",
            "本益比(PE)": round(pe, 1) if pe else "N/A",
            "股息率": f"{div_yield*100:.1f}%",
            "营收增长": f"{rev_growth*100:.1f}%"
        }
    except:
        return None

# --- 4. 主界面运行 ---
st.title("🏆 ASX 价值投资长期体检表")
st.write("根据 ROE、现金流、负债比等核心维度自动评分")

# 合并待扫描池
final_pool = []
if manual_input:
    final_pool.extend([x.strip() for x in manual_input.split(",")])
final_pool.extend(st.session_state.fav_list)
final_pool = list(set(final_pool)) # 去重

if st.button(f"对 {len(final_pool)} 只股票进行深度体检"):
    if not final_pool:
        st.error("请输入代码或完善长期列表")
    else:
        results = []
        progress = st.progress(0)
        for i, t in enumerate(final_pool):
            with st.spinner(f"正在抓取 {t} 财报数据..."):
                res = analyze_fundamental(t)
                if res: results.append(res)
            progress.progress((i + 1) / len(final_pool))
        
        if results:
            df_final = pd.DataFrame(results)
            # 排序：评分最高且ROE最高
            df_final = df_final.sort_values(by=["综合评分", "ROE"], ascending=False)
            
            st.subheader("📋 体检报告单")
            st.dataframe(df_final, use_container_width=True)
            
            # 关键提醒
            st.markdown("""
            ---
            **体检标准说明：**
            * **综合评分**：最高4分。满分代表公司同时满足：ROE > 15%, 利润率 > 10%, 现金流为正, 负债比 < 100%。
            * **数据来源**：雅虎财经实时财务摘要。
            """)
        else:
            st.warning("未能获取有效数据，请检查代码输入是否正确。")
