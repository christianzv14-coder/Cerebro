from sqlalchemy import create_engine, text
import sys
import os

# Add the current directory to sys.path so we can import app
sys.path.append(os.getcwd())

from app.core.security import get_password_hash
from app.core.config import settings

def fix_user():
    # Use the same DB URL as the app
    engine = create_engine(settings.FINANCE_DATABASE_URL)
    
    email = "christian.zv@cerebro.com"
    password = "123456"
    hashed_pwd = get_password_hash(password)
    
    with engine.connect() as conn:
        # Check if user exists
        result = conn.execute(text("SELECT email FROM users WHERE email = :email"), {"email": email}).fetchone()
        
        if result:
            print(f"User {email} exists. Updating password...")
            conn.execute(
                text("UPDATE users SET hashed_password = :hp, is_active = 1 WHERE email = :email"),
                {"hp": hashed_pwd, "email": email}
            )
        else:
            print(f"User {email} not found. Creating...")
            conn.execute(
                text("INSERT INTO users (email, hashed_password, full_name, role, is_active) VALUES (:email, :hp, :fn, :role, :ia)"),
                {"email": email, "hp": hashed_pwd, "fn": "Christian ZV", "role": "admin", "ia": 1}
            )
        conn.commit()
    print("User fixed successfully.")

if __name__ == "__main__":
    fix_user()
