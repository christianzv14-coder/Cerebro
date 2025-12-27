import sqlite3
# actually we use postgres, so usually psycopg2 or via sqlalchemy text
from sqlalchemy import text
from app.database import SessionLocal

def consolidate_raw():
    print("--- CONSOLIDATE RAW SQL ---")
    db = SessionLocal()
    try:
        # 1. Check who we have
        # Target: want pedro.pascal@cerebro.com to be 'Pedro Pascal' and have all activities.
        # Current: 
        #   pedro.pascal@cerebro.com -> 'Pedro pascal' (Activities: 0)
        #   pedro@cerebro.com        -> 'Pedro Pascal' (Activities: X)
        
        # Step A: Move Activities from 'Pedro Pascal' (bad match) to 'Pedro pascal' (good user current name)
        # We temporarily degrade the activity tech name to match the target user's current lowercase name.
        print("Step 1: Point activities to 'Pedro pascal'...")
        db.execute(text("UPDATE activities SET tecnico_nombre = 'Pedro pascal' WHERE tecnico_nombre = 'Pedro Pascal'"))
        db.commit()
        
        # Step B: Now 'pedro@cerebro.com' has NO activities linked (because we changed them to lowercase).
        # So we can delete 'pedro@cerebro.com'.
        print("Step 2: Delete duplicate 'pedro@cerebro.com'...")
        db.execute(text("DELETE FROM users WHERE email = 'pedro@cerebro.com'"))
        db.commit()
        
        # Step C: Rename 'pedro.pascal@cerebro.com' to 'Pedro Pascal' (Capitalized)
        print("Step 3: Capitalize user 'Pedro pascal' -> 'Pedro Pascal'...")
        db.execute(text("UPDATE users SET tecnico_nombre = 'Pedro Pascal' WHERE email = 'pedro.pascal@cerebro.com'"))
        db.commit()

        # Step D: Update Activities to match new Capitalized User Name
        print("Step 4: Capitalize activities 'Pedro pascal' -> 'Pedro Pascal'...")
        db.execute(text("UPDATE activities SET tecnico_nombre = 'Pedro Pascal' WHERE tecnico_nombre = 'Pedro pascal'"))
        db.commit()
        
        print("--- SUCCESS ---")
        
    except Exception as e:
        print(f"FAIL: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    consolidate_raw()
