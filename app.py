import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="ASX 全量扫描器", layout="wide")
st.title("🇦🇺 ASX 股票自定义扫描系统")

# --- 修改后的列表获取逻辑 ---
st.sidebar.header("1. 上传股票池")
uploaded_file = st.sidebar.file_uploader("上传 CSV 文件 (第一列为代码)", type="csv")

if uploaded_file:
    # 读取上传的文件
    df_input = pd.read_csv(uploaded_file)
    # 假设第一列是代码，并自动加上 .AX
    raw_tickers = df_input.iloc[:, 0].tolist()
    asx_pool = [str(t).strip().split('.')[0] + ".AX" for t in raw_tickers]
    st.sidebar.success(f"成功加载 {len(asx_pool)} 只股票")
else:
    # 默认显示的备用小池子
    asx_pool = ["CBA.AX", "BHP.AX", "CSL.AX", "TLS.AX"]
    st.sidebar.warning("等待上传 CSV，当前使用默认演示列表")


# --- 第二步：扫描参数设置 ---
st.sidebar.header("过滤参数")
vol_threshold = st.sidebar.slider("量比阈值 (今日成交量/平均)", 1.0, 3.0, 1.5)
min_change = st.sidebar.slider("最小涨幅 (%)", 0.0, 5.0, 1.0) / 100

def run_scanner(ticker_list):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(ticker_list):
        try:
            status_text.text(f"正在分析: {ticker}")
            stock = yf.Ticker(ticker)
            # 获取最近30天数据
            df = stock.history(period="30d")
            
            if len(df) < 20: continue

            # 数据计算
            curr_price = df['Close'].iloc[-1]
            last_price = df['Close'].iloc[-2]
            curr_vol = df['Volume'].iloc[-1]
            avg_vol = df['Volume'].mean()
            daily_change = (curr_price - last_price) / last_price
            
            # 均线
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            ma50 = df['Close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else ma20

            # 筛选条件：1.涨幅达标 2.量比达标 3.收盘价在20日线之上（趋势向上）
            if daily_change >= min_change and (curr_vol / avg_vol) >= vol_threshold and curr_price > ma20:
                results.append({
                    "代码": ticker,
                    "价格": f"${curr_price:.2f}",
                    "涨幅": f"{daily_change*100:.2f}%",
                    "量比": round(curr_vol/avg_vol, 2),
                    "20日均线": f"${ma20:.2f}"
                })
        except:
            continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    status_text.text("分析完成！")
    return pd.DataFrame(results)

# --- 第三步：运行界面 ---
if st.button(f"点此开始全量扫描 {len(asx_pool)} 只股票"):
    with st.spinner('扫描中，大约需要 1-2 分钟...'):
        final_results = run_scanner(asx_pool)
        
    if not final_results.empty:
        st.write(f"### 🎯 今日精选结果 ({len(final_results)} 只)")
        st.dataframe(final_results.sort_values(by="量比", ascending=False), use_container_width=True)
    else:
        st.warning("目前没有股票完全符合设定条件。")
