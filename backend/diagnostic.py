import os
import io
from datetime import date
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.models import User, Activity, ActivityState, DaySignature, FailureReason
from app.services.sheets_service import sync_signature_to_sheet

def run_diagnostic():
    db = SessionLocal()
    try:
        print("--- Diagnostic Start ---")
        
        # 1. Check User
        user = db.query(User).filter(User.email == "juan.perez@cerebro.com").first()
        if not user:
            print("ERROR: User 'juan.perez@cerebro.com' not found.")
            return
        print(f"User found: {user.tecnico_nombre}")

        # 2. Check Activity
        act = db.query(Activity).filter(Activity.tecnico_nombre == user.tecnico_nombre).first()
        if not act:
            print("ERROR: No activities found for this user.")
        else:
            print(f"Activity found: {act.ticket_id} | State: {act.estado}")

        # 3. Simulate Signature Save Logic
        today = date.today()
        # Clean up existing for test
        db.query(DaySignature).filter(DaySignature.tecnico_nombre == user.tecnico_nombre, DaySignature.fecha == today).delete()
        db.commit()
        
        print(f"Simulating signature save for {user.tecnico_nombre} on {today}...")
        mock_path = "uploads/signatures/test_sig.png"
        os.makedirs(os.path.dirname(mock_path), exist_ok=True)
        with open(mock_path, "wb") as f:
            f.write(b"mock_png_data")
            
        new_sig = DaySignature(
            tecnico_nombre=user.tecnico_nombre,
            fecha=today,
            signature_ref=mock_path
        )
        db.add(new_sig)
        db.commit()
        db.refresh(new_sig)
        print(f"Signature record created in DB. ID: {new_sig.id}")

        # 4. Test Sheets Sync
        print("Testing Google Sheets sync...")
        try:
            sync_signature_to_sheet(new_sig)
            print("SUCCESS: sync_signature_to_sheet finished without raising.")
        except Exception as e:
            print(f"ERROR during Sheets sync: {e}")

        # 5. Verify Idempotency check
        existing = db.query(DaySignature).filter(
            DaySignature.tecnico_nombre == user.tecnico_nombre,
            DaySignature.fecha == today
        ).first()
        if existing:
            print(f"VERIFIED: getSignatureStatus logic would find this signature (ID: {existing.id})")
        else:
            print("ERROR: getSignatureStatus logic failed to find the signature just created.")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
    finally:
        db.close()
        print("--- Diagnostic End ---")

if __name__ == "__main__":
    run_diagnostic()
