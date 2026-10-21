import pandas as pd
from analytics.data_cache import get_price_history


def calculate_performance(symbol):

    # ------------------------------------------------------------
    # Get historical price data from cache
    # ------------------------------------------------------------

    history = get_price_history()

    if history is None or history.empty:
        return {
            "perf_1w": None,
            "perf_1m": None,
            "perf_3m": None,
            "perf_6m": None,
            "perf_1y": None
        }

    # ------------------------------------------------------------
    # Handle symbol column safely
    # ------------------------------------------------------------

    if "symbol" in history.columns:
        df = history[history["symbol"] == symbol]
    else:
        df = history[history["Symbol"] == symbol]

    if df.empty:
        return {
            "perf_1w": None,
            "perf_1m": None,
            "perf_3m": None,
            "perf_6m": None,
            "perf_1y": None
        }

    # ------------------------------------------------------------
    # Ensure chronological order
    # ------------------------------------------------------------

    df = df.sort_values("Date")

    if len(df) < 2:
        return {
            "perf_1w": None,
            "perf_1m": None,
            "perf_3m": None,
            "perf_6m": None,
            "perf_1y": None
        }

    # ------------------------------------------------------------
    # Current price
    # ------------------------------------------------------------

    current_price = df["Close"].iloc[-1]

    if pd.isna(current_price) or current_price == 0:
        return {
            "perf_1w": None,
            "perf_1m": None,
            "perf_3m": None,
            "perf_6m": None,
            "perf_1y": None
        }

    # ------------------------------------------------------------
    # Helper function
    # ------------------------------------------------------------

    def pct_change(days):

        # Need enough candles
        if len(df) <= days:
            return None

        past_price = df["Close"].iloc[-(days + 1)]

        if pd.isna(past_price) or past_price == 0:
            return None

        return ((current_price - past_price) / past_price) * 100

    # ------------------------------------------------------------
    # Return performance metrics
    # ------------------------------------------------------------

    return {
        "perf_1w": pct_change(5),
        "perf_1m": pct_change(21),
        "perf_3m": pct_change(63),
        "perf_6m": pct_change(126),
        "perf_1y": pct_change(252)
    }