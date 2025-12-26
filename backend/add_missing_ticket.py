import sys
import os
sys.path.append(os.getcwd())
from app.services.sheets_service import get_sheet
from datetime import date

def add_ticket():
    sheet = get_sheet()
    if not sheet: return
    
    today = date.today()
    ws = sheet.worksheet(f"Bitacora {today.year}")
    
    # Check if already exists
    rows = ws.get_all_values()
    if any(row[3] == "TKT-M1-01" for row in rows if len(row) > 3):
        print("Already exists")
        return
        
    print("Adding TKT-M1-01 to Sheet...")
    # Row structure: Año, Fecha Plan, Fecha Cierre, Ticket ID, Tecnico, Patente, Cliente, Direccion, Tipo Trabajo, Estado Final, ...
    new_row = [
        str(today.year),
        str(today),
        "",
        "TKT-M1-01",
        "Juan Perez",
        "XY-9999",
        "Cliente Manana",
        "Ruta 66 km 10",
        "Mantenimiento",
        "PENDIENTE"
    ]
    ws.append_row(new_row)
    print("Done")

if __name__ == "__main__":
    add_ticket()
