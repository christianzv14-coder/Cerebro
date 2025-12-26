import sys
import os
sys.path.append(os.getcwd())
from io import BytesIO
import pandas as pd
from app.database import SessionLocal
from app.services.excel_service import process_excel_upload
from datetime import date

def test_excel_to_sheets():
    print("--- TESTING EXCEL UPLOAD -> SHEETS SYNC ---")
    db = SessionLocal()
    try:
        # 1. Create a dummy planning Excel
        ticket_id = f"TEST-PLAN-{date.today().strftime('%M%S')}"
        data = {
            'fecha': [date.today()],
            'ticket_id': [ticket_id],
            'tecnico_nombre': ['Juan Perez'],
            'patente': ['TEST-123'],
            'cliente': ['Empresa Test SSync'],
            'direccion': ['Calle Falsa 123'],
            'tipo_trabajo': ['Prueba Sync']
        }
        df = pd.DataFrame(data)
        excel_file = BytesIO()
        df.to_excel(excel_file, index=False)
        excel_file.seek(0)
        
        print(f"Uploading ticket: {ticket_id}...")
        
        # 2. Process upload
        stats = process_excel_upload(excel_file, db)
        print(f"Stats: {stats}")
        
        print("\nSUCCESS: System should have created the activity and synced it to Sheets.")
        print(f"Check your Google Sheet for ticket: {ticket_id}")
        
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_excel_to_sheets()
