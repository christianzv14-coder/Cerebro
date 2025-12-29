
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models.models import User, Activity, Base

# Ensure tables exist (optional, mostly for local dev)
# Base.metadata.create_all(bind=engine)

db = SessionLocal()

print("--- USERS IN DB ---")
users = db.query(User).all()
for u in users:
    print(f"ID: {u.id} | Name: '{u.tecnico_nombre}' | Email: {u.email} | Role: {u.role}")

print("\n--- ACTIVITIES FOR TODAY (2025-12-29) AND 19th ---")
dates_to_check = [date(2025, 12, 29), date(2025, 12, 19)]
for d in dates_to_check:
    print(f"\nChecking date: {d}")
    acts = db.query(Activity).filter(Activity.fecha == d).all()
    if not acts:
        print("  No activities found.")
    for a in acts:
        print(f"  ID: {a.id} | Tech: '{a.tecnico_nombre}' | Ticket: {a.ticket_id}")

db.close()
