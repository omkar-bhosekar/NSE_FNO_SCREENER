import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# -----------------------
# PAGE SETTINGS
# -----------------------
st.set_page_config(layout="wide")

st.title("📊 NSE Screener Dashboard")

# -----------------------
# AUTO REFRESH
# -----------------------
st_autorefresh(interval=20000)

# -----------------------
# LOAD DATA
# -----------------------
@st.cache_data(ttl=15)
def load_data():

    try:

        df = pd.read_excel("screener.xlsx")

        return df

    except Exception as e:

        st.error(f"Error loading Excel: {e}")

        return pd.DataFrame()


df = load_data()

# -----------------------
# EMPTY CHECK
# -----------------------
if df.empty:

    st.warning("No data available")

    st.stop()

# -----------------------
# HANDLE INDUSTRY COLUMN
# -----------------------
if "Industry" not in df.columns and "BASIC_INDUSTRY" in df.columns:

    df["Industry"] = df["BASIC_INDUSTRY"]

# -----------------------
# PERCENT COLUMNS
# -----------------------
PERCENT_COLUMNS = [

    "Change %",
    "Gap %",
    "Chg from Open %",
    "Vol Change %",
    "Prev vs Avg 10D %",
    "Vol vs Avg 10D %",
    "Vol vs Avg 30D %",
    "Vol vs Avg 60D %",
    "Vol vs Avg 90D %",
    "Perf 1W",
    "Perf 1M",
    "Perf 3M",
    "Perf 6M",
    "Perf 1Y"
]

# -----------------------
# ENSURE NUMERIC
# -----------------------
for col in PERCENT_COLUMNS:

    if col in df.columns:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).round(2)

# -----------------------
# SIDEBAR FILTERS
# -----------------------
st.sidebar.title("📌 Market Filters")

# -----------------------
# INDEX FILTER
# -----------------------
selected_index = st.sidebar.selectbox(
    "Sector (INDEX_NAME)",
    ["All"] + sorted(
        df["INDEX_NAME"].dropna().unique().tolist()
    )
)

# -----------------------
# INDUSTRY FILTER
# -----------------------
selected_industry = st.sidebar.selectbox(
    "Industry",
    ["All"] + sorted(
        df["Industry"].dropna().unique().tolist()
    )
)

# -----------------------
# SIGNAL FILTER
# -----------------------
if "Signal" in df.columns:

    selected_signal = st.sidebar.selectbox(
        "Signal",
        ["All"] + sorted(
            df["Signal"].dropna().unique().tolist()
        )
    )

else:

    selected_signal = "All"

# -----------------------
# APPLY FILTERS
# -----------------------
if selected_index != "All":

    df = df[df["INDEX_NAME"] == selected_index]

if selected_industry != "All":

    df = df[df["Industry"] == selected_industry]

if selected_signal != "All":

    df = df[df["Signal"] == selected_signal]

# -----------------------
# FILTERED EMPTY CHECK
# -----------------------
if df.empty:

    st.warning("No matching stocks")

    st.stop()
    
# -----------------------
# DISPLAY COPY
# -----------------------
display_df = df.copy()

# -----------------------
# FORMAT % FOR DISPLAY
# -----------------------
for col in PERCENT_COLUMNS:

    if col in display_df.columns:

        display_df[col] = display_df[col].apply(
            lambda x: f"{x:.2f} %" if pd.notna(x) else ""
        )

# -----------------------
# COLOR LOGIC
# -----------------------
def highlight_cells(row):

    styles = [""] * len(row)

    # -----------------------
    # COLOR BASED ON Change %
    # -----------------------

    try:
        change = float(
            str(row.get("Change %"))
            .replace("%", "")
            .strip()
        )
    except:
        change = 0


    if pd.notna(change):

        color = (
            "#00C853"
            if change > 0
            else "#D50000"
            if change < 0
            else ""
        )

        target_cols = [
            "Price",
            "INDEX_NAME",
            "SIMPLE_INDUSTRY",
            "BASIC_INDUSTRY",
            "CONCISE_DEFINITION"
        ]

        for col in target_cols:

            if col in row.index:

                styles[row.index.get_loc(col)] = (
                    f"color: {color}; font-weight: bold"
                )

    # -----------------------
    # SELF COLORING
    # -----------------------

    self_columns = PERCENT_COLUMNS + ["Vol Change"]

    for col in self_columns:

        if col in row.index:

            val = row[col]

            try:

                val = float(str(val).replace("%", "").strip())

                if val > 0:

                    styles[row.index.get_loc(col)] = (
                        "color: #00C853; font-weight: bold"
                    )

                elif val < 0:

                    styles[row.index.get_loc(col)] = (
                        "color: #D50000; font-weight: bold"
                    )

            except:
                pass

    return styles

# -----------------------
# TABLE
# -----------------------
st.subheader("📋 Data Table")

styled_df = display_df.style.apply(
    highlight_cells,
    axis=1,
    raw=False
)

st.dataframe(
    styled_df,
    width="stretch",
    height=700
)

# ============================================================
# STOCK MOVES CHART
# ============================================================

st.subheader("📈 Stock Moves - Change from Open %")

if "Symbol" in df.columns and "Chg from Open %" in df.columns:

    df_chart = df.copy()

    # -----------------------
    # USE Chg from Open %
    # -----------------------

    df_chart["Change_num"] = pd.to_numeric(
        df_chart["Chg from Open %"],
        errors="coerce"
    )

    # -----------------------
    # FILTER ±1%
    # -----------------------

    df_chart = df_chart[
        (df_chart["Change_num"] >= 1)
        |
        (df_chart["Change_num"] <= -1)
    ]

    # -----------------------
    # GAINERS / LOSERS
    # -----------------------

    gainers = df_chart[df_chart["Change_num"] >= 1]

    losers = df_chart[df_chart["Change_num"] <= -1]

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Gainers ≥ 1%",
            len(gainers)
        )

    with col2:

        st.metric(
            "Losers ≤ -1%",
            len(losers)
        )

    # -----------------------
    # SORT
    # -----------------------

    df_sorted = df_chart.sort_values("Change_num")

    # -----------------------
    # CHART
    # -----------------------

    fig1 = px.bar(
        df_sorted,
        x="Symbol",
        y="Change_num",
        color="Change_num",
        color_continuous_scale=[
            "red",
            "white",
            "green"
        ]
    )

    st.plotly_chart(
        fig1,
        width="stretch"
    )

else:

    st.warning(
        "Columns missing for stock chart"
    )

st.divider()

# ============================================================
# VOLUME MOVERS
# ============================================================

st.subheader("📊 Volume Movers - Vol Change %")

if "Symbol" in df.columns and "Vol Change %" in df.columns:

    df_chart_vol = df.copy()

    df_chart_vol["Vol_num"] = pd.to_numeric(
        df_chart_vol["Vol Change %"],
        errors="coerce"
    )

    df_sorted_vol = df_chart_vol.sort_values(
        "Vol_num"
    )

    fig_vol = px.bar(
        df_sorted_vol,
        x="Symbol",
        y="Vol_num",
        color="Vol_num",
        color_continuous_scale=[
            "red",
            "white",
            "green"
        ]
    )

    st.plotly_chart(
        fig_vol,
        width="stretch"
    )

else:

    st.warning(
        "Columns missing for volume chart"
    )

st.divider()

# ============================================================
# SECTOR PERFORMANCE
# ============================================================

st.subheader("🏭 Sector Performance (INDEX_NAME) - Chg from Open %")

if (
    "INDEX_NAME" in df.columns
    and
    "Chg from Open %" in df.columns
):

    sector_df = (
        df.groupby("INDEX_NAME")
        .agg(
            Change_num=("Chg from Open %", "mean"),
            Stock_Count=("Symbol", "count")
        )
        .reset_index()
        .sort_values("Change_num")
    )

    # -----------------------
    # LABEL
    # -----------------------

    sector_df["label"] = (
        sector_df["INDEX_NAME"]
        +
        " ("
        +
        sector_df["Stock_Count"].astype(str)
        +
        ")"
    )

    # -----------------------
    # DISPLAY STRING
    # -----------------------

    sector_df["Change_str"] = (
        sector_df["Change_num"]
        .apply(lambda x: f"{x:.2f}%")
    )

    # -----------------------
    # TOP / WEAK
    # -----------------------

    if not sector_df.empty:

        top_sector = sector_df.iloc[-1]

        weak_sector = sector_df.iloc[0]

        st.success(
            f"🔥 Strongest Sector: "
            f"{top_sector['INDEX_NAME']} "
            f"({top_sector['Change_num']:.2f}%)"
        )

        st.error(
            f"📉 Weakest Sector: "
            f"{weak_sector['INDEX_NAME']} "
            f"({weak_sector['Change_num']:.2f}%)"
        )

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Total Sectors",
                len(sector_df)
            )

        with col2:

            st.metric(
                "Top Sector Strength",
                f"{top_sector['Change_num']:.2f}%"
            )

    # -----------------------
    # CHART
    # -----------------------

    fig2 = px.bar(
        sector_df,
        x="Change_num",
        y="label",
        orientation="h",
        color="Change_num",
        text="Change_str",
        color_continuous_scale=[
            "red",
            "white",
            "green"
        ],
        height=700
    )

    fig2.update_traces(
        textposition="outside",
        textfont=dict(size=11),
        marker_line_width=0,
        cliponaxis=False
    )

    fig2.update_layout(
        yaxis=dict(
            tickfont=dict(size=11),
            categoryorder="total ascending"
        )
    )

    fig2.update_traces(
        hovertemplate="%{y}<br>%{x:.2f}%<extra></extra>"
    )

    st.plotly_chart(
        fig2,
        width="stretch"
    )

else:

    st.warning(
        "INDEX_NAME or Chg from Open % not found"
    )

# ============================================================
# LAST UPDATE
# ============================================================

if "Last Update" in df.columns:

    st.caption(
        f"Last Updated: "
        f"{df['Last Update'].iloc[0]}"
    )