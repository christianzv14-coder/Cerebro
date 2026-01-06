
import openpyxl

def analyze():
    dest_filename = 'temp_gantt.xlsx'
    wb = openpyxl.load_workbook(filename=dest_filename, data_only=True)
    ws = wb.active
    
    print(f"Sheet Name: {ws.title}")
    
    # scan first 20 rows, 10 cols
    for r in range(1, 20):
        vals = []
        for c in range(1, 15):
            val = ws.cell(row=r, column=c).value
            if val is not None:
                vals.append(f"({r},{c})={val}")
        if vals:
            print(f"Row {r}: {', '.join(vals)}")

if __name__ == "__main__":
    analyze()
