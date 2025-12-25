from sqlalchemy import text
from app.database import engine, Base
from app.models.models import User, Activity, DaySignature, FailureReason

print("Resetting Database (Forced)...")

with engine.connect() as connection:
    try:
        connection.execution_options(isolation_level="AUTOCOMMIT")
        print("Dropping 'users' table with CASCADE...")
        # Force drop users and anything pointing to it (like the old 'messages' table)
        connection.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        
        print("Dropping other app tables...")
        connection.execute(text("DROP TABLE IF EXISTS activities CASCADE"))
        connection.execute(text("DROP TABLE IF EXISTS day_signatures CASCADE"))
        connection.execute(text("DROP TABLE IF EXISTS failure_reasons CASCADE"))
        # Drop old tables if they exist and we want to clean up
        connection.execute(text("DROP TABLE IF EXISTS messages CASCADE"))
        
        print("Old tables dropped.")
    except Exception as e:
        print(f"Error during raw drop: {e}")

print("Creating new schema...")
try:
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")
except Exception as e:
    print(f"Error creating tables: {e}")
