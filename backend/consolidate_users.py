from app.database import SessionLocal
from app.models.models import User, Activity

def consolidate():
    print("--- CONSOLIDATING ACCOUNTS ---")
    db = SessionLocal()
    try:
        # 1. Identify valid and invalid users
        juan = db.query(User).filter(User.email == "juan.perez@cerebro.com").first()
        pedro_good_email = db.query(User).filter(User.email == "pedro.pascal@cerebro.com").first()
        pedro_bad_email = db.query(User).filter(User.email == "pedro@cerebro.com").first()

        # Check Juan
        if juan:
            print(f"[OK] Juan Perez exists ({juan.email})")
        else:
            print("[WARN] Juan Perez missing! Creating/Ignoring...")

        # 2. HANDLE CONFLICT & REASSIGN
        if pedro_bad_email:
            print(f"[ACTION] Found duplicate user: {pedro_bad_email.email}")
            
            # Step A: Rename Bad User to free up the 'Pedro Pascal' name slot
            # (We assume the FK cascades on update or we update activities manually)
            old_name = pedro_bad_email.tecnico_nombre
            temp_name = "Pedro_Temp_Delete"
            
            pedro_bad_email.tecnico_nombre = temp_name
            db.commit()
            print(f" -> Renamed old user to '{temp_name}'")
            
            # Update activities explicitly if FK doesn't cascade update
            activities = db.query(Activity).filter(Activity.tecnico_nombre == old_name).all()
            for a in activities:
                a.tecnico_nombre = temp_name
            db.commit()

        # 3. FIX 'pedro.pascal@cerebro.com' -> 'Pedro Pascal'
        if pedro_good_email:
            print(f"[ACTION] Renaming GOOD user: {pedro_good_email.email}")
            target_name = "Pedro Pascal"
            
            if pedro_good_email.tecnico_nombre != target_name:
                pedro_good_email.tecnico_nombre = target_name
                db.commit()
                print(f" -> RENAMED {pedro_good_email.email} to '{target_name}'")
            
            # 4. REASSIGN ACTIVITIES from Temp -> New Good User
            # Now we move the activities from 'Pedro_Temp_Delete' to 'Pedro Pascal'
            orphaned_activities = db.query(Activity).filter(Activity.tecnico_nombre == "Pedro_Temp_Delete").all()
            print(f" -> Reassigning {len(orphaned_activities)} activities to '{target_name}'...")
            for a in orphaned_activities:
                a.tecnico_nombre = target_name
            db.commit()
            
        # 5. NOW DELETE THE BAD USER (It has no activities now)
        if pedro_bad_email:
             print(f"[ACTION] Deleting empty bad user: {pedro_bad_email.email}")
             db.delete(pedro_bad_email)
             db.commit()
             print(" -> Deleted.")

        # 4. Verify Activities Linkage
        # Since activities link by 'tecnico_nombre', they should now map to this user.
        count_juan = db.query(Activity).filter(Activity.tecnico_nombre == "Juan Perez").count()
        count_pedro = db.query(Activity).filter(Activity.tecnico_nombre == "Pedro Pascal").count()
        
        print(f"\n[VERIFICATION]")
        print(f"Activities for 'Juan Perez': {count_juan}")
        print(f"Activities for 'Pedro Pascal': {count_pedro}")

    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    consolidate()
