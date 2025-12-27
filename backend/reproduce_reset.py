import pandas as pd
from datetime import date
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Activity, ActivityState, User, DaySignature, Role
from app.services.excel_service import process_excel_upload
from io import BytesIO

def reproduce():
    db = SessionLocal()
    try:
        # 1. Setup Data
        tech_name = "Pedro Test"
        today = date.today()
        
        # Ensure user exists
        user = db.query(User).filter(User.tecnico_nombre == tech_name).first()
        if not user:
            user = User(email="pedro@test.com", tecnico_nombre=tech_name, hashed_password="pw", role=Role.TECH)
            db.add(user)
            db.commit()
            
        print(f"User: {user.tecnico_nombre}")

        # Create "Old" Activity (CONFIRMED CLOSED)
        old_act = Activity(
            ticket_id="OLD-123",
            fecha=today,
            tecnico_nombre=tech_name,
            estado=ActivityState.EXITOSO,
            cliente="Old Client"
        )
        db.add(old_act)
        
        # Create "Old" Signature
        old_sig = DaySignature(
            tecnico_nombre=tech_name,
            fecha=today,
            signature_ref="path/to/sig"
        )
        db.add(old_sig)
        db.commit()
        
        print("\n[BEFORE UPLOAD]")
        print(f"Activities: {db.query(Activity).filter(Activity.tecnico_nombre == tech_name, Activity.fecha == today).count()}")
        print(f"Signatures: {db.query(DaySignature).filter(DaySignature.tecnico_nombre == tech_name, DaySignature.fecha == today).count()}")

        # 2. Simulate Upload
        # Create a dummy Excel file
        data = {
            'fecha': [today],
            'ticket_id': ['NEW-456'],
            'tecnico_nombre': [tech_name], # Exact match
            'patente': ['AB1234'],
            'cliente': ['New Client'],
            'direccion': ['New Address'],
            'tipo_trabajo': ['Install']
            # Missing optional fields handled by service
        }
        df = pd.DataFrame(data)
        
        # Process
        # We need to mock the file object
        # excel_service takes 'file' which it reads with pd.read_excel
        # We can pass a BytesIO of the saved excel
        
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        
        print("\n>>> Processing Upload...")
        process_excel_upload(excel_buffer, db)
        
        # 3. Verify
        print("\n[AFTER UPLOAD]")
        activities = db.query(Activity).filter(Activity.tecnico_nombre == tech_name, Activity.fecha == today).all()
        signatures = db.query(DaySignature).filter(DaySignature.tecnico_nombre == tech_name, DaySignature.fecha == today).all()
        
        print(f"Activities Count: {len(activities)}")
        for a in activities:
            print(f"  - {a.ticket_id} ({a.estado})")
            
        print(f"Signatures Count: {len(signatures)}")
        
        if len(activities) == 1 and activities[0].ticket_id == 'NEW-456':
            print("SUCCESS: Old activities deleted.")
        else:
            print("FAILURE: Old activities persist.")
            
        if len(signatures) == 0:
            print("SUCCESS: Signature deleted.")
        else:
            print("FAILURE: Signature persists.")

    finally:
        # Cleanup
        db.query(Activity).filter(Activity.tecnico_nombre == tech_name).delete()
        db.query(DaySignature).filter(DaySignature.tecnico_nombre == tech_name).delete()
        db.commit()
        db.close()

if __name__ == "__main__":
    reproduce()
