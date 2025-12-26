import sys
import os
sys.path.append(os.getcwd())
from app.services.sheets_service import get_sheet

def inspect():
    sheet = get_sheet()
    if not sheet: return
    ws = sheet.worksheet("Bitacora 2025")
    all_rows = ws.get_all_values()
    headers = all_rows[0]
    
    print("--- BITACORA 2025 INSPECTION ---")
    for i, row in enumerate(all_rows[1:5], start=2):
        print(f"\nRow {i}:")
        for col_idx, val in enumerate(row):
            header = headers[col_idx] if col_idx < len(headers) else f"Col{col_idx+1}"
            print(f"  {header}: {val}")

if __name__ == "__main__":
    inspect()
