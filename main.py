print("MAIN SCRIPT STARTED")

import time
import pandas as pd

# ==========================================
# LOAD SECTOR CLASSIFICATION
# ==========================================

sector_file = "data/fno_symbols.csv"
sector_df = pd.read_csv(sector_file)

# clean symbols once at startup

sector_df["SYMBOL"] = sector_df["SYMBOL"].astype(str).str.strip()

sector_map = (

    sector_df[

        ["SYMBOL","INDEX_NAME","SIMPLE_INDUSTRY","BASIC_INDUSTRY","CONCISE_DEFINITION"]

    ]

    .drop_duplicates("SYMBOL")

    .set_index("SYMBOL")

)

pd.set_option("display.width", None)

from utils.market_hours import is_market_open, wait_until_market_opens

from data_fetch.fno_loader import get_fno_symbols

from display_engine.excel_writer import write_excel

from nse_fetch import fetch_stock_data

from analytics.screener_engine import build_screener_row

from analytics.rank_tracker import update_volume_ranks

from analytics.data_cache import load_history

from data_fetch.history_updater import update_if_required

from utils.logger import log_info, log_error




# =====================================
# CONFIG
# =====================================

REFRESH_INTERVAL = 20

# =====================================
# LOAD F&O UNIVERSE
# =====================================

FNO_STOCKS = get_fno_symbols()

# =====================================
# MAIN SCREENER
# =====================================

def run_screener():

    log_info("Screener started")

    print("Checking historical database...")

    update_if_required()

    print("Loading historical database...")

    load_history()

    print("History loaded")

    while True:

        # ---------------------------------
        # Market hours check
        # ---------------------------------

        try:

            if not is_market_open():

                print("Market closed.")

                wait_until_market_opens()

                continue

        except Exception as e:

            log_error(f"Market hour check failed: {e}")

            time.sleep(REFRESH_INTERVAL)

            continue

        print("\nFetching live market data...\n")

        # ---------------------------------
        # Fetch live NSE data
        # ---------------------------------

        try:

            live_df = fetch_stock_data(FNO_STOCKS)

        except Exception as e:

            log_error(f"Live fetch failed: {e}")

            print("Live fetch failed. Retrying...")

            time.sleep(REFRESH_INTERVAL)

            continue

        # ---------------------------------
        # Validate live data
        # ---------------------------------

        if live_df is None or live_df.empty:

            print("No live data received. Retrying...")

            log_error("Live data fetch returned empty")

            time.sleep(REFRESH_INTERVAL)

            continue

        rows = []

        # ---------------------------------
        # Build screener rows
        # ---------------------------------

        for r in live_df.itertuples():

            symbol = r.symbol

            price = r.price

            volume = r.volume

            prev_volume = r.prev_volume

            open_price = r.open

            prev_close = r.prev_close

            try:

                row = build_screener_row(

                    symbol,

                    price,

                    volume,

                    prev_volume,

                    open_price,

                    prev_close

                )

                if row:

                    rows.append(row)


            except Exception as e:

                print(f"Error processing {symbol}: {e}")

                log_error(f"{symbol} processing failed: {e}")

                continue

        # ---------------------------------
        # Build DataFrame
        # ---------------------------------

        screener_df = pd.DataFrame(rows)
        
        # ==========================================
        # CLEAN SYMBOLS
        # ==========================================

        screener_df["Symbol"] = screener_df["Symbol"].astype(str).str.strip()

        # ==========================================
        # MERGE SECTOR DATA
        # ==========================================

        try:

            screener_df = screener_df.merge(

                sector_map,

                how="left",

                left_on="Symbol",

                right_index=True

            )

        except Exception as e:

            log_error(f"Sector merge failed: {e}")

        # ==========================================
        # MOVE SECTOR COLUMNS TO END
        # ==========================================

        sector_cols = [

            "INDEX_NAME",

            "SIMPLE_INDUSTRY",

            "BASIC_INDUSTRY",

            "CONCISE_DEFINITION"

        ]

        existing_sector_cols = [c for c in sector_cols if c in screener_df.columns]

        other_cols = [c for c in screener_df.columns if c not in existing_sector_cols]

        screener_df = screener_df[other_cols + existing_sector_cols]

        print("Screener columns:", screener_df.columns)

        if screener_df.empty:

            print("No screener data available.")

            time.sleep(REFRESH_INTERVAL)

            continue

        # ==========================================
        # Ensure sector columns appear at the end
        # ==========================================

        sector_cols = [

            "INDEX_NAME",

            "SIMPLE_INDUSTRY",

            "BASIC_INDUSTRY",

            "CONCISE_DEFINITION"

        ]

        existing_sector_cols = [c for c in sector_cols if c in screener_df.columns]

        other_cols = [c for c in screener_df.columns if c not in existing_sector_cols]

        screener_df = screener_df[other_cols + existing_sector_cols]

        # ---------------------------------
        # Sort by Volume Change %
        # ---------------------------------

        if "Vol Change %" in screener_df.columns:

            screener_df = screener_df.sort_values(

                "Vol Change %",

                ascending=False

            )

        # ---------------------------------
        # UPDATE VOLUME RANKS
        # ---------------------------------

        try:

            screener_df = update_volume_ranks(
                screener_df
            )

        except Exception as e:

            print(f"Rank tracking failed: {e}")

        # ---------------------------------
        # Terminal preview
        # ---------------------------------

        print("\n===== NSE F&O LIVE SCREENER =====\n")

        try:

            print(screener_df.round(2).to_string(index=False))

        except Exception as e:

            print("Unable to display screener preview")

            log_error(f"Terminal preview error: {e}")

        # ---------------------------------
        # Write Excel dashboard
        # ---------------------------------

        try:

            write_excel(screener_df)

        except Exception as e:

            log_error(f"Excel write failed: {e}")

            print("Excel update failed")

        # ---------------------------------
        # Refresh delay
        # ---------------------------------

        time.sleep(REFRESH_INTERVAL)

# =====================================
# SCRIPT ENTRY
# =====================================

if __name__ == "__main__":

    run_screener()