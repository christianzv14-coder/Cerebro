from sqlalchemy import text
from app.database import SessionLocal
from app.core.security import get_password_hash
from app.models.models import User

def reset_pedro():
    print("--- RESETTING PEDRO ---")
    db = SessionLocal()
    try:
        # 1. DELETE EVERYTHING FOR PEDRO
        names = ['Pedro Pascal', 'Pedro pascal']
        emails = ['pedro.pascal@cerebro.com', 'pedro@cerebro.com']
        
        print("1. Cleaning old data...")
        for name in names:
            db.execute(text(f"DELETE FROM day_signatures WHERE tecnico_nombre = '{name}'"))
            db.execute(text(f"DELETE FROM activities WHERE tecnico_nombre = '{name}'"))
        
        for email in emails:
            db.execute(text(f"DELETE FROM users WHERE email = '{email}'"))
            
        db.commit()
        print("   -> Deleted old Pedros and their data.")

        # 2. CREATE FRESH PEDRO
        print("2. Creating NEW Pedro Pascal (pedro.pascal@cerebro.com)...")
        hashed_pwd = get_password_hash("123456")
        new_user = User(
            email="pedro.pascal@cerebro.com",
            hashed_password=hashed_pwd,
            tecnico_nombre="Pedro Pascal",
            role="TECH",
            is_active=True
        )
        db.add(new_user)
        db.commit()
        print(f"   -> Created User ID: {new_user.id}")

    except Exception as e:
        print(f"FAIL: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_pedro()
