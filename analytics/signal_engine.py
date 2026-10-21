def detect_signal(vol_change_pct, perf_1m, gap_pct):

    # handle missing values
    if vol_change_pct is None or perf_1m is None or gap_pct is None:
        return None

    # volume breakout
    if perf_1m > 10 and vol_change_pct > 20:
        return "VOL_BREAKOUT"

    # accumulation
    if perf_1m > 5 and vol_change_pct > 10:
        return "ACCUMULATION"

    # gap move
    if gap_pct > 2:
        return "GAP_UP"

    if gap_pct < -2:
        return "GAP_DOWN"

    return None