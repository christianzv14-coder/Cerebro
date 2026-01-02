import sys
import os

# Add current directory to path so we can import app modules
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models.models import User # Required for relationship mapper
from app.models.finance import Commitment
from app.services.sheets_service import sync_commitment_to_sheet

def force_sync():
    print("Connecting to DB...")
    db = SessionLocal()
    try:
        commitments = db.query(Commitment).all()
        print(f"Found {len(commitments)} commitments.")
        
        for c in commitments:
            print(f"Syncing {c.title}...")
            sync_commitment_to_sheet(c)
            
        print("Done! Check your Google Sheet now.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    force_sync()
