
from sqlalchemy import create_engine, text
from app.core.config import settings
import os

# Ensure we use the remote URL if locally setting invalid? 
# Assuming settings.DATABASE_URL is correct for the environment this runs in (shell context of user seems to map to remote or local? 
# The user's info says "The user has 1 active workspaces...".
# I'm running python on the user's machine?
# `debug_remote_email.py` used `requests` to talk to the REMOTE server.
# `check_active_techs.py` imports `app.core.config` and connects to DB.
# Does the user's local `.env` point to Railway DB?
# `admin.py` (viewed earlier) had `SMTP_...` vars.
# If I am running on User's Local Windows, does it have access to Railway PG directly?
# The `debug_remote_email.py` works via HTTP API.
# The `check_active_techs.py` attempts to connect to DB directly via SQLAlchemy.
# **CRITICAL**: If the user's local machine cannot connect to Railway PG directly (firewall/allowed IPs), `check_active_techs.py` checks LOCAL DB (or fails).
# The user's local `Cerebro` folder likely has a local `.env` or defaults.
# If `debug_remote_email.py` worked, it's because it hits the API.
# If `check_active_techs.py` gave `[]`, maybe it checked the LOCAL empty DB?
# The USER is testing against the REMOTE server (App points to Remote).
# **I MUST CHECK THE REMOTE STATUS VIA API**, NOT VIA LOCAL SCRIPT connecting to DB (unless I'm sure local env points to remote).

# `debug_remote_email.py` uses `requests.get/post` to `https://cerebro-patio-production.up.railway.app`.
# THIS IS THE WAY.
# My `check_active_techs.py` might have been checking the WRONG DATABASE (Local).
# That explains why it was empty if I only deployed changes but the data is on Remote!

# I will modify `debug_remote_email.py` to add a "status check" via API, or use an existing API endpoint.
# `GET /activities/dates` returns dates.
# `GET /signatures/status` returns status for *current user* (I need token).
# `GET /admin/debug_full_system`? No.
# I need an endpoint that lists ALL activities or stats.
# `POST /admin/upload_excel` returns stats.
# Is there a `GET /admin/status`? No.
# But `debug_remote_email.py` already logs in as Admin? Or User?
# `debug_remote_email.py` logs in as `christianzv14@gmail.com`.
# I should call `GET /activities/dates` using the token in `debug_remote_email.py`.
# If `dates` is empty, then Remote DB is empty.

# I will modify `debug_remote_email.py` to check `GET /activities/dates`.

import requests

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"

def check_remote():
    print(f"--- CHECKING REMOTE DATA ({BASE_URL}) ---")
    
    # 1. Login
    login_data = {"username": "juan.perez@cerebro.com", "password": "123456"}
    resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if resp.status_code != 200:
        print(f"LOGIN FAILED: {resp.status_code} - {resp.text}")
        return
    token = resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("-> Login OK.")

    # 2. Check Dates (All available dates for user)
    resp_dates = requests.get(f"{BASE_URL}/activities/dates", headers=headers)
    dates = resp_dates.json()
    print(f"-> AVAILABLE DATES (For Juan): {dates}")
    
    # 3. Check Signature Status (For Today, or Last Date)
    if dates:
        # Check today
        from datetime import date
        today = str(date.today())
        resp_sig = requests.get(f"{BASE_URL}/signatures/status?fecha={today}", headers=headers)
        print(f"-> SIGNATURE STATUS (Today {today}): {resp_sig.json()}")
        
        # Check Last Date in list
        last_date = dates[0]
        resp_sig_last = requests.get(f"{BASE_URL}/signatures/status?fecha={last_date}", headers=headers)
        print(f"-> SIGNATURE STATUS (Last Plan {last_date}): {resp_sig_last.json()}")
    else:
        print("-> NO ACTIVITIES FOUND (Empty Plan).")

if __name__ == "__main__":
    check_remote()
