
from sqlalchemy import create_engine, text
from app.core.config import settings

# Create engine
engine = create_engine(settings.DATABASE_URL)

TECHS_TO_CLEAN = ["Juan Perez", "Pedro Pascal"]

with engine.connect() as conn:
    print("--- CLEANING TEST DATA (ACTIVITIES & SIGNATURES) ---")
    
    for tech in TECHS_TO_CLEAN:
        print(f"\nProcessing '{tech}'...")
        
        # 1. Delete Activities
        res_act = conn.execute(text(f"DELETE FROM activities WHERE tecnico_nombre = '{tech}'"))
        print(f"  - Deleted Activities: {res_act.rowcount}")
        
        # 2. Delete Signatures
        res_sig = conn.execute(text(f"DELETE FROM day_signatures WHERE tecnico_nombre = '{tech}'"))
        print(f"  - Deleted Signatures: {res_sig.rowcount}")
        
    conn.commit()
    print("\n✅ DATA CLEANUP COMPLETE.")
