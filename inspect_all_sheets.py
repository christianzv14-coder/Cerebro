
import pandas as pd

def inspect_all():
    fpath = "c:/Users/chzam/OneDrive/Desktop/cerebro-patio/Cerebro/Detalle Entel.xlsx"
    xls = pd.ExcelFile(fpath)
    print(f"Sheets: {xls.sheet_names}")
    
    for sheet in xls.sheet_names:
        print(f"\n--- SHEET: {sheet} ---")
        try:
            df = pd.read_excel(xls, sheet_name=sheet, nrows=5, header=None)
            for i, row in df.iterrows():
                # Check for ID pattern in row
                row_list = row.tolist()
                found_id = any(str(x).startswith('569') for x in row_list)
                prefix = "**FOUND ID**" if found_id else ""
                print(f"{prefix} Row {i}: {row_list}")
        except Exception as e:
            print(f"Error reading {sheet}: {e}")

if __name__ == "__main__":
    inspect_all()
