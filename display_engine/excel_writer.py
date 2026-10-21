import pandas as pd
import xlwings as xw
from datetime import datetime

# ----------------------------------------
# Volume formatter (K / M format)
# ----------------------------------------

def format_volume(v):

    if pd.isna(v):
        return ""

    v = float(v)
    sign = "-" if v < 0 else ""
    v = abs(v)

    if v >= 1_000_000:
        return f"{sign}{round(v/1_000_000,2)} M"

    if v >= 1_000:
        return f"{sign}{round(v/1_000,1)} K"

    return f"{sign}{round(v,2)}"

# ----------------------------------------
# Excel writer
# ----------------------------------------

def write_excel(df):
    try:
        # ----------------------------------------
        # Sort + reset index
        # ----------------------------------------
        df = df.sort_values("Vol Change %", ascending=False).reset_index(drop=True)

        # ----------------------------------------
        # Price formatting
        # ----------------------------------------
        if "Price" in df.columns:
            df["Price"] = pd.to_numeric(df["Price"], errors="coerce").fillna(0).round(0).astype(int)

        # ----------------------------------------
        # Rank column
        # ----------------------------------------
        df.insert(0, "Rank", range(1, len(df) + 1))

        # ----------------------------------------
        # Prev vs Avg 10D % (NEW COLUMN)
        # ----------------------------------------
        if "Prev Day Vol" in df.columns and "Avg Vol 10D" in df.columns:
            prev_vol = pd.to_numeric(df["Prev Day Vol"], errors="coerce")
            avg10 = pd.to_numeric(df["Avg Vol 10D"], errors="coerce")
            df["Prev vs Avg 10D %"] = ((prev_vol - avg10) / avg10) * 100

        # ----------------------------------------
        # Percent formatting
        # ----------------------------------------
        percent_cols = [
            "Change %", "Gap %", "Chg from Open %", "Vol Change %", "Prev vs Avg 10D %",
            "Vol vs Avg 10D %", "Vol vs Avg 30D %", "Vol vs Avg 60D %", 
            "Vol vs Avg 90D %", "Perf 1W", "Perf 1M", "Perf 3M", "Perf 6M", "Perf 1Y"
        ]

        # ----------------------------------------
        # Percent columns → keep numeric
        # ----------------------------------------

        for col in percent_cols:

            if col in df.columns:

                df[col] = (
                    pd.to_numeric(df[col], errors="coerce")
                    .round(2)
                )

        # ----------------------------------------
        # Volume formatting
        # ----------------------------------------
        volume_cols = [
            "Volume", "Prev Day Vol", "Avg Vol 10D", "Avg Vol 30D",
            "Avg Vol 60D", "Avg Vol 90D", "Vol Change"
        ]

        for col in volume_cols:
            if col in df.columns:
                df[col] = df[col].apply(format_volume)

        # ----------------------------------------
        # Column order
        # ----------------------------------------
        columns = [
            "Rank", "Current Rank", "Previous Rank", "Rank Δ", "Symbol", "Price", "Change %", "Gap %", "Chg from Open %","Perf 1W", 
            "Perf 1M", "Perf 3M", "Perf 6M", "Perf 1Y", "Volume", "Prev Day Vol", 
            "Prev vs Avg 10D %", "Vol Change %","Vol vs Avg 10D %", "Vol Change", 
            "Avg Vol 10D", "Avg Vol 30D", "Avg Vol 60D", "Avg Vol 90D",
            "Vol vs Avg 30D %", "Vol vs Avg 60D %", "Vol vs Avg 90D %", "Signal",
            "INDEX_NAME", "SIMPLE_INDUSTRY", "BASIC_INDUSTRY", "CONCISE_DEFINITION"
        ]

        columns = [c for c in columns if c in df.columns]
        df = df[columns]

        # ----------------------------------------
        # Last update time
        # ----------------------------------------
        df["Last Update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ----------------------------------------
        # Excel connection
        # ----------------------------------------
        file = "screener.xlsx"
        try:
            wb = xw.Book(file)
            wb.save()
        except:
            wb = xw.Book()
            wb.save(file)

        # *** CRITICAL OPTIMIZATION: Suspend Excel state ***
        app = wb.app
        app.screen_updating = False
        app.calculation = 'manual'    # Prevents Excel from recalculating during write
        app.enable_events = False     # Prevents macros/events from firing

        sheet_name = "Screener"
        if sheet_name in [s.name for s in wb.sheets]:
            ws = wb.sheets[sheet_name]
        else:
            ws = wb.sheets.add(sheet_name)

        # ----------------------------------------
        # Clear sheet & Write Data
        # ----------------------------------------
        ws.clear() # Clears data AND old formats
        
        ws.range("A1").options(index=False, header=True).value = df
        
        # ----------------------------------------
        # Excel dimensions
        # ----------------------------------------

        last_row = len(df) + 1
        last_col = len(df.columns)
        
        
        # ----------------------------------------
        # APPLY EXCEL NUMBER FORMATS
        # ----------------------------------------

        # Percentage columns
        for col in percent_cols:

            if col in df.columns:

                col_idx = df.columns.get_loc(col) + 1

                rng = ws.range((2, col_idx), (last_row, col_idx))

                rng.number_format = '0.00" %"'

                # Price column
                if "Price" in df.columns:

                    col_idx = df.columns.get_loc("Price") + 1

                    rng = ws.range((2, col_idx), (last_row, col_idx))

                    rng.number_format = '0'
        
        ws.range("1:1").api.Font.Bold = True
        
        # ----------------------------------------
        # Formatting, AutoFilter, Freeze Panes
        # ----------------------------------------
        last_row = ws.range("A1").expand().last_cell.row
        last_col = ws.range("A1").expand().last_cell.column
        data_range = ws.range((1, 1), (last_row, last_col))

        try:
            header_range = ws.range((1, 1), (1, last_col))
            header_range.api.WrapText = True
        except: pass

        try:
            ws.api.AutoFilterMode = False
            data_range.api.AutoFilter()
        except: pass

        try:
            ws.activate()
            window = ws.book.app.api.ActiveWindow
            window.SplitRow = 1
            window.SplitColumn = 0
            window.FreezePanes = True
        except: pass

        # ----------------------------------------
        # NEW TRULY FAST COLOR CODING (Bulk FormatConditions)
        # ----------------------------------------
        # To bypass Python's string conversion, we inject Excel formulas that strip "%", "M", and "K" 
        # so Excel evaluates the pure math instantly across thousands of cells.
        
        # 1. Price and Text Columns (Based on Change %)
        if "Change %" in df.columns:
            change_col_idx = df.columns.get_loc("Change %") + 1
            # Get Excel Column Letter (e.g. 'D')
            chg_letter = ws.range((1, change_col_idx)).address.split('$')[1] 
            
            form_pos_change = f'=VALUE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(TRIM(${chg_letter}2), "%", ""), "M", ""), "K", "")) > 0'
            form_neg_change = f'=VALUE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(TRIM(${chg_letter}2), "%", ""), "M", ""), "K", "")) < 0'
            
            target_cols = ["Price", "INDEX_NAME", "SIMPLE_INDUSTRY", "BASIC_INDUSTRY", "CONCISE_DEFINITION"]
            for col in target_cols:
                if col in df.columns:
                    col_idx = df.columns.get_loc(col) + 1
                    rng = ws.range((2, col_idx), (last_row, col_idx))
                    
                    # Type=2 is xlExpression
                    rng.api.FormatConditions.Add(Type=2, Formula1=form_pos_change).Font.Color = 5287936
                    rng.api.FormatConditions.Add(Type=2, Formula1=form_neg_change).Font.Color = 255

        # 2. Remaining Percentage/Volume Columns (Based on their own values)
        color_columns = [
            "Change %", "Gap %", "Chg from Open %", "Vol Change %", "Prev vs Avg 10D %",
            "Vol vs Avg 10D %", "Vol vs Avg 30D %", "Vol vs Avg 60D %", "Vol vs Avg 90D %",
            "Vol Change", "Perf 1W", "Perf 1M", "Perf 3M", "Perf 6M", "Perf 1Y"
        ]

        for col in color_columns:
            if col in df.columns:
                col_idx = df.columns.get_loc(col) + 1
                col_letter = ws.range((1, col_idx)).address.split('$')[1]
                rng = ws.range((2, col_idx), (last_row, col_idx))
                
                form_pos_self = f'=VALUE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(TRIM(${col_letter}2), "%", ""), "M", ""), "K", "")) > 0'
                form_neg_self = f'=VALUE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(TRIM(${col_letter}2), "%", ""), "M", ""), "K", "")) < 0'
                
                rng.api.FormatConditions.Add(Type=2, Formula1=form_pos_self).Font.Color = 5287936
                rng.api.FormatConditions.Add(Type=2, Formula1=form_neg_self).Font.Color = 255

        # Final layout adjustments
        data_range.api.HorizontalAlignment = -4108
        data_range.api.VerticalAlignment = -4108
        data_range.autofit()
        wb.save()
        print("Excel screener updated")
        return True
        

    except Exception as e:
        print("Excel error:", e)
        return False

    finally:
        # Crucial: Always restore Excel's environment states
        try:
            if 'app' in locals():
                app.screen_updating = True
                app.calculation = 'automatic'
                app.enable_events = True
        except: pass

