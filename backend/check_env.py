import os
from dotenv import load_dotenv
from app.core.config import settings

def check_env():
    print("--- ENV CHECK ---")
    load_dotenv()
    env_db = os.getenv("DATABASE_URL")
    settings_db = settings.DATABASE_URL
    print(f"OS ENV DATABASE_URL: {env_db}")
    print(f"SETTINGS DATABASE_URL: {settings_db}")
    print("--- ENV CHECK END ---")

if __name__ == "__main__":
    check_env()
