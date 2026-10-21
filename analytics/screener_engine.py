# ============================================================
# NSE F&O SCREENER ENGINE
# Builds one screener row for each symbol
# ============================================================

from analytics.volume_engine import calculate_volume_metrics
from analytics.performance_engine import calculate_performance
from analytics.signal_engine import detect_signal


# ============================================================
# STANDARDIZATION HELPERS
# ============================================================

def safe_float(value, default=0):

    try:
        if value is None:
            return default

        return round(float(value), 2)

    except:
        return default


def safe_percent(value):

    return safe_float(value, 0)


# ============================================================
# EMPTY FALLBACKS
# ============================================================

EMPTY_VOLUME_DATA = {
    "avg10": 0,
    "avg30": 0,
    "avg60": 0,
    "avg90": 0,
    "vol_change": 0,
    "vol_change_pct": 0,
    "vol_vs_avg10": 0,
    "vol_vs_avg30": 0,
    "vol_vs_avg60": 0,
    "vol_vs_avg90": 0
}

EMPTY_PERFORMANCE_DATA = {
    "perf_1w": 0,
    "perf_1m": 0,
    "perf_3m": 0,
    "perf_6m": 0,
    "perf_1y": 0
}


# ============================================================
# BUILD SCREENER ROW
# ============================================================

def build_screener_row(
    symbol,
    price,
    volume,
    prev_volume,
    open_price,
    prev_close
):

    # ============================================================
    # LIVE PRICE CALCULATIONS
    # ============================================================

    if prev_close and prev_close != 0:

        change_pct = ((price - prev_close) / prev_close) * 100

        gap_pct = ((open_price - prev_close) / prev_close) * 100

    else:

        change_pct = 0
        gap_pct = 0

    # ------------------------------------------------------------

    if open_price and open_price != 0:

        chg_from_open = ((price - open_price) / open_price) * 100

    else:

        chg_from_open = 0

    # ============================================================
    # HISTORICAL ANALYTICS
    # ============================================================

    volume_data = calculate_volume_metrics(
        symbol,
        volume,
        prev_volume
    )

    perf_data = calculate_performance(symbol)

    # ============================================================
    # SAFETY FALLBACKS
    # ============================================================

    if volume_data is None:
        volume_data = EMPTY_VOLUME_DATA.copy()

    if perf_data is None:
        perf_data = EMPTY_PERFORMANCE_DATA.copy()

    # ============================================================
    # SIGNAL DETECTION
    # ============================================================

    signal = detect_signal(
        volume_data.get("vol_change_pct", 0),
        perf_data.get("perf_1m", 0),
        gap_pct
    )

    # ============================================================
    # FINAL SCREENER ROW
    # ============================================================

    row = {

        # ========================================================
        # BASIC
        # ========================================================

        "Symbol": symbol,

        "Price": safe_float(price),

        # ========================================================
        # PRICE MOVEMENT %
        # ========================================================

        "Change %": safe_percent(change_pct),

        "Gap %": safe_percent(gap_pct),

        "Chg from Open %": safe_percent(chg_from_open),

        # ========================================================
        # VOLUME
        # ========================================================

        "Volume": safe_float(volume),

        "Prev Day Vol": safe_float(prev_volume),

        # ========================================================
        # VOLUME AVERAGES
        # ========================================================

        "Avg Vol 10D": safe_float(volume_data.get("avg10")),

        "Avg Vol 30D": safe_float(volume_data.get("avg30")),

        "Avg Vol 60D": safe_float(volume_data.get("avg60")),

        "Avg Vol 90D": safe_float(volume_data.get("avg90")),

        # ========================================================
        # VOLUME VS AVERAGES %
        # ========================================================

        "Vol vs Avg 10D %": safe_percent(
            volume_data.get("vol_vs_avg10")
        ),

        "Vol vs Avg 30D %": safe_percent(
            volume_data.get("vol_vs_avg30")
        ),

        "Vol vs Avg 60D %": safe_percent(
            volume_data.get("vol_vs_avg60")
        ),

        "Vol vs Avg 90D %": safe_percent(
            volume_data.get("vol_vs_avg90")
        ),

        # ========================================================
        # VOLUME CHANGE
        # ========================================================

        "Vol Change": safe_float(
            volume_data.get("vol_change")
        ),

        "Vol Change %": safe_percent(
            volume_data.get("vol_change_pct")
        ),

        # ========================================================
        # PERFORMANCE %
        # ========================================================

        "Perf 1W": safe_percent(
            perf_data.get("perf_1w")
        ),

        "Perf 1M": safe_percent(
            perf_data.get("perf_1m")
        ),

        "Perf 3M": safe_percent(
            perf_data.get("perf_3m")
        ),

        "Perf 6M": safe_percent(
            perf_data.get("perf_6m")
        ),

        "Perf 1Y": safe_percent(
            perf_data.get("perf_1y")
        ),

        # ========================================================
        # SIGNAL
        # ========================================================

        "Signal": signal
    }

    return row