import pandas as pd
import yfinance as yf

def load_symbols():
    df = pd.read_csv(
        "data/fno_symbols.csv",
        header=None,
        encoding="utf-8-sig"
    )
    symbols = (
        df.iloc[:,0]
        .astype(str)
        .str.strip()
        .dropna()
        .tolist()
    )
    return symbols

def build_history():
    symbols = load_symbols()
    print("Total symbols:", len(symbols))

    # Convert to Yahoo format
    tickers = [s + ".NS" for s in symbols]
    print("Downloading historical data in batch...")

    # We remove group_by="ticker" because modern yfinance handles stacking better without it
    data = yf.download(
        tickers,
        period="6mo",
        interval="1d",
        threads=True,
        progress=True
    )

    if data.empty:
        print("No data fetched. Check your internet or symbol list.")
        return

    print("Flattening data into a clean table...")
    
    # ---------------------------------------------------------
    # THE FIX: Use pandas .stack() to perfectly format the data
    # ---------------------------------------------------------
    # yf.download returns columns as a MultiIndex (Price, Ticker)
    # stack() drops the Tickers down into the rows instantly.
    
    try:
        # Modern pandas stacking
        flat_df = data.stack(level="Ticker", future_stack=True).reset_index()
    except Exception:
        # Fallback for older versions of pandas/yfinance
        flat_df = data.stack(level=1).reset_index()

    # Rename the multi-index column name to "symbol"
    # It might be named "Ticker" or "level_1" depending on your pandas version
    flat_df = flat_df.rename(columns={"Ticker": "symbol", "level_1": "symbol"})
    
    # Remove the '.NS' suffix so it matches your screener's symbol format
    flat_df["symbol"] = flat_df["symbol"].str.replace(".NS", "", regex=False)
    
    # Clean up column headers (removes any weird spaces)
    flat_df.columns = [str(c).strip() for c in flat_df.columns]
    
    # Sort chronologically by stock so it looks clean
    if "Date" in flat_df.columns:
        flat_df = flat_df.sort_values(by=["symbol", "Date"]).reset_index(drop=True)

    # Save cleanly, overwriting the corrupted file
    flat_df.to_csv("data/price_history.csv", index=False)

    print("\nHistory database built cleanly!")
    print("Rows:", len(flat_df))
    print("Symbols:", flat_df["symbol"].nunique())

if __name__ == "__main__":
    build_history()