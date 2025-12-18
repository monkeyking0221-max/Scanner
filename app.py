import streamlit as st
import yfinance as yf
import pandas as pd

# 设置网页标题
st.set_page_config(page_title="ASX 每日精选筛选器", layout="wide")
st.title("🇦🇺 ASX 澳洲股市每日精选筛选器")
st.write("基于 均线多头排列 + 异动量比 + 涨幅过滤 逻辑")

# 1. 定义 ASX 关注池 (你可以根据需要添加更多代码)
DEFAULT_TICKERS = [
    "CBA.AX", "BHP.AX", "CSL.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "FMG.AX", 
    "TLS.AX", "WOW.AX", "WES.AX", "MQG.AX", "RIO.AX", "GMG.AX", "WDS.AX"
]

# 侧边栏配置
st.sidebar.header("参数设置")
input_tickers = st.sidebar.text_area("输入 ASX 代码 (逗号分隔)", ",".join(DEFAULT_TICKERS))
vol_threshold = st.sidebar.slider("成交量比率阈值 (倍数)", 1.0, 5.0, 1.5)

def screen_asx(ticker_list):
    results = []
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(ticker_list):
        try:
            stock = yf.Ticker(ticker.strip())
            df = stock.history(period="30d")
            
            if len(df) < 20: continue

            # 核心数据
            curr_close = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            curr_vol = df['Volume'].iloc[-1]
            avg_vol = df['Volume'].mean()
            
            # 技术指标计算
            ma5 = df['Close'].rolling(5).mean().iloc[-1]
            ma10 = df['Close'].rolling(10).mean().iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            
            # 筛选逻辑
            is_bullish = ma5 > ma10 > ma20  # 均线多头
            vol_ratio = curr_vol / avg_vol  # 量比
            daily_change = (curr_close - prev_close) / prev_close
            
            # 过滤条件: 均线向上 + 量比达标 + 涨幅在 1% 到 8% 之间
            if is_bullish and vol_ratio >= vol_threshold and 0.01 < daily_change < 0.08:
                results.append({
                    "代码": ticker,
                    "当前价": f"${curr_close:.2f}",
                    "今日涨幅": f"{daily_change*100:.2f}%",
                    "量比": round(vol_ratio, 2),
                    "状态": "📈 趋势走强"
                })
        except:
            pass
        progress_bar.progress((i + 1) / len(ticker_list))
    
    return pd.DataFrame(results)

if st.button("开始扫描今日精选"):
    list_to_scan = input_tickers.split(",")
    with st.spinner('正在分析 ASX 数据...'):
        final_df = screen_asx(list_to_scan)
        
    if not final_df.empty:
        st.success(f"扫描完成！找到 {len(final_df)} 只符合条件的股票：")
        st.table(final_df.sort_values(by="量比", ascending=False))
    else:
        st.warning("今日暂无符合条件的筛选结果，建议扩大关注池或降低量比阈值。")

st.info("注：数据来源 Yahoo Finance，ASX 数据通常有 20 分钟延迟。")