
import os
import sys
import pandas as pd
from io import BytesIO
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add backend to path
sys.path.append(os.getcwd())

from app.services.excel_service import process_excel_upload
from app.models.models import ActivityState

# Mock SQLAlchemy Session and Models
class MockSession:
    def query(self, *args): 
        return self
    def filter(self, *args): 
        return self
    def delete(self): 
        return 0
    def first(self): 
        return None # Simulate not found -> Create new
    def all(self):
        return [] # Return empty list for mock users
    def add(self, *args): 
        print("[MOCK DB] Adding record...")
    def commit(self): 
        print("[MOCK DB] Commit.")
    def refresh(self, *args): 
        pass
    def rollback(self):
        print("[MOCK DB] Rollback.")

def test_flow():
    print("--- TESTING FULL UPLOAD FLOW (WITH MOCK DB) ---")
    
    # 1. Create a dummy Excel file in memory
    print("Creating dummy Excel file...")
    df = pd.DataFrame({
        'fecha': ['2023-10-27', '2023-10-27', '2023-10-27'],
        'ticket_id': ['TICKET-TEST-001', 'TICKET-TEST-002', 'TICKET-TEST-003'],
        'tecnico_nombre': ['Juan Perez', 'Pedro Gonzalez', 'Pedro Gonzalez'],
        'patente': ['AB-CD-12', 'XY-ZA-99', 'XY-ZA-99'],
        'cliente': ['Cliente Test', 'Cliente Pedro 1', 'Cliente Pedro 2'],
        'direccion': ['Calle Falsa 123', 'Av Siempre Viva 742', 'Callejon 9'],
        'tipo_trabajo': ['Instalacion', 'Reparacion', 'Revision'],
        'Prioridad': ['Alta', 'Media', 'Baja'],
        'Comuna': ['Santiago', 'Providencia', 'Las Condes'],
        'Region': ['Metropolitana', 'Metropolitana', 'Metropolitana']
    })
    
    excel_file = BytesIO()
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    excel_file.seek(0)
    
    # 2. Mock DB
    mock_db = MockSession()
    
    # 3. Run Process
    print("Running process_excel_upload...")
    try:
        stats = process_excel_upload(excel_file, mock_db)
        print("\nProcess Result Stats:", stats)
        print("SUCCESS! If you received an email, the flow works.")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_flow()
