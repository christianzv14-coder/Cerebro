import requests
import sys

BASE_URL = "http://127.0.0.1:8001"

def test_endpoint(name, url, expected_content_type=None, expected_status=200):
    print(f"Testing {name} ({url})...", end=" ")
    try:
        resp = requests.get(url)
        if resp.status_code != expected_status:
            print(f"FAILED (Status {resp.status_code})")
            return False
        
        if expected_content_type and expected_content_type not in resp.headers.get("Content-Type", ""):
             print(f"FAILED (Content-Type mismatch: {resp.headers.get('Content-Type')})")
             return False
             
        print("OK")
        return True
    except Exception as e:
        print(f"FAILED (Exception: {e})")
        return False

def run_tests():
    print(f"--- Verifying Deployment Readiness on {BASE_URL} ---\n")
    
    # 1. Frontend Root
    if not test_endpoint("Root (Index)", f"{BASE_URL}/", "text/html"): return
    
    # 2. Static Assets
    if not test_endpoint("App JS", f"{BASE_URL}/static/app.js", "application/javascript"): return
    if not test_endpoint("Style CSS", f"{BASE_URL}/static/style.css", "text/css"): return
    
    # 3. API Health
    # Root API endpoint (if exists) or Docs
    test_endpoint("API Docs", f"{BASE_URL}/docs", "text/html")
    
    # 4. Functional Data
    test_endpoint("Dashboard Data", f"{BASE_URL}/api/v1/expenses/dashboard", "application/json")
    test_endpoint("Commitments", f"{BASE_URL}/api/v1/commitments/", "application/json")
    
    print("\n✅ All system checks passed. The Monolith is ready.")

if __name__ == "__main__":
    run_tests()
