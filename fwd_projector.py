
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# 🔧 Inject dark theme CSS
st.markdown(
    """
    <style>
    body {
        background-color: #111111;
        color: #f1f1f1;
    }
    .stApp {
        background-color: #111111;
    }
    .css-18e3th9, .css-1d391kg, .css-1dp5vir, .css-1v0mbdj, .st-bb, .st-bc {
        background-color: #1e1e1e;
        color: #f1f1f1;
    }
    .stButton > button {
        background-color: #333333;
        color: white;
        border-radius: 6px;
    }
    .stButton > button:hover {
        background-color: #444444;
    }
    .stDataFrame, .stTable {
        background-color: #1e1e1e;
        color: #f1f1f1;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.set_page_config(page_title="🔭 FWD Projector", layout="centered")
st.title("🔭 FWD Projector")
st.markdown("Analyze what happens after key price behaviors, based on historical data.")

# Select Ticker
ticker = st.selectbox("Select Ticker", ["SPY", "QQQ", "DIA"])

# Strategy Selection
strategy = st.radio("Select Condition Type", ["% Move in X Days", "Open Up / Close Down Reversal"])

# Inputs for Strategy 1
if strategy == "% Move in X Days":
    percent_move = st.number_input("Total % Move (positive or negative)", value=-6.0, step=0.5)
    days = st.number_input("Number of Days for Move", value=2, step=1)

# Inputs for Strategy 2
elif strategy == "Open Up / Close Down Reversal":
    open_up_pct = st.number_input("Open Up %", value=1.0, step=0.1)
    close_down_pct = st.number_input("Close Down %", value=1.0, step=0.1)

# Download data
@st.cache_data
def get_data(ticker):
    df = yf.download(ticker, start="2000-01-01", progress=False)
    df.dropna(inplace=True)
    return df

df = get_data(ticker)

def find_matches_move(df, percent_move, num_days):
    matches = []
    for i in range(len(df) - num_days - 252):
        window = df.iloc[i:i + num_days + 1]
        cumulative_return = float(window["Close"].iloc[-1]) / float(window["Close"].iloc[0]) - 1
        if percent_move < 0:
            if cumulative_return <= percent_move / 100:
                matches.append(df.index[i + num_days])
        else:
            if cumulative_return >= percent_move / 100:
                matches.append(df.index[i + num_days])
    return matches

def find_matches_reversal(df, open_up_pct, close_down_pct):
    matches = []
    for i in range(1, len(df)):
        prev_close = df['Close'].iloc[i - 1]
        open_price = df['Open'].iloc[i]
        close_price = df['Close'].iloc[i]

        open_change = ((open_price - prev_close) / prev_close) * 100
        close_change = ((close_price - open_price) / open_price) * 100

        if float(open_change) >= open_up_pct and float(close_change) <= -close_down_pct:
            matches.append(df.index[i])
    return matches

def calculate_forward_returns(df, match_dates, months_forward=[1, 3, 6, 12]):
    results = []
    prices = df["Close"]
    for match_date in match_dates:
        if match_date not in prices.index:
            continue
        row = {"Match Date": match_date.strftime('%Y-%m-%d')}
        idx_now = prices.index.get_loc(match_date)
        price_now = prices.iloc[idx_now]

        for m in months_forward:
            idx_future = idx_now + int(m * 21)  # approx 21 trading days per month
            if idx_future < len(prices):
                price_future = prices.iloc[idx_future]
                fwd_return = (price_future / price_now - 1) * 100
                row[f"{m}M Forward Return"] = f"{float(fwd_return):.2f}%"
            else:
                row[f"{m}M Forward Return"] = "N/A"

        results.append(row)
    return pd.DataFrame(results)

# Run Query
if st.button("Run FWD Projector"):
    if strategy == "% Move in X Days":
        matches = find_matches_move(df, percent_move, days)
    elif strategy == "Open Up / Close Down Reversal":
        matches = find_matches_reversal(df, open_up_pct, close_down_pct)
    else:
        matches = []

    if matches:
        result_df = calculate_forward_returns(df, matches)
        st.success(f"✅ Found {len(matches)} matches.")
        st.dataframe(result_df)

        # Summary Stats
        try:
            numeric_df = result_df.drop(columns=["Match Date"]).replace("N/A", np.nan)
            numeric_df = numeric_df.applymap(lambda x: float(str(x).replace('%', '')) if pd.notnull(x) else np.nan)
            summary = numeric_df.describe().loc[["mean", "std", "min", "max"]].T
            summary.columns = ["Mean %", "Std Dev", "Min %", "Max %"]
            st.subheader("📊 Summary Stats")
            st.dataframe(summary)
        except:
            st.warning("⚠️ Could not calculate summary stats due to formatting issue.")

        # CSV Download
        csv = result_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv, file_name="fwd_projector_results.csv", mime="text/csv")
    else:
        st.warning("No matching periods found.")

