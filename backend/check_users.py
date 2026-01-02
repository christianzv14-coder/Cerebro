from app.database import SessionLocal
from app.models.models import User

db = SessionLocal()
users = db.query(User).all()
print(f"Total Users: {len(users)}")
for u in users:
    print(f"ID: {u.id}, Email: {u.email}, Name: {u.tecnico_nombre}, Role: {u.role}")
db.close()
