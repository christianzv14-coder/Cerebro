
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8001/api/v1/expenses/categories/"

def test_categories():
    print("--- Testing Category Management ---")

    # 1. Create a Test Category
    print("\n1. creating 'TestCat' in 'TEST_SECTION'...")
    try:
        payload = {"section": "TEST_SECTION", "category": "TestCat", "budget": 100}
        res = requests.post(BASE_URL, json=payload)
        print(f"POST Status: {res.status_code}")
        print(f"POST Response: {res.text}")
        if res.status_code != 200:
            return
    except Exception as e:
        print(f"POST Failed: {e}")
        return

    time.sleep(2) # Give Sheets a moment

    # 2. Update the Category
    print("\n2. Updating 'TestCat' budget to 500...")
    try:
        payload = {"section": "TEST_SECTION", "category": "TestCat", "new_budget": 500}
        res = requests.patch(BASE_URL, json=payload)
        print(f"PATCH Status: {res.status_code}")
        print(f"PATCH Response: {res.text}")
    except Exception as e:
        print(f"PATCH Failed: {e}")

    time.sleep(2)

    # 3. Delete the Category
    print("\n3. Deleting 'TestCat'...")
    try:
        # requests.delete doesn't support json body in some older specs but FastAPI/Modern HTTP does.
        # However, standard practice often puts it in fetch body.
        payload = {"section": "TEST_SECTION", "category": "TestCat"}
        res = requests.delete(BASE_URL, json=payload)
        print(f"DELETE Status: {res.status_code}")
        print(f"DELETE Response: {res.text}")
    except Exception as e:
        print(f"DELETE Failed: {e}")

if __name__ == "__main__":
    test_categories()
