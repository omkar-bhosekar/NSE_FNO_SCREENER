"""Historical database loader and per-symbol cache."""
from pathlib import Path
import pandas as pd

price_history_cache = None
volume_history_cache = {}


def load_history():
    global price_history_cache, volume_history_cache

    path = Path("data/price_history.csv")
    if not path.exists() or path.stat().st_size == 0:
        raise FileNotFoundError(f"Historical database not found or empty: {path}")

    print("Loading historical database into memory...")
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    rename = {}
    for col in df.columns:
        if col.lower() == "date":
            rename[col] = "Date"
        elif col.lower() == "symbol":
            rename[col] = "symbol"
    df = df.rename(columns=rename)

    required = {"Date", "symbol", "Volume", "Close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Historical database missing required columns: {sorted(missing)}")

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
    df = df.dropna(subset=["Date", "symbol"])
    df = df[df["symbol"].ne("")].sort_values(["symbol", "Date"]).reset_index(drop=True)

    if df.empty:
        raise ValueError("Historical database has no usable rows.")

    price_history_cache = df
    volume_history_cache = {}
    for symbol, symbol_df in df.groupby("symbol", sort=False):
        volume_history_cache[symbol] = symbol_df[["Date", "Volume"]].copy().sort_values("Date")

    print(f"Historical data loaded: {len(df):,} rows")
    print(f"Price cache symbols: {df['symbol'].nunique()}")
    print(f"Volume cache symbols: {len(volume_history_cache)}")


def get_price_history():
    return price_history_cache


def get_symbol_volume_history(symbol):
    return volume_history_cache.get(str(symbol).strip().upper())
