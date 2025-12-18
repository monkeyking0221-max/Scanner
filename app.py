import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os

st.set_page_config(page_title="ASX 多列表扫描器", layout="wide")

# --- 1. 数据持久化处理 ---
CONFIG_FILE = "my_lists.json"

def load_lists():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        # 初始默认数据
        return {
            "我的关注": ["CBA", "BHP", "CSL"],
            "矿业板块": ["RIO", "FMG", "WDS"],
            "科技板块": ["XRO", "WTC", "CPU"]
        }

def save_lists(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

# 初始化 session_state 存储列表
if 'all_lists' not in st.session_state:
    st.session_state.all_lists = load_lists()

# --- 2. 侧边栏：管理模式 ---
st.sidebar.title("⚙️ 列表管理")
manage_mode = st.sidebar.checkbox("开启编辑模式")

if manage_mode:
    st.subheader("📝 编辑/增减你的股票清单")
    
    # 将字典转换为 DataFrame 方便编辑
    # 格式：列表名称 | 股票代码 (逗号分隔)
    list_data = [{"列表名称": k, "代码内容": ", ".join(v)} for k, v in st.session_state.all_lists.items()]
    df_editor = pd.DataFrame(list_data)
    
    # 使用交互式表格编辑器
    edited_df = st.data_editor(df_editor, num_rows="dynamic", use_container_width=True)
    
    if st.button("保存修改"):
        # 将编辑后的表格转回字典
        new_lists = {}
        for _, row in edited_df.iterrows():
            if pd.notna(row['列表名称']):
                # 清理代码：去空格、转大写
                codes = [c.strip().upper() for c in str(row['代码内容']).split(",") if c.strip()]
                new_lists[row['列表名称']] = codes
        
        st.session_state.all_lists = new_lists
        save_lists(new_lists)
        st.success("配置已保存！")
        st.rerun()

st.divider()

# --- 3. 主界面：选择与扫描 ---
st.title("🇦🇺 ASX 选股扫描器")

col1, col2 = st.columns([1, 2])

with col1:
    selected_list_name = st.selectbox("选择要扫描的列表", list(st.session_state.all_lists.keys()))
    current_codes = st.session_state.all_lists[selected_list_name]
    st.info(f"当前选中: {len(current_codes)} 只股票")

with col2:
    vol_ratio = st.slider("量比阈值", 1.0, 3.0, 1.5)
    min_change = st.slider("最小涨幅 (%)", 0.0, 5.0, 1.0) / 100

# 补全 .AX 后缀
final_tickers = [c if c.endswith(".AX") else c + ".AX" for c in current_codes]

# --- 4. 扫描函数 ---
def run_scan(tickers):
    results = []
    prog = st.progress(0)
    for i, t in enumerate(tickers):
        try:
            stock = yf.Ticker(t)
            df = stock.history(period="30d")
            if len(df) < 20: continue
            
            c_p = df['Close'].iloc[-1]
            l_p = df['Close'].iloc[-2]
            ratio = df['Volume'].iloc[-1] / df['Volume'].mean()
            change = (c_p - l_p) / l_p
            
            if change >= min_change and ratio >= vol_ratio:
                results.append({"代码": t, "价格": f"${c_p:.2f}", "涨幅": f"{change*100:.2f}%", "量比": round(ratio, 2)})
        except: continue
        prog.progress((i+1)/len(tickers))
    return pd.DataFrame(results)

if st.button(f"开始扫描 {selected_list_name}"):
    if not final_tickers:
        st.error("列表为空，请先在编辑模式添加股票。")
    else:
        res = run_scan(final_tickers)
        if not res.empty:
            st.dataframe(res.sort_values("量比", ascending=False), use_container_width=True)
        else:
            st.warning("无符合条件的结果。")
