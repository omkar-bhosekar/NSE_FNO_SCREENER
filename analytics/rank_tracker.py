import pandas as pd
import os

# ============================================================
# SNAPSHOT FILE
# ============================================================

RANK_FILE = "data/volume_rank_snapshot.csv"


# ============================================================
# UPDATE VOLUME RANKS
# ============================================================

def update_volume_ranks(df):

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

    if "Vol Change %" not in df.columns:
        return df

    # --------------------------------------------------------
    # SORT BY VOLUME CHANGE %
    # --------------------------------------------------------

    df = df.sort_values(
        "Vol Change %",
        ascending=False
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # CURRENT RANK
    # --------------------------------------------------------

    df["Current Rank"] = df.index + 1

    # --------------------------------------------------------
    # DEFAULT VALUES
    # --------------------------------------------------------

    df["Previous Rank"] = None
    df["Rank Δ"] = 0

    # --------------------------------------------------------
    # LOAD OLD SNAPSHOT
    # --------------------------------------------------------

    if os.path.exists(RANK_FILE):

        prev_df = pd.read_csv(RANK_FILE)

        prev_rank_map = dict(
            zip(
                prev_df["Symbol"],
                prev_df["Current Rank"]
            )
        )

        # ----------------------------------------------------
        # MAP PREVIOUS RANK
        # ----------------------------------------------------

        df["Previous Rank"] = df["Symbol"].map(
            prev_rank_map
        )

        # ----------------------------------------------------
        # CALCULATE RANK DELTA
        # ----------------------------------------------------

        df["Rank Δ"] = (
            df["Previous Rank"]
            -
            df["Current Rank"]
        )

        df["Rank Δ"] = (
            df["Rank Δ"]
            .fillna(0)
            .astype(int)
        )

    # --------------------------------------------------------
    # SAVE CURRENT SNAPSHOT
    # --------------------------------------------------------

    save_df = df[[
        "Symbol",
        "Current Rank"
    ]]

    save_df.to_csv(
        RANK_FILE,
        index=False
    )

    return df