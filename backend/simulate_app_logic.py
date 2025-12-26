import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def check_status():
    print("\n--- SIMULATING APP STARTUP ---")
    print(f"1. App connecting to: {BASE_URL}/api/v1/signatures/status")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/signatures/status", timeout=5)
        print(f"2. Response Code: {response.status_code}")
        print(f"3. Raw JSON: {response.text}")
        
        data = response.json()
        is_signed = data.get("is_signed", False)
        
        print("\n--- UI DECISION LOGIC ---")
        print(f"Server says is_signed = {is_signed}")
        
        if is_signed:
            print("RESULT: Button text SHOULD be -> 'FIRMAR JORNADA (Signed: true)'")
            print("RESULT: Button color SHOULD be -> GREEN")
        else:
            print("RESULT: Button text SHOULD be -> 'FIRMAR JORNADA (Signed: false)'")
            print("RESULT: Button color SHOULD be -> BLACK")
            
    except Exception as e:
        print(f"CRITICAL ERROR: Could not connect to backend. {e}")

if __name__ == "__main__":
    check_status()
