
import openpyxl

def debug_gantt():
    fpath = "outputs/gantt_Final_Revertido_FIX.xlsx"
    print(f"Inspecting File: {fpath}")
    
    wb = openpyxl.load_workbook(fpath)
    ws = wb.active
    
    COL_START_DAY = 7 # G
    START_ROW = 5
    
    total_val = 0
    total_count = 0
    non_numeric = 0
    
    for r in range(START_ROW, 200):
        # Scan columns G to BO (approx 60 days)
        for c in range(COL_START_DAY, COL_START_DAY + 62):
            cell = ws.cell(row=r, column=c)
            v = cell.value
            
            if v is not None:
                # print(f"Row {r} Col {c}: {v} (Type: {type(v)})")
                if isinstance(v, (int, float)):
                    total_val += v
                    total_count += 1
                else:
                    print(f"WARNING: Non-numeric value at Row {r} Col {c}: {v} type {type(v)}")
                    non_numeric += 1
                    try:
                        total_val += float(v)
                    except:
                        pass
                        
    print(f"--- SCAN RESULT ---")
    print(f"Total Sum of Grid (Numeric): {total_val}")
    print(f"Non-numeric Cells: {non_numeric}")
    
    if total_val == 314:
        print("PYTHON SEES 314.")
    else:
        print(f"PYTHON SEES {total_val}. Discrepancy!")

if __name__ == "__main__":
    debug_gantt()
