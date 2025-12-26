import requests
import time
import os
from datetime import date

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_full_flow():
    print("\n🚀 INICIANDO TEST DE SISTEMA COMPLETO...")
    
    # 1. Login
    print("\n1. Autenticando...")
    login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": "juan.perez@cerebro.com", "password": "123456"})
    if login_res.status_code != 200:
        print(f"❌ Error Login: {login_res.text}")
        return
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Autenticado correctamente.")

    # 2. Start Activity
    ticket = "TKT-001"
    print(f"\n2. Iniciando Tarea {ticket}...")
    start_res = requests.post(f"{BASE_URL}/activities/{ticket}/start", headers=headers, json={"timestamp": "2025-12-25T10:00:00"})
    print(f"   Status: {start_res.status_code}")
    
    # 3. Finish Activity
    print(f"\n3. Finalizando Tarea {ticket}...")
    finish_res = requests.post(
        f"{BASE_URL}/activities/{ticket}/finish", 
        headers=headers, 
        json={
            "timestamp": "2025-12-25T11:00:00",
            "resultado": "EXITOSO",
            "observacion": "Prueba automática del sistema"
        }
    )
    print(f"   Status: {finish_res.status_code}")

    # 4. Upload Signature (Base64)
    print("\n4. Enviando Firma (Base64 Mode)...")
    dummy_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==" # 1x1 Transparent PNG
    sign_res = requests.post(f"{BASE_URL}/signatures/", headers=headers, json={"image_base64": dummy_b64})
    print(f"   Status: {sign_res.status_code}")
    print(f"   Respuesta: {sign_res.text}")

    print("\n************************************************")
    if sign_res.status_code == 200 and finish_res.status_code == 200:
        print("✅ EL BACKEND FUNCIONA AL 100% ✅")
        print("Si el Google Sheet se actualizó, el problema está ÚNICAMENTE en la App Móvil.")
    else:
        print("❌ EL TEST FALLÓ. Revisa los códigos de error arriba.")
    print("************************************************\n")

if __name__ == "__main__":
    test_full_flow()
