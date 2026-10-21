"""History update status helpers."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
META_FILE = ROOT / "data" / "history_meta.json"
HISTORY_FILE = ROOT / "data" / "price_history.csv"
IST = ZoneInfo("Asia/Kolkata")


def history_updated_today():
    if not META_FILE.exists() or not HISTORY_FILE.exists() or HISTORY_FILE.stat().st_size == 0:
        return False
    try:
        meta = json.loads(META_FILE.read_text(encoding="utf-8"))
        if meta.get("last_update") != datetime.now(IST).strftime("%Y-%m-%d"):
            return False
        # New metadata must be successful. Older metadata without status is accepted
        # only when it records a date and the CSV exists and is non-empty.
        return meta.get("status", "success") == "success" and int(meta.get("rows", 0)) > 0
    except Exception:
        return False
