
import sqlite3
import os
import sys
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# 1. Setup
load_dotenv('backend/.env')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
CREDS_JSON = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')

def wipe_db(db_path):
    if not os.path.exists(db_path):
        print(f"Skipping {db_path} (not found)")
        return
    
    print(f"\n--- WIPING {db_path} ---")
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in c.fetchall()]
        print(f"Found tables: {tables}")
        
        tables_to_wipe = ['expenses', 'commitments', 'activities', 'day_signatures', 'signatures']
        for table in tables_to_wipe:
            if table in tables:
                print(f"  - Wiping table: {table}")
                c.execute(f"DELETE FROM {table}")
        
        # Reset auto-increment
        if 'sqlite_sequence' in tables:
            for table in tables_to_wipe:
                if table in tables:
                    c.execute(f"UPDATE sqlite_sequence SET seq = 0 WHERE name = ?", (table,))
        
        conn.commit()
        conn.close()
        print(f"Successfully wiped {db_path}")
    except Exception as e:
        print(f"Error wiping {db_path}: {e}")

def wipe_sheets():
    if not GOOGLE_SHEET_ID or not CREDS_JSON:
        print("Skipping Sheets wipe (Missing ID or JSON in backend/.env)")
        return
    
    print(f"\n--- WIPING GOOGLE SHEET: {GOOGLE_SHEET_ID} ---")
    try:
        import base64
        creds_str = CREDS_JSON
        if not creds_str.strip().startswith('{'):
            try:
                creds_str = base64.b64decode(creds_str).decode('utf-8')
            except: pass
            
        creds_dict = json.loads(creds_str)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sh = client.open_by_key(GOOGLE_SHEET_ID)
        
        sheets_to_wipe = ['Gastos', 'Compromisos', 'Bitacora']
        for sheet_name in sheets_to_wipe:
            try:
                ws = sh.worksheet(sheet_name)
                print(f"  - Wiping sheet: {sheet_name} (keeping headers)")
                # A to Z, starting from row 2
                ws.batch_clear(["A2:Z5000"])
            except gspread.WorksheetNotFound:
                print(f"  - Sheet '{sheet_name}' not found, skipping.")
        
        print("Successfully wiped Google Sheets")
    except Exception as e:
        print(f"Error wiping Google Sheets: {e}")

if __name__ == "__main__":
    # Local Databases
    wipe_db('cerebro.db')
    wipe_db('backend/sql_app.db')
    
    # Remote Sheets
    wipe_sheets()
    
    print("\n--- DATA WIPE COMPLETE: FRESH START READY ---")
