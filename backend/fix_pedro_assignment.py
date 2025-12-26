from app.database import SessionLocal
from app.models.models import Activity, User

def fix_pedro():
    db = SessionLocal()
    try:
        # Find activities assigned to "Pedro"
        activities = db.query(Activity).filter(Activity.tecnico_nombre == "Pedro").all()
        print(f"Found {len(activities)} activities assigned to 'Pedro'.")
        
        # Check if user "Pedro Pascal" exists
        user = db.query(User).filter(User.tecnico_nombre == "Pedro Pascal").first()
        if not user:
            print("User 'Pedro Pascal' not found.")
            return

        # Update them to "Pedro Pascal"
        for a in activities:
            a.tecnico_nombre = "Pedro Pascal"
        
        db.commit()
        print(f"Updated {len(activities)} activities to 'Pedro Pascal'.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_pedro()
