
import os
from dotenv import load_dotenv

load_dotenv()

g_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
g_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")

print(f"GOOGLE_SERVICE_ACCOUNT_FILE: {g_file}")
print(f"GOOGLE_SHEETS_CREDENTIALS_JSON exists?: {bool(g_json)}")
if g_json:
    print(f"GOOGLE_SHEETS_CREDENTIALS_JSON length: {len(g_json)}")
    print(f"GOOGLE_SHEETS_CREDENTIALS_JSON starts with: {g_json[:10]}...")
