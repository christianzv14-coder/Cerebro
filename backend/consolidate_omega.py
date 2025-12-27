from sqlalchemy import text
from app.database import SessionLocal

def consolidate_omega():
    print("--- CONSOLIDATE OMEGA (ALL TABLES) ---")
    db = SessionLocal()
    try:
        # 1. Activities
        print("Moving Activities 'Pedro Pascal' -> 'Pedro pascal'...")
        db.execute(text("UPDATE activities SET tecnico_nombre = 'Pedro pascal' WHERE tecnico_nombre = 'Pedro Pascal'"))
        
        # 2. Signatures (The missing link!)
        print("Moving Signatures 'Pedro Pascal' -> 'Pedro pascal'...")
        db.execute(text("UPDATE day_signatures SET tecnico_nombre = 'Pedro pascal' WHERE tecnico_nombre = 'Pedro Pascal'"))
        
        db.commit() # Commit reassignment first
        
        # 3. Delete Duplicate User
        print("Deleting 'pedro@cerebro.com'...")
        db.execute(text("DELETE FROM users WHERE email = 'pedro@cerebro.com'"))
        db.commit()
        
        # 4. Rename Target User
        print("Renaming 'Pedro pascal' -> 'Pedro Pascal'...")
        db.execute(text("UPDATE users SET tecnico_nombre = 'Pedro Pascal' WHERE email = 'pedro.pascal@cerebro.com'"))
        db.commit()

        # 5. Rename Activities & Signatures back to Capitalized
        db.execute(text("UPDATE activities SET tecnico_nombre = 'Pedro Pascal' WHERE tecnico_nombre = 'Pedro pascal'"))
        db.execute(text("UPDATE day_signatures SET tecnico_nombre = 'Pedro Pascal' WHERE tecnico_nombre = 'Pedro pascal'"))
        db.commit()
        
        print("--- OMEGA SUCCESS ---")
        
    except Exception as e:
        print(f"FAIL: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    consolidate_omega()
