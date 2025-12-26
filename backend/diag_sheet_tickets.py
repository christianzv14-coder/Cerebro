import sys
import os
sys.path.append(os.getcwd())
from app.services.sheets_service import get_sheet
from datetime import date

def diag():
    sheet = get_sheet()
    if not sheet:
        print("Could not open sheet")
        return
    
    today = date.today()
    title = f"Bitacora {today.year}"
    try:
        ws = sheet.worksheet(title)
        rows = ws.get_all_values()
        if not rows:
            print("Sheet is empty")
            return
        
        headers = rows[0]
        print(f"Headers: {headers}")
        
        # Look for ticket id col
        ticket_col = -1
        for i, h in enumerate(headers):
            if h.strip().lower() in ["ticket id", "ticket_id", "ticket"]:
                ticket_col = i
                break
        
        if ticket_col == -1:
            print("Ticket ID column not found")
        
        print("\nFirst 10 rows (Ticket ID):")
        for i, row in enumerate(rows[1:11], start=2):
            val = row[ticket_col] if ticket_col < len(row) else "N/A"
            print(f"Row {i}: {val}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    diag()
