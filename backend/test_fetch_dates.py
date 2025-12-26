import sys
import os
sys.path.append(os.getcwd())
from app.database import SessionLocal
from app.models.models import Activity, User
from datetime import date

def test_fetch():
    db = SessionLocal()
    tech_name = "Juan Perez"
    dates = [date(2025, 12, 25), date(2025, 12, 26)]
    
    for d in dates:
        print(f"\n--- Fetching for {d} ---")
        acts = db.query(Activity).filter(Activity.tecnico_nombre == tech_name, Activity.fecha == d).all()
        if not acts:
            print("No activities found")
        for a in acts:
            print(f"TKT: {a.ticket_id} | STATE: {a.estado}")

if __name__ == "__main__":
    test_fetch()
