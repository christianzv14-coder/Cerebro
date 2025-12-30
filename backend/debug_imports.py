import sys
import os

# Mimic the Dockerfile structure
sys.path.append(os.getcwd())

print("Attempting to import app.main...")
try:
    from app import main
    print("SUCCESS: app.main imported.")
except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()

print("Attempting to import app.routers.admin...")
try:
    from app.routers import admin
    print("SUCCESS: app.routers.admin imported.")
except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
