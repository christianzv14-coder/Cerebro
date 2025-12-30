
from sqlalchemy import create_engine, text
from app.core.config import settings

# Force autocommit execution options
engine = create_engine(settings.DATABASE_URL, execution_options={"isolation_level": "AUTOCOMMIT"})
NEW_EMAIL = "christianzv14@gmail.com"
TARGET_USERS = ["Juan Perez", "Pedro Pascal"]

with engine.connect() as conn:
    print(f"--- UPDATING EMAILS TO {NEW_EMAIL} (AUTOCOMMIT) ---")
    
    for name in TARGET_USERS:
        # Check if user exists
        try:
            res = conn.execute(text(f"SELECT id, email FROM users WHERE tecnico_nombre = '{name}'")).fetchone()
            if res:
                print(f"Updating {name} (Current: {res[1]})...")
                conn.execute(text(f"UPDATE users SET email = '{NEW_EMAIL}' WHERE tecnico_nombre = '{name}'"))
                print("✅ Updated.")
            else:
                print(f"⚠️ User {name} not found.")
        except Exception as e:
            print(f"Error on {name}: {e}")
            
    print("DONE.")
