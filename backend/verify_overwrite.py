import sys
import os
sys.path.append(os.getcwd())
from io import BytesIO
import pandas as pd
from app.database import SessionLocal
from app.models.models import Activity
from app.services.excel_service import process_excel_upload
from datetime import date

def verify_overwrite():
    print("--- VERIFYING EXCEL OVERWRITE LOGIC ---")
    db = SessionLocal()
    tech_name = "Juan Perez"
    today = date.today()
    
    try:
        # 1. Ensure there is at least one PENDIENTE activity for today
        act = db.query(Activity).filter(Activity.tecnico_nombre == tech_name, Activity.fecha == today).first()
        if not act:
            print("Creating a dummy activity to test deletion...")
            act = Activity(ticket_id="TKT-TO-DELETE", tecnico_nombre=tech_name, fecha=today)
            db.add(act)
            db.commit()
        
        print(f"Current activities for {tech_name} on {today} confirmed.")
        
        # 2. Upload a new Excel with DIFFERENT tickets for the same date/tech
        data = {
            'fecha': [today],
            'ticket_id': [f"NEW-TICKET-{date.today().strftime('%H%M')}"],
            'tecnico_nombre': [tech_name],
            'patente': ['OVER-123'],
            'cliente': ['Overwritten Inc'],
            'direccion': ['Nowhere'],
            'tipo_trabajo': ['Clean Test']
        }
        df = pd.DataFrame(data)
        excel_file = BytesIO()
        df.to_excel(excel_file, index=False)
        excel_file.seek(0)
        
        print("Uploading new plan...")
        process_excel_upload(excel_file, db)
        
        # 3. Check if previous tickets are gone
        remaining = db.query(Activity).filter(Activity.tecnico_nombre == tech_name, Activity.fecha == today).all()
        print(f"\nActivities remaining for {tech_name} on {today}:")
        for r in remaining:
            print(f"  - {r.ticket_id} ({r.estado})")
            
        if any(r.ticket_id == "TKT-TO-DELETE" for r in remaining):
            print("\nFAILURE: Old activity was NOT deleted.")
        else:
            print("\nSUCCESS: Old PENDIENTE activities were cleared before upload.")
            
    finally:
        db.close()

if __name__ == "__main__":
    verify_overwrite()
