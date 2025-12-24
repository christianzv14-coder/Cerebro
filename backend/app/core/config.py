import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Cerebro Patio App"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super_secret_key_change_me_in_prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/cerebro_db")

    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS_JSON: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "")
    GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "")

    class Config:
        case_sensitive = True

settings = Settings()
