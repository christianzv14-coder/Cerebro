import sys
import os
sys.path.append(os.getcwd())
from app.database import SessionLocal
from app.models.models import Activity

def check():
    db = SessionLocal()
    try:
        acts = db.query(Activity).all()
        for a in acts:
            print(f"--- {a.ticket_id} ---")
            print(f"Ticket Hex: {a.ticket_id.encode('utf-8').hex()}")
            print(f"Cliente: {a.cliente}")
            if a.cliente:
                print(f"Cliente Hex: {a.cliente.encode('utf-8').hex()}")
            print(f"State: {a.estado}")
    finally:
        db.close()

if __name__ == "__main__":
    check()
