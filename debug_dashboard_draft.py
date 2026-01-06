
import sys
import os
import json

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Manually load .env
try:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        print(f"Loading .env from {env_path}")
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value
    else:
        print(".env not found")
except Exception as e:
    print(f"Error loading .env: {e}")

try:
    from backend.app.services.sheets_service import get_dashboard_data
    
    print("Fetching dashboard data for 'Christian ZV'...")
    data = get_dashboard_data("Christian ZV")
    
    if data:
        print(json.dumps(data, indent=2, default=str))
    else:
        print("Result is None")

except ImportError as e:
    print(f"ImportError: {e}")
    # Try adding 'backend' to path if needed (though project root should suffice)
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
        from app.services.sheets_service import get_dashboard_data
        print("Fetching dashboard data for 'Christian ZV' (fallback import)...")
        data = get_dashboard_data("Christian ZV")
        print(json.dumps(data, indent=2, default=str))
    except Exception as e2:
        print(f"Fallback Error: {e2}")

except Exception as e:
    print(f"Error: {e}")
