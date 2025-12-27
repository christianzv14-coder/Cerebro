from app.database import SessionLocal
from app.models.models import User

def fix_user_casing():
    print("--- FIXING USER CASING ---")
    db = SessionLocal()
    try:
        # Find Pedro
        user = db.query(User).filter(User.email == "pedro.pascal@cerebro.com").first()
        if not user:
            print("User pedro.pascal@cerebro.com not found!")
            return

        print(f"Found User: {user.tecnico_nombre} (ID: {user.id})")
        
        # Update to Capitalized
        if user.tecnico_nombre != "Pedro Pascal":
            user.tecnico_nombre = "Pedro Pascal"
            db.commit()
            print(" -> UPDATED to 'Pedro Pascal'")
        else:
            print(" -> Already correct.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_user_casing()
