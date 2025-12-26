import sys
import json
import os
from datetime import date
from dotenv import load_dotenv
from app.services.sheets_service import get_sheet
from app.database import SessionLocal
from app.models.models import User, DaySignature

# Load .env from backend folder
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, ".env"))

def diagnose_all():
    original_stdout = sys.stdout
    try:
        with open("diag_output.txt", "w", encoding="utf-8") as f:
            sys.stdout = f
            
            print(f"🕒 SERVER DATE: {date.today()}")
            
            print("\n--- BASE DE DATOS: Users ---")
            db = SessionLocal()
            users = db.query(User).all()
            for u in users:
                print(f"ID: {u.id} | Email: {u.email} | Nombre: '{u.tecnico_nombre}' | Role: {u.role}")

            print("\n--- BASE DE DATOS: DaySignatures ---")
            sigs = db.query(DaySignature).all()
            if not sigs:
                print("LA TABLA DaySignatures ESTÁ VACÍA.")
            for s in sigs:
                print(f"ID: {s.id} | Tech: '{s.tecnico_nombre}' | Fecha: {s.fecha} | Ref: {s.signature_ref}")
            db.close()

            print("\n🔍 DIAGNÓSTICO DE GOOGLE SHEETS")
            sheet = get_sheet()
            if not sheet:
                print("❌ Error: No se pudo conectar a Google Sheets.")
                return

            worksheets = [ws.title for ws in sheet.worksheets()]
            print(f"Pestañas encontradas: {worksheets}")

            for title in ["Bitacora 2025", "Firmas 2025"]:
                if title in worksheets:
                    print(f"\n--- Detalle de '{title}' ---")
                    ws = sheet.worksheet(title)
                    rows = ws.get_all_values()
                    if not rows:
                        print("Vacia.")
                    else:
                        headers = [h.strip().lower() for h in rows[0]]
                        print(f"Headers ({len(headers)}): {headers}")
                        
                        # List all rows for Firmas 2025
                        if title == "Firmas 2025":
                            print(f"\nContenido de '{title}':")
                            for i, row in enumerate(rows[1:], start=2):
                                print(f"Row {i}: {row}")
                        
                        # Check for specific row (Juan Perez today) in Bitacora
                        if title == "Bitacora 2025":
                            print("\nBuscando coincidencias para 'Juan Perez' today (2025-12-25) in Bitacora...")
                            for i, row in enumerate(rows[1:], start=2):
                                if "juan perez" in str(row).lower():
                                    print(f"Row {i}: {row}")
                else:
                    print(f"\n❌ Pestaña '{title}' NO encontrada.")
                    
    finally:
        sys.stdout = original_stdout
    print("✅ Diagnóstico completado. Revisa 'diag_output.txt'.")

if __name__ == "__main__":
    diagnose_all()
