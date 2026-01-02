import requests

urls = [
    "http://127.0.0.1:8001/static/app.js",
    "http://127.0.0.1:8001/"
]
for url in urls:
    print(f"--- {url} ---")
    try:
        resp = requests.get(url)
        print(f"Status: {resp.status_code}")
        print(f"Headers: {resp.headers}")
        print(f"Content Preview: {resp.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
