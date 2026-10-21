# MBOS EOD Automation Patch

This patch is designed to be copied into the existing `NSE_FNO_SCREENER` project. It does not include the full project and does not replace `main.py`.

## Files in this patch

- `data_fetch/history_updater.py` — safe merge-based historical update with backups and metadata.
- `analytics/data_cache.py` — normalizes symbol/date data and rebuilds cache cleanly.
- `analytics/volume_engine.py` — excludes the current date from historical baseline averages.
- `utils/history_manager.py` — checks successful update metadata and non-empty history.
- `display_engine/excel_writer.py` — same writer with explicit `True` / `False` return status.
- `automation/daily_eod_update.py` — one-shot EOD update, validation, screener build, and dated CSV/XLSX reports.

## Before installing

1. Close the live screener.
2. Make a full copy of your project folder as a backup.
3. Back up `data/price_history.csv`, `data/history_meta.json`, and `screener.xlsx`.
4. Extract this ZIP at the project root, allowing the listed folders/files to merge into the existing folders.

Do not put the patch folder itself inside the project as a nested folder. The resulting path must be:
`NSE_FNO_SCREENER\automation\daily_eod_update.py`

## Run a manual test first

Open the VS Code terminal and run:

```powershell
cd C:\Users\Omkar\Desktop\NSE_FNO_SCREENER
python -m automation.daily_eod_update
```

The first run can take several minutes because new symbols may need an 18-month bootstrap. Check:
- `logs\eod_update.log`
- `data\price_history.csv`
- `data\history_meta.json`
- `reports\` for timestamped CSV and XLSX files
- `screener.xlsx`

The EOD runner requires at least 90% of the F&O universe to have a daily bar dated today. If Yahoo Finance has not published today's daily bars yet, it will retry once after 60 seconds and then fail safely rather than publish a potentially incomplete report.

## Important Excel / Task Scheduler constraint

The existing writer uses `xlwings`, which automates desktop Microsoft Excel. For Windows Task Scheduler, choose **Run only when user is logged on** so Excel COM automation can access the desktop session. Test manually first.

## Task Scheduler setup

Only after the manual run succeeds:

- Trigger: Daily at 4:15 PM (Asia/Kolkata local Windows time).
- Program/script: the full path to the Python executable in your project environment, e.g. `C:\Users\Omkar\Desktop\NSE_FNO_SCREENER\.venv\Scripts\python.exe` if that is your actual venv path.
- Add arguments: `-m automation.daily_eod_update`
- Start in: `C:\Users\Omkar\Desktop\NSE_FNO_SCREENER`
- Select **Run only when user is logged on**.
- Do not enable overlapping runs; if the task is already running, do not start another instance.

## Design notes / limitations

- The history updater downloads 10 days for symbols already in the database and 18 months for symbols not yet present, then merges and deduplicates by symbol/date. It retains old rows when a ticker download fails.
- A timestamped backup is written to `data\backups\` before the historical CSV is replaced.
- `history_meta.json` marks a date successful only when at least 95% of configured symbols downloaded usable rows. Partial runs still save valid merged data but do not mark the date complete.
- The EOD report is built from daily historical bars, not the intraday 1-minute fetcher.
- Yahoo Finance data availability is not guaranteed. This patch validates coverage, but it cannot guarantee the source is complete or exchange-authoritative.
- Do not run the old `data_fetch/yahoo_history.py`; it replaces the history CSV without merging.
