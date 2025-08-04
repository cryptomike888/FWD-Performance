

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# --- Page layout ---
st.set_page_config(page_title="Lookahead Engine", layout="centered")
st.title("🔭 Lookahead Engine")
st.markdown("Analyze what typically happens *after* a move like -6% in 2 days for SPY, QQQ, or DIA.")

# --- Inputs ---
ticker = st.selectbox("Select Ticker", ["SPY", "QQQ", "DIA"])
percent_move = st.number_input("Total % Move (positive or negative)", value=-6.0, step=0.5)
days = st.number_input("Number of Days for Move", value=2, step=1)

# --- Download data ---
@st.cache_data
def get_data(ticker):
    df = yf.download(ticker, start="2000-01-01", progress=False)
    df["Return"] = df["Close"].pct_change()
    return df

df = get_data(ticker)

# --- Find matching periods ---
def find_matches(df, percent_move, period):
    matches = []
    for i in range(len(df) - period - 252):  # reserve 1 year for forward returns
        window = df.iloc[i : i + period + 1]
        if len(window) < period + 1:
            continue
        cumulative_return = float(window["Close"].iloc[-1].item()) / float(window["Close"].iloc[0].item()) - 1

        if percent_move < 0:
            if cumulative_return <= percent_move / 100:
                matches.append(df.index[i + period])
        else:
            if cumulative_return >= percent_move / 100:
                matches.append(df.index[i + period])
    return matches

# --- Calculate forward returns ---
def calculate_forward_returns(df, match_dates, months_forward=[1, 3, 6, 12]):
    results = []
    prices = df["Close"]
    all_dates = df.index

    for date in match_dates:
        row = {"Match Date": date.strftime('%Y-%m-%d')}
        idx_now = all_dates.searchsorted(date)

        if idx_now >= len(all_dates):
            continue

        try:
            price_now = float(prices.iloc[idx_now].item())
        except:
            continue

        valid_row = False

        for m in months_forward:
            future_date = date + pd.DateOffset(months=m)
            idx_future = all_dates.searchsorted(future_date)

            if idx_future >= len(all_dates):
                row[f"{m}M Forward Return"] = "N/A"
                continue

            try:
                price_future = float(prices.iloc[idx_future].item())
                fwd_return = (price_future / price_now - 1) * 100
                row[f"{m}M Forward Return"] = f"{fwd_return:.2f}%"
                valid_row = True
            except:
                row[f"{m}M Forward Return"] = "N/A"

        if valid_row:
            results.append(row)

    return pd.DataFrame(results)

# --- Run Lookahead ---
if st.button("Run Lookahead"):
    matches = find_matches(df, percent_move, days)
    if matches:
        result_df = calculate_forward_returns(df, matches)
        if result_df.empty:
            st.warning("❗ Matches were found, but no valid forward returns could be calculated.")
        else:
            st.success(f"✅ Found {len(result_df)} matching periods.")
            st.dataframe(result_df)

            # --- Summary Statistics ---
            st.subheader("📊 Summary Statistics")
            numeric_df = result_df.drop(columns=["Match Date"]).replace("N/A", np.nan)

            for col in numeric_df.columns:
                numeric_df[col] = numeric_df[col].str.replace('%', '').astype(float)

            summary_stats = pd.DataFrame({
                "Mean (%)": numeric_df.mean(),
                "Median (%)": numeric_df.median(),
                "Std Dev (%)": numeric_df.std()
            }).round(2)

            st.dataframe(summary_stats)

            # --- CSV Download ---
            csv_data = result_df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Results as CSV", csv_data, file_name="lookahead_results.csv", mime="text/csv")
    else:
        st.warning("⚠️ No matching periods found.")
