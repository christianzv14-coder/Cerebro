import sys
import os
sys.path.append(os.getcwd())
from app.database import SessionLocal
from app.models.models import Activity
from app.services.sheets_service import sync_activity_to_sheet

def test_sync():
    db = SessionLocal()
    try:
        act = db.query(Activity).filter(Activity.ticket_id == "TKT-001").first()
        if not act:
            print("Activity not found in DB")
            return
        
        print(f"Syncing {act.ticket_id} with state {act.estado}...")
        sync_activity_to_sheet(act)
        print("Done")
    finally:
        db.close()

if __name__ == "__main__":
    test_sync()
