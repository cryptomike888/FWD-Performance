
import yfinance as yf
import pandas as pd
from datetime import datetime

# === STEP 1: Download SPY Data ===
df = yf.download("SPY", start="2000-01-01", auto_adjust=True)
print("✅ Download complete.")
print(df.head())
print(f"Data shape: {df.shape}\n")

# === STEP 2: Calculate daily percent change ===
df["pct"] = df["Close"].pct_change() * 100
df.dropna(inplace=True)

# === STEP 3: Define condition ===
pct_move = 2.0  # 2% move
num_days = 2    # for 2 days in a row
direction = "Down"  # use "Up" for up moves

condition_dates = []

for i in range(len(df) - num_days - 252):  # ensure 12M forward buffer
    window = df.iloc[i+1:i+1+num_days]
    if direction == "Down" and (window["pct"] <= -pct_move).all():
        condition_dates.append(df.index[i+num_days])
    elif direction == "Up" and (window["pct"] >= pct_move).all():
        condition_dates.append(df.index[i+num_days])

print(f"\n✅ Found {len(condition_dates)} matching condition dates.")

# === STEP 4: Calculate forward returns ===
if not condition_dates:
    print("⚠️ No historical matches found for that condition.")
else:
    returns = {"1M": [], "3M": [], "6M": [], "9M": [], "12M": []}
    for date in condition_dates:
        try:
            base = df.loc[date, "Close"]
            for m in [1, 3, 6, 9, 12]:
                future_date = date + pd.DateOffset(months=m)
                future_index = df.index[df.index.get_indexer([future_date], method='nearest')[0]]
                future_price = df.loc[future_index, "Close"]
                change = (future_price - base) / base * 100
                returns[f"{m}M"].append(change)
        except:
            continue

    result_df = pd.DataFrame({
        "Avg Return": {k: f"{pd.Series(v).mean():.2f}%" if v else "-" for k, v in returns.items()},
        "Count": {k: len(v) for k, v in returns.items()}
    })

    print("\n📊 Forward Return Results:")
    print(result_df)
