import pandas as pd

# ------------------------------------------
# Screener Settings
# ------------------------------------------

REFRESH_INTERVAL = 20

MIN_RVOL = 1.5

# ------------------------------------------
# Load F&O Stocks Automatically
# ------------------------------------------

df = pd.read_csv("data/fno_symbols.csv")

# Use first column
FNO_STOCKS = (
    df.iloc[:, 0]
    .dropna()
    .astype(str)
    .str.strip()
    .tolist()
)

print(f"Loaded {len(FNO_STOCKS)} F&O Stocks")