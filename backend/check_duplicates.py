
import os
import sys
from collections import defaultdict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.getcwd())

from app.database import Base
from app.models.models import User, Activity

# Setup DB connection
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def check_duplicates():
    print("--- CHECKING FOR DUPLICATE USERS (CASE INSENSITIVE) ---")
    users = db.query(User).all()
    
    seen = defaultdict(list)
    for u in users:
        key = u.tecnico_nombre.strip().lower()
        seen[key].append(u.tecnico_nombre)
        
    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    
    if duplicates:
        print("FOUND DUPLICATES:")
        for k, v in duplicates.items():
            print(f"  '{k}': {v}")
    else:
        print("No casing duplicates found for users.")

    print("\n--- CHECKING ACTIVITIES VS USERS ---")
    activities = db.query(Activity).all()
    orphan_activities = 0
    
    user_names = {u.tecnico_nombre for u in users}
    
    for act in activities:
        if act.tecnico_nombre not in user_names:
            print(f"Warning: Activity {act.ticket_id} has tech '{act.tecnico_nombre}' which is NOT in Users table.")
            orphan_activities += 1
            
    print(f"Total Orphan Activities: {orphan_activities}")

if __name__ == "__main__":
    check_duplicates()
