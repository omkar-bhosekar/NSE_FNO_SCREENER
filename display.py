from tabulate import tabulate

def show_table(df):



    if df is None or df.empty:

        print("\nNo data available.\n")

        return



    # -----------------------------------------------------------

    # Sort by Volume Change %

    # -----------------------------------------------------------



    if "Vol Change %" in df.columns:

        df = df.sort_values("Vol Change %", ascending=False).reset_index(drop=True)



    print("\n")

    print("===== NSE F&O LIVE SCREENER =====")

    print("\n")



    # -----------------------------------------------------------

    # Columns to display

    # -----------------------------------------------------------



    columns = [

        "Symbol",

        "Price",

        "Change %",

        "Gap %",

        "Chg from Open %",

        "Volume",

        "Avg Vol 10D",

        "Avg Vol 30D",

        "Avg Vol 60D",

        "Avg Vol 90D",

        "Vol Change",

        "Vol Change %",

        "Perf 1W",

        "Perf 1M",

        "Perf 3M",

        "Perf 6M",

        "Perf 1Y",

        "Signal"

    ]



    # Keep only columns that exist

    available_cols = [c for c in columns if c in df.columns]



    # -----------------------------------------------------------

    # Print table

    # -----------------------------------------------------------



    print(

        tabulate(

            df[available_cols],

            headers="keys",

            tablefmt="pretty",

            showindex=False

        )

    ) 