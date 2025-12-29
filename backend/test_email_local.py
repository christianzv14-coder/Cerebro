
import os
import sys
import pandas as pd
import socket
from dotenv import load_dotenv

# Load env vars from .env file
load_dotenv()

# Add backend to path to allow imports
sys.path.append(os.getcwd())

try:
    from app.services.email_service import send_plan_summary
except ImportError:
    # Try alternate path if running from parent
    sys.path.append(os.path.join(os.getcwd(), 'backend'))
    from app.services.email_service import send_plan_summary

def test_email_configuration():
    print("--- TESTING EMAIL CONFIGURATION ---")
    
    user = os.getenv("SMTP_USER", "NOT_SET")
    to = os.getenv("SMTP_TO", "NOT_SET")
    password = os.getenv("SMTP_PASS", "NOT_SET")
    
    print(f"SMTP_USER: {user}")
    print(f"SMTP_TO: {to}")
    print(f"SMTP_PASS: {'******' if password != 'NOT_SET' else 'NOT_SET'}")
    
    # Mock Data
    stats = {"processed": 10, "created": 5, "updated": 5}
    df = pd.DataFrame({
        "tecnico_nombre": ["Tech A", "Tech B", "Tech A"],
        "comuna": ["Comuna 1", "Comuna 2", "Comuna 1"]
    })
    
    # Debug: Check network connectivity
    print("\n--- NETWORK TEST ---")
    try:
        ip = socket.gethostbyname("smtp.gmail.com")
        print(f"DNS Resolution (smtp.gmail.com): Success ({ip})")
        
        # Test Port 465
        print("Testing Port 465...")
        try:
            sock = socket.create_connection(("smtp.gmail.com", 465), timeout=5)
            print("Port 465: Open")
            sock.close()
        except Exception as e:
            print(f"Port 465: Closed/Blocked ({e})")

        # Test Port 587
        print("Testing Port 587...")
        try:
            sock = socket.create_connection(("smtp.gmail.com", 587), timeout=5)
            print("Port 587: Open")
            sock.close()
        except Exception as e:
            print(f"Port 587: Closed/Blocked ({e})")
            
    except Exception as e:
        print(f"DNS Resolution Failed: {e}")

    print("\n--- SENDING EMAIL ---")
    try:
        send_plan_summary(stats, df)
        print("Email sent attempt finished successfully.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_email_configuration()
