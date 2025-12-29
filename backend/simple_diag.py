
import requests
import json

BASE_URL = "https://cozy-smile-production.up.railway.app/api/v1"

def run():
    print("Hitting /admin/test_email...")
    try:
        res = requests.get(f"{BASE_URL}/admin/test_email", timeout=30)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            print("REPORT:")
            print(json.dumps(res.json(), indent=2))
        else:
            print(f"Error Body: {res.text}")
    except Exception as e:
        print(f"Request Failed: {e}")

if __name__ == "__main__":
    run()
