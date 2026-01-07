import requests
import json
import time

BASE_URL = "https://pacific-determination-production.up.railway.app"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"
EXPENSES_URL = f"{BASE_URL}/api/v1/expenses/"

def verify_delete_flow():
    session = requests.Session()
    
    # 1. Login
    print(f"Logging in to {LOGIN_URL}...")
    try:
        resp = session.post(LOGIN_URL, data={"username": "christian.zv@cerebro.com", "password": "123456"})
    except Exception as e:
        print(f"Login connection failed: {e}")
        return

    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} - {resp.text}")
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful.")

    # 2. Create a test expense to delete
    print("Creating test expense...")
    expense_data = {
        "amount": 123,
        "concept": "TEST_DELETE_SCRIPT",
        "category": "General",
        "payment_method": "EFECTIVO",
        "section": "OTROS"
    }
    resp = session.post(EXPENSES_URL, data=expense_data, headers=headers) # Using data= for Form (if it's form) or json=
    # Check finance.py: create_expense uses Form(...). So data= is correct.
    
    if resp.status_code != 200:
        print(f"Create Failed: {resp.status_code} - {resp.text}")
        return
    
    expense_id = resp.json().get("id")
    print(f"Created expense ID: {expense_id}")

    # 3. Verify it exists in list
    print("Fetching list...")
    resp = session.get(EXPENSES_URL, headers=headers)
    expenses = resp.json()
    found = False
    for e in expenses:
        if e["id"] == expense_id:
            found = True
            break
    
    if not found:
        print("ERROR: Created expense not found in list!")
        return
    print("Expense confirmed in list.")

    # 4. DELETE IT
    print(f"Deleting expense ID {expense_id}...")
    delete_url = f"{EXPENSES_URL}{expense_id}"
    resp = session.delete(delete_url, headers=headers)
    
    print(f"DELETE Response Status: {resp.status_code}")
    print(f"DELETE Response Body: {resp.text}")

    if resp.status_code == 200:
        print("DELETE reported success.")
    else:
        print("DELETE reported FAILURE.")

    # 5. Verify gone
    print("Verifying it is gone...")
    resp = session.get(EXPENSES_URL, headers=headers)
    expenses = resp.json()
    found_after = any(e["id"] == expense_id for e in expenses)
    
    if found_after:
        print("CRITICAL FAIL: Expense still exists after delete!")
    else:
        print("SUCCESS: Expense successfully deleted.")

if __name__ == "__main__":
    verify_delete_flow()
