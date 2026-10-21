import yfinance as yf
import pandas as pd
from config import FNO_STOCKS

def download_history():

    all_data = []

    for sym in FNO_STOCKS:

        ticker = sym + ".NS"

        print("Downloading:", ticker)

        df = yf.download(ticker, period="6mo", interval="1d")

        # convert index to column
        df.reset_index(inplace=True)

        # flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df["symbol"] = sym

        df = df[["Date", "Open", "High", "Low", "Close", "Volume", "symbol"]]

        all_data.append(df)

    final_df = pd.concat(all_data, ignore_index=True)

    final_df.to_csv("data/price_history.csv", index=False)

    print("Historical database created successfully")
    
if __name__ == "__main__": download_history()