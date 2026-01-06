
import openpyxl

def inspect_raw():
    fpath = "c:/Users/chzam/OneDrive/Desktop/cerebro-patio/Cerebro/Detalle Entel.xlsx"
    print(f"Opening {fpath}...")
    
    wb = openpyxl.load_workbook(fpath, data_only=True)
    ws = wb.active
    
    print("\n--- RAW CELL DUMP (Rows 1-5, Cols A-O) ---")
    for r in range(1, 6):
        row_vals = []
        for c in range(1, 16): # A to O
            cell = ws.cell(row=r, column=c)
            row_vals.append(f"{cell.coordinate}:{cell.value}")
        print(f"Row {r}: {row_vals}")

if __name__ == "__main__":
    inspect_raw()
