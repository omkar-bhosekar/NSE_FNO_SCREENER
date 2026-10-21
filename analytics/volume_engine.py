"""Volume analytics using only completed prior sessions for baseline averages."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from analytics.data_cache import get_symbol_volume_history

IST = ZoneInfo("Asia/Kolkata")


def calculate_volume_metrics(symbol, current_volume, prev_volume):
    df = get_symbol_volume_history(symbol)
    empty = {
        "avg10": 0, "avg30": 0, "avg60": 0, "avg90": 0,
        "vol_change": 0, "vol_change_pct": 0,
        "vol_vs_avg10": 0, "vol_vs_avg30": 0,
        "vol_vs_avg60": 0, "vol_vs_avg90": 0,
    }
    if df is None or df.empty:
        return empty.copy()

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")
    df = df.dropna(subset=["Date", "Volume"]).sort_values("Date")
    df = df[df["Volume"] > 0]

    # If today's EOD bar is already in history, exclude it from the baseline.
    today = datetime.now(IST).date()
    df = df[df["Date"].dt.date != today]
    volumes = df["Volume"]

    def average(n):
        if volumes.empty:
            return 0.0
        value = volumes.tail(n).mean()
        return 0.0 if pd.isna(value) else float(value)

    avg10, avg30, avg60, avg90 = average(10), average(30), average(60), average(90)
    current_volume = float(current_volume or 0)
    prev_volume = float(prev_volume or 0)
    vol_change = current_volume - prev_volume
    vol_change_pct = (vol_change / prev_volume * 100) if prev_volume else 0.0

    return {
        "avg10": avg10, "avg30": avg30, "avg60": avg60, "avg90": avg90,
        "vol_change": vol_change, "vol_change_pct": vol_change_pct,
        "vol_vs_avg10": ((current_volume - avg10) / avg10 * 100) if avg10 else 0.0,
        "vol_vs_avg30": ((current_volume - avg30) / avg30 * 100) if avg30 else 0.0,
        "vol_vs_avg60": ((current_volume - avg60) / avg60 * 100) if avg60 else 0.0,
        "vol_vs_avg90": ((current_volume - avg90) / avg90 * 100) if avg90 else 0.0,
    }
