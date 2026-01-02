import requests
import json

url = "http://localhost:8000/api/v1/expenses/"
data = {
    "amount": 123,
    "concept": "Diagnostic Test",
    "category": "OTROS",
    "section": "OTROS"
}

try:
    response = requests.post(url, data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"FAILED to connect: {e}")
