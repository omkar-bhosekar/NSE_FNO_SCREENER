"""
Safe daily historical-data updater for MBOS / NSE F&O Screener.

- Bootstraps 18 months for symbols not yet present.
- Downloads the most recent 10 calendar days for symbols already in history.
- Merges instead of replacing existing history.
- Deduplicates on (symbol, Date).
- Writes atomically and keeps a timestamped backup before replacing the CSV.
- Only marks the date as successfully updated when symbol-download coverage is >= 95%.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"
HISTORY_FILE = DATA_DIR / "price_history.csv"
META_FILE = DATA_DIR / "history_meta.json"
BACKUP_DIR = DATA_DIR / "backups"
IST = ZoneInfo("Asia/Kolkata")
REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume", "symbol"]
BOOTSTRAP_PERIOD = "18mo"
INCREMENTAL_PERIOD = "10d"
SUCCESS_COVERAGE = 0.95


def _now():
    return datetime.now(IST)


def _load_symbols():
    from data_fetch.fno_loader import get_fno_symbols

    symbols = [str(s).strip().upper() for s in get_fno_symbols() if str(s).strip()]
    # Stable order and no duplicate symbols.
    return list(dict.fromkeys(symbols))


def _normalise_columns(df: pd.DataFrame, symbol: str | None = None) -> pd.DataFrame:
    df = df.copy()

    if isinstance(df.columns, pd.MultiIndex):
        # yfinance may return (Price, Ticker) multi-level columns.
        df.columns = [str(col[0]) for col in df.columns]

    df.columns = [str(c).strip() for c in df.columns]

    rename = {}
    for col in df.columns:
        low = col.lower()
        if low in {"date", "datetime"}:
            rename[col] = "Date"
        elif low == "symbol":
            rename[col] = "symbol"
        elif low in {"open", "high", "low", "close", "volume"}:
            rename[col] = low.capitalize()
    df = df.rename(columns=rename)

    if "Date" not in df.columns and df.index.name and str(df.index.name).lower() in {"date", "datetime"}:
        df = df.reset_index()
        df.columns = [str(c[0] if isinstance(c, tuple) else c).strip() for c in df.columns]
        rename = {}
        for col in df.columns:
            low = col.lower()
            if low in {"date", "datetime"}:
                rename[col] = "Date"
            elif low in {"open", "high", "low", "close", "volume"}:
                rename[col] = low.capitalize()
        df = df.rename(columns=rename)

    if "symbol" not in df.columns and symbol:
        df["symbol"] = symbol

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"History data missing columns: {missing}")

    df = df[REQUIRED_COLUMNS].copy()
    # Daily Yahoo timestamps are date labels. Keep the exchange calendar date.
    parsed = pd.to_datetime(df["Date"], errors="coerce", utc=True)
    df["Date"] = parsed.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None).dt.normalize()
    df["symbol"] = df["symbol"].astype(str).str.strip().str.upper()

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Date", "Close", "Volume"])
    df = df[df["symbol"].ne("") & df["symbol"].ne("NAN")]
    return df


def _download_symbol(symbol: str, period: str) -> pd.DataFrame:
    ticker = f"{symbol}.NS"
    downloaded = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if downloaded is None or downloaded.empty:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    downloaded = downloaded.reset_index()
    if isinstance(downloaded.columns, pd.MultiIndex):
        downloaded.columns = [str(c[0]) for c in downloaded.columns]

    # Some yfinance versions name the index column Datetime.
    if "Date" not in downloaded.columns and "Datetime" in downloaded.columns:
        downloaded = downloaded.rename(columns={"Datetime": "Date"})
    downloaded["symbol"] = symbol
    return _normalise_columns(downloaded, symbol=symbol)


def _read_existing() -> pd.DataFrame:
    if not HISTORY_FILE.exists() or HISTORY_FILE.stat().st_size == 0:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    existing = pd.read_csv(HISTORY_FILE)
    existing.columns = [str(c).strip() for c in existing.columns]
    if "symbol" not in existing.columns and "Symbol" in existing.columns:
        existing = existing.rename(columns={"Symbol": "symbol"})
    if "Date" not in existing.columns and "date" in existing.columns:
        existing = existing.rename(columns={"date": "Date"})
    return _normalise_columns(existing)


def _write_json_atomic(path: Path, payload: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(temp, path)


def update_history() -> dict:
    """Download recent history, merge safely, and return a run summary."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    symbols = _load_symbols()
    if not symbols:
        raise RuntimeError("No F&O symbols loaded; refusing to update history.")

    existing = _read_existing()
    existing_symbols = set(existing["symbol"].unique()) if not existing.empty else set()
    print(f"Historical updater: {len(symbols)} symbols; existing rows: {len(existing):,}")

    downloaded_frames = []
    successful_symbols = []
    failed_symbols = []

    for idx, symbol in enumerate(symbols, start=1):
        period = INCREMENTAL_PERIOD if symbol in existing_symbols else BOOTSTRAP_PERIOD
        print(f"[{idx}/{len(symbols)}] {symbol} ({period})")
        try:
            fresh = _download_symbol(symbol, period)
            if fresh.empty:
                failed_symbols.append(symbol)
                print(f"  No usable rows returned for {symbol}")
                continue
            downloaded_frames.append(fresh)
            successful_symbols.append(symbol)
        except Exception as exc:
            failed_symbols.append(symbol)
            print(f"  Download failed for {symbol}: {exc}")

    if not downloaded_frames:
        raise RuntimeError(
            "No usable history was downloaded. Existing CSV and metadata were left unchanged."
        )

    downloaded = pd.concat(downloaded_frames, ignore_index=True)
    if existing.empty:
        merged = downloaded
    else:
        merged = pd.concat([existing, downloaded], ignore_index=True)

    merged = merged[REQUIRED_COLUMNS].copy()
    merged["Date"] = pd.to_datetime(merged["Date"], errors="coerce")
    merged["symbol"] = merged["symbol"].astype(str).str.strip().str.upper()
    merged = merged.dropna(subset=["Date", "Close", "Volume"])
    merged = merged.drop_duplicates(subset=["symbol", "Date"], keep="last")
    merged = merged.sort_values(["symbol", "Date"]).reset_index(drop=True)

    if merged.empty:
        raise RuntimeError("Merged history is empty; refusing to replace existing database.")

    coverage = len(set(successful_symbols)) / len(symbols)
    now = _now()
    previous_meta = {}
    if META_FILE.exists():
        try:
            previous_meta = json.loads(META_FILE.read_text(encoding="utf-8"))
        except Exception:
            previous_meta = {}

    # Back up the prior CSV before replacing it.
    if HISTORY_FILE.exists() and HISTORY_FILE.stat().st_size > 0:
        backup_name = f"price_history_before_{now.strftime('%Y%m%d_%H%M%S')}.csv"
        shutil.copy2(HISTORY_FILE, BACKUP_DIR / backup_name)

    temp_csv = HISTORY_FILE.with_suffix(".csv.tmp")
    merged.to_csv(temp_csv, index=False, date_format="%Y-%m-%d")
    os.replace(temp_csv, HISTORY_FILE)

    is_complete = coverage >= SUCCESS_COVERAGE
    meta = {
        "last_update": now.strftime("%Y-%m-%d") if is_complete else previous_meta.get("last_update", ""),
        "last_attempt": now.strftime("%Y-%m-%d %H:%M:%S"),
        "history_period": "18mo bootstrap + 10d rolling merge",
        "symbols": len(symbols),
        "symbols_downloaded": len(successful_symbols),
        "symbols_failed": failed_symbols,
        "download_coverage_pct": round(coverage * 100, 2),
        "rows": int(len(merged)),
        "latest_date": str(pd.to_datetime(merged["Date"]).max().date()),
        "status": "success" if is_complete else "partial",
        "version": 2,
    }
    _write_json_atomic(META_FILE, meta)

    print(
        f"History saved: {len(merged):,} rows; "
        f"{len(successful_symbols)}/{len(symbols)} symbols downloaded "
        f"({coverage:.1%}); status={meta['status']}"
    )
    if failed_symbols:
        print("Symbols with failed/empty downloads:", ", ".join(failed_symbols))
    return meta


def update_if_required() -> bool:
    from utils.history_manager import history_updated_today

    if history_updated_today():
        print("History already updated successfully today.")
        return True

    print("Updating historical database...")
    try:
        result = update_history()
        return result.get("status") == "success"
    except Exception as exc:
        print(f"Historical update did not complete: {exc}")
        return False


if __name__ == "__main__":
    update_history()
