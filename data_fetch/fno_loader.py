import pandas as pd

def get_fno_symbols():

    df = pd.read_csv(
        "data/fno_symbols.csv",
        encoding="utf-8-sig"
    )

    # if header exists
    if df.columns[0].lower() == "symbol":
        symbols = df.iloc[:,0].dropna().astype(str).str.strip().tolist()
    else:
        # no header
        symbols = df.iloc[:,0].dropna().astype(str).str.strip().tolist()

    print("F&O symbols loaded:", len(symbols))

    return symbols