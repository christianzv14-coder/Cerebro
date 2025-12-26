import sys
import os
sys.path.append(os.getcwd())
from app.database import SessionLocal
from app.models.models import Activity, DaySignature

def check():
    db = SessionLocal()
    try:
        print("--- ACTIVITIES ---")
        acts = db.query(Activity).all()
        for a in acts:
            print(f"ID: {a.ticket_id}, Ticket: {a.ticket_id}, Fecha: {a.fecha}, State: {a.estado}, Tech: {a.tecnico_nombre}")
            
        print("\n--- SIGNATURES ---")
        sigs = db.query(DaySignature).all()
        for s in sigs:
            print(f"ID: {s.id}, Tech: {s.tecnico_nombre}, Date: {s.fecha}")
    finally:
        db.close()

if __name__ == "__main__":
    check()
