from app.database import SessionLocal
from app.models.models import User, DaySignature, Activity
from datetime import date
import os

def diag():
    db = SessionLocal()
    print("--- DIAGNOSTIC START ---")
    try:
        today = date.today()
        print(f"Server Date: {today}")
        
        # 1. Check Signatures
        sigs = db.query(DaySignature).all()
        print(f"\nTotal Signatures in DB: {len(sigs)}")
        for s in sigs:
            print(f" - Tech: {s.tecnico_nombre} | Date: {s.fecha} | Ref: {s.signature_ref} | Created: {s.timestamp}")

        # 2. Check Files
        sig_dir = "uploads/signatures"
        if os.path.exists(sig_dir):
            files = os.listdir(sig_dir)
            print(f"\nFiles in {sig_dir}: {len(files)}")
            for f in files:
                size = os.path.getsize(os.path.join(sig_dir, f))
                print(f" - File: {f} ({size} bytes)")
        else:
            print(f"\nDirectory {sig_dir} does NOT exist.")

        # 3. Check Activities for Juan
        acts = db.query(Activity).filter(Activity.fecha == today).all()
        print(f"\nActivities Today: {len(acts)}")
        for a in acts:
            print(f" - {a.ticket_id}: {a.estado} (Tech: {a.tecnico_nombre})")

    finally:
        db.close()
    print("\n--- DIAGNOSTIC END ---")

if __name__ == "__main__":
    diag()
