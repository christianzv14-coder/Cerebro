from app.database import SessionLocal
from app.models.models import DaySignature, User
from datetime import date
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_signatures():
    db = SessionLocal()
    try:
        today = date.today()
        print(f"--- CHECKING SIGNATURES FOR TODAY ({today}) ---")
        
        sigs = db.query(DaySignature).filter(DaySignature.fecha == today).all()
        
        if not sigs:
            print("No signatures found for today.")
        else:
            for s in sigs:
                print(f"FOUND: ID={s.id} Tech='{s.tecnico_nombre}' Time={s.timestamp}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_signatures()
