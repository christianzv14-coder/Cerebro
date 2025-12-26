from app.database import SessionLocal
from app.models.models import Activity, User

def fix():
    print("=== FIXING TASKS FOR PEDRO ===")
    db = SessionLocal()
    try:
        # 1. Get correct user name for Pedro
        pedro_user = db.query(User).filter(User.email.like("%pedro%")).first()
        if not pedro_user:
            print("ERROR: No matching user found for 'Pedro' (email check).")
            return
            
        real_name = pedro_user.tecnico_nombre
        print(f"Target User found: '{real_name}' (Email: {pedro_user.email})")

        # 2. Find mismatching activities (assigned to just "Pedro")
        mismatched = db.query(Activity).filter(Activity.tecnico_nombre == "Pedro").all()
        
        if not mismatched:
            print("No activities found specifically assigned to 'Pedro'.")
            # Check if there are ANY activities for the real user
            correct = db.query(Activity).filter(Activity.tecnico_nombre == real_name).all()
            if correct:
                print(f"Good news: Found {len(correct)} activities already correctly assigned to '{real_name}'.")
            else:
                print(f"Warning: No activities found for '{real_name}' either.")
        else:
            print(f"Found {len(mismatched)} activities assigned to 'Pedro'. Updating to '{real_name}'...")
            for a in mismatched:
                print(f" -> Updating Ticket {a.ticket_id}: '{a.tecnico_nombre}' => '{real_name}'")
                a.tecnico_nombre = real_name
            
            db.commit()
            print("Update complete!")

    except Exception as e:
        print(f"Error during fix: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix()
