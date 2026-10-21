"""One-shot MBOS end-of-day update and report generator.

Run from Windows Task Scheduler at approximately 4:15 PM IST.
This script deliberately does not start the 20-second live loop.
"""
from __future__ import annotations

import logging
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

import pandas as pd

from data_fetch.fno_loader import get_fno_symbols
from data_fetch.history_updater import update_history
from analytics.data_cache import load_history, get_price_history
from analytics.screener_engine import build_screener_row
from analytics.rank_tracker import update_volume_ranks
from display_engine.excel_writer import write_excel

IST = ZoneInfo("Asia/Kolkata")
MIN_COVERAGE = 0.90
MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 60
REPORT_DIR = PROJECT_ROOT / "reports"
LOG_DIR = PROJECT_ROOT / "logs"
LIVE_WORKBOOK = PROJECT_ROOT / "screener.xlsx"


def configure_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "eod_update.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def _load_sector_map():
    path = PROJECT_ROOT / "data" / "fno_symbols.csv"
    sector_df = pd.read_csv(path, encoding="utf-8-sig")
    sector_df.columns = [str(c).strip() for c in sector_df.columns]
    if "SYMBOL" not in sector_df.columns:
        raise ValueError("data/fno_symbols.csv must contain a SYMBOL column")
    sector_df["SYMBOL"] = sector_df["SYMBOL"].astype(str).str.strip().str.upper()
    sector_cols = [
        c for c in ["INDEX_NAME", "SIMPLE_INDUSTRY", "BASIC_INDUSTRY", "CONCISE_DEFINITION"]
        if c in sector_df.columns
    ]
    return sector_df[["SYMBOL"] + sector_cols].drop_duplicates("SYMBOL").set_index("SYMBOL"), sector_cols


def _read_history():
    path = PROJECT_ROOT / "data" / "price_history.csv"
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    rename = {}
    for col in df.columns:
        if col.lower() == "date":
            rename[col] = "Date"
        elif col.lower() == "symbol":
            rename[col] = "symbol"
    df = df.rename(columns=rename)
    required = {"Date", "symbol", "Open", "Close", "Volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Historical database missing columns: {sorted(missing)}")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()
    for col in ["Open", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Date", "symbol", "Open", "Close", "Volume"])
    return df.sort_values(["symbol", "Date"]).reset_index(drop=True)


def _build_eod_dataframe(history, symbols):
    today = datetime.now(IST).date()
    history_dates = history["Date"].dt.date
    today_data = history[history_dates == today].copy()
    today_symbols = set(today_data["symbol"].unique())
    coverage = len(today_symbols) / max(1, len(symbols))
    logging.info(
        "Current-session historical coverage: %s/%s symbols (%.1f%%)",
        len(today_symbols), len(symbols), coverage * 100,
    )
    if coverage < MIN_COVERAGE:
        raise RuntimeError(
            f"Current-session data coverage {coverage:.1%} is below the "
            f"{MIN_COVERAGE:.0%} threshold. No EOD report will be published."
        )

    rows = []
    for symbol in symbols:
        symbol_df = history[history["symbol"] == symbol].sort_values("Date")
        current = symbol_df[symbol_df["Date"].dt.date == today]
        if current.empty:
            continue
        current_row = current.iloc[-1]
        previous = symbol_df[symbol_df["Date"].dt.date < today]
        if previous.empty:
            logging.warning("Skipping %s: no previous-session record.", symbol)
            continue
        previous_row = previous.iloc[-1]
        try:
            row = build_screener_row(
                symbol,
                float(current_row["Close"]),
                float(current_row["Volume"]),
                float(previous_row["Volume"]),
                float(current_row["Open"]),
                float(previous_row["Close"]),
            )
            if row:
                rows.append(row)
        except Exception:
            logging.exception("Failed building EOD row for %s", symbol)

    result = pd.DataFrame(rows)
    if result.empty:
        raise RuntimeError("No EOD screener rows were built.")

    if "Symbol" not in result.columns:
        raise RuntimeError("Screener output does not contain the expected Symbol column.")

    sector_map, sector_cols = _load_sector_map()
    result["Symbol"] = result["Symbol"].astype(str).str.strip().str.upper()
    result = result.merge(sector_map, how="left", left_on="Symbol", right_index=True)

    if "Vol Change %" in result.columns:
        result = result.sort_values("Vol Change %", ascending=False)
    result = result.reset_index(drop=True)

    # Preserve existing rank-tracking behavior where available.
    try:
        result = update_volume_ranks(result)
    except Exception:
        logging.exception("Rank tracking failed; continuing with current-session ranking.")

    existing_sector_cols = [c for c in sector_cols if c in result.columns]
    other_cols = [c for c in result.columns if c not in existing_sector_cols]
    result = result[other_cols + existing_sector_cols]
    logging.info("Built EOD report with %s rows.", len(result))
    return result


def _save_reports(screener_df):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(IST).strftime("%Y-%m-%d_%H%M%S")
    csv_path = REPORT_DIR / f"eod_screener_{timestamp}.csv"
    xlsx_snapshot = REPORT_DIR / f"eod_screener_{timestamp}.xlsx"

    # Save an unformatted numeric CSV for research/reproducibility.
    screener_df.to_csv(csv_path, index=False)

    if not write_excel(screener_df.copy()):
        raise RuntimeError("Excel writer reported failure; no dated XLSX snapshot created.")
    if not LIVE_WORKBOOK.exists() or LIVE_WORKBOOK.stat().st_size == 0:
        raise RuntimeError("screener.xlsx was not created or is empty.")

    shutil.copy2(LIVE_WORKBOOK, xlsx_snapshot)
    if xlsx_snapshot.stat().st_size == 0:
        raise RuntimeError("Dated Excel snapshot is empty.")

    logging.info("Saved numeric CSV: %s", csv_path)
    logging.info("Saved Excel snapshot: %s", xlsx_snapshot)


def main():
    configure_logging()
    logging.info("========== MBOS EOD RUN STARTED ==========")
    now = datetime.now(IST)
    if now.weekday() >= 5:
        logging.info("Weekend detected; no NSE EOD run required.")
        return 0

    symbols = get_fno_symbols()
    if not symbols:
        logging.error("No F&O symbols found.")
        return 2

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        logging.info("History update attempt %s/%s", attempt, MAX_ATTEMPTS)
        try:
            update_history()  # Force a refresh even if the morning run already updated.
            load_history()
            history = _read_history()
            screener_df = _build_eod_dataframe(history, symbols)
            _save_reports(screener_df)
            logging.info("========== MBOS EOD RUN SUCCESS ==========")
            return 0
        except Exception as exc:
            last_error = exc
            logging.exception("EOD attempt %s failed.", attempt)
            if attempt < MAX_ATTEMPTS:
                logging.info("Waiting %s seconds before retry.", RETRY_DELAY_SECONDS)
                time.sleep(RETRY_DELAY_SECONDS)

    logging.error("EOD run failed after retries: %s", last_error)
    logging.error("Existing screener.xlsx and prior dated snapshots were not intentionally deleted.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
