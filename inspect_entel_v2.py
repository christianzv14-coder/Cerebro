
import openpyxl
import os

def inspect_entel_v2():
    dpath = "c:/Users/chzam/OneDrive/Desktop/cerebro-patio/Cerebro"
    fname = "Detalle Entel.xlsx"
    fpath = os.path.join(dpath, fname)
    
    print(f"Reading (Read-Only) from: {fpath}")
    
    try:
        wb = openpyxl.load_workbook(fpath, read_only=True, data_only=True)
        ws = wb.active
        print("\n--- FIRST 5 ROWS ---")
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i >= 5: break
            print(f"Row {i+1}: {row}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_entel_v2()
