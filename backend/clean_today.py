from app.database import SessionLocal
from app.models.models import Activity, DaySignature, ActivityState
from app.services.sheets_service import get_sheet, normalize_sheet_date
from datetime import date
import gspread
import os
from dotenv import load_dotenv

# Load .env from backend folder
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, ".env"))

def clean_all():
    today = date.today()
    print(f"=== TOTAL CLEANING FOR {today} (DB + SHEETS) ===")
    
    db = SessionLocal()
    try:
        # 1. DB Cleanup
        sigs = db.query(DaySignature).filter(DaySignature.fecha == today).all()
        print(f"Deleting {len(sigs)} signatures from DB...")
        for s in sigs: db.delete(s)
        
        acts = db.query(Activity).filter(Activity.fecha == today).all()
        print(f"Resetting {len(acts)} activities to PENDIENTE in DB...")
        for a in acts:
            a.estado = ActivityState.PENDIENTE
            a.hora_inicio = None
            a.hora_fin = None
            a.resultado_motivo = None
            a.observacion = None
            a.duracion_min = None
            
        db.commit()
    finally:
        db.close()

    # 2. Google Sheets Cleanup
    print("\nCleaning Google Sheets (Bitacora 2025)...")
    gs = get_sheet()
    if gs:
        try:
            ws = gs.worksheet(f"Bitacora {today.year}")
            rows = ws.get_all_values()
            headers = [h.strip().lower() for h in rows[0]]
            
            # Find columns
            date_col = -1
            for c in ["fecha plan", "fecha"]:
                if c in headers: date_col = headers.index(c); break
                
            state_col = -1
            for c in ["estado final", "estado"]:
                if c in headers: state_col = headers.index(c) + 1; break
                
            sign_col = -1
            if "firmado" in headers: sign_col = headers.index("firmado") + 1
            
            motivo_col = -1
            for c in ["motivo fallo", "motivo fallido", "motivo"]:
                if c in headers: motivo_col = headers.index(c) + 1; break

            today_iso = str(today)
            for i, row in enumerate(rows[1:], start=2):
                if len(row) > date_col and normalize_sheet_date(row[date_col]) == today_iso:
                    print(f"  Resetting row {i} in Sheet...")
                    if state_col: ws.update_cell(i, state_col, "PENDIENTE")
                    if sign_col: ws.update_cell(i, sign_col, "")
                    if motivo_col: ws.update_cell(i, motivo_col, "")
            
            print("Google Sheet cleanup DONE.")
        except Exception as e:
            print(f"Error cleaning sheet: {e}")
    
    print("\n=== CLEANUP COMPLETE ===")

if __name__ == "__main__":
    clean_all()
