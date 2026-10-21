import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz


IST = pytz.timezone("Asia/Kolkata")


# --------------------------------------------------
# Process one symbol dataframe
# --------------------------------------------------

def _process_df(sym, df):

    if df is None or df.empty:
        return None

    df = df.dropna(how="all")

    if df.empty:
        return None

    # --------------------------------------
    # Safe timezone handling
    # --------------------------------------

    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    df = df.tz_convert(IST)

    today = datetime.now(IST).date()

    # --------------------------------------
    # Filter today's data only
    # --------------------------------------

    today_df = df[df.index.date == today]

    if today_df.empty:
        return None

    # --------------------------------------
    # Keep only NSE trading hours
    # --------------------------------------

    today_df = today_df.between_time("09:15", "15:30")

    if today_df.empty:
        return None

    close_series = today_df["Close"].ffill()
    open_series = today_df["Open"].ffill()

    volume_series = today_df["Volume"].fillna(0)

    # Remove incomplete last minute candle
    if len(volume_series) > 1:
        volume_series = volume_series.iloc[:-1]

    price = close_series.iloc[-1]
    open_price = open_series.iloc[0]
    volume = volume_series.sum()

    # --------------------------------------
    # Previous day volume
    # --------------------------------------

    prev_day_df = df[df.index.date < today]

    if prev_day_df.empty:
        prev_volume = 0
    else:

        prev_day = prev_day_df.index.date.max()

        prev_day_data = prev_day_df[prev_day_df.index.date == prev_day]

        prev_day_data = prev_day_data.between_time("09:15", "15:30")

        prev_volume = prev_day_data["Volume"].fillna(0).sum()

    # --------------------------------------
    # Previous day close
    # --------------------------------------

    prev_day_df = df[df.index.date < today]

    if prev_day_df.empty:
        prev_close = close_series.iloc[0]
    else:
        prev_close = prev_day_df["Close"].dropna().iloc[-1]

    return {
        "symbol": sym,
        "price": price,
        "volume": volume,
        "prev_volume": prev_volume,
        "open": open_price,
        "prev_close": prev_close
    }


# --------------------------------------------------
# Main fetch engine
# --------------------------------------------------

def fetch_stock_data(symbols):

    print("\nFetching live market data...")

    tickers = [s + ".NS" for s in symbols]

    try:

        data = yf.download(
            tickers,
            period="2d",
            interval="1m",
            progress=False,
            threads=True
        )

    except Exception as e:

        print("Yahoo batch fetch failed:", e)
        return pd.DataFrame()

    rows = []
    missing = []

    # --------------------------------------
    # Process batch result
    # --------------------------------------

    for sym in symbols:

        ticker = sym + ".NS"

        try:

            df = data.xs(ticker, axis=1, level=1)

            row = _process_df(sym, df)

            if row:
                rows.append(row)
            else:
                print("No usable data:", sym)
                missing.append(sym)

        except Exception as e:

            print("Batch fetch error:", sym, "|", e)
            missing.append(sym)

    # --------------------------------------
    # Retry missing symbols individually
    # --------------------------------------

    if missing:

        print("\nRetrying missing symbols:", len(missing))
        print("Missing symbols list:", missing)

        retry_rows = []

        for sym in missing:

            try:

                df = yf.download(
                    sym + ".NS",
                    period="2d",
                    interval="1m",
                    progress=False
                )

                row = _process_df(sym, df)

                if row:
                    retry_rows.append(row)
                else:
                    print("Retry returned empty:", sym)

            except Exception as e:

                print("Retry failed:", sym, "|", e)

        rows.extend(retry_rows)

    return pd.DataFrame(rows)