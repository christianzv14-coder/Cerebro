import requests
import json
import base64
import os
from dotenv import load_dotenv

# Load .env from backend folder
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, ".env"))

BASE_URL = "http://127.0.0.1:8000/api/v1"

def simulate():
    print("--- SIMULACIÓN DE FIRMA (BASE64) ---")
    
    # 1. Login
    login_data = {"username": "juan.perez@cerebro.com", "password": "123456"}
    print(f"Iniciando sesión como {login_data['username']}...")
    r = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if r.status_code != 200:
        print(f"Error login: {r.text}")
        return
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print("Login exitoso.")

    # 2. Upload Signature
    dummy_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    print("\nSubiendo firma en formato JSON Base64...")
    payload = {"image_base64": dummy_b64}
    r = requests.post(f"{BASE_URL}/signatures/", headers=headers, json=payload)
    
    print(f"Respuesta Servidor: {r.status_code} - {r.text}")
    if r.status_code == 200:
        print("\n✅ ¡ÉXITO! La firma fue procesada.")
    else:
        print("\n❌ FALLÓ la subida.")

if __name__ == "__main__":
    simulate()
