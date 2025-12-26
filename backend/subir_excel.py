import requests
import sys
import os

# Configuración
BASE_URL = "http://127.0.0.1:8000/api/v1"
ADMIN_EMAIL = "admin@cerebro.com"
ADMIN_PASS = "123456"

def subir_archivo(ruta_excel):
    if not os.path.exists(ruta_excel):
        print(f"Error: No se encuentra el archivo '{ruta_excel}'")
        return

    print(f"--- Iniciando Carga de Planificación ---")
    
    # 1. Obtener Token
    print("1. Autenticando como Admin...")
    try:
        login_res = requests.post(f"{BASE_URL}/auth/login", data={
            "username": ADMIN_EMAIL,
            "password": ADMIN_PASS
        })
        login_res.raise_for_status()
        token = login_res.json()["access_token"]
        print("   -> Autenticación Exitosa.")
    except Exception as e:
        print(f"   -> ERROR de Autenticación: {e}")
        return

    # 2. Subir Archivo
    print(f"2. Subiendo archivo '{ruta_excel}'...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with open(ruta_excel, "rb") as f:
            files = {"file": (os.path.basename(ruta_excel), f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            upload_res = requests.post(f"{BASE_URL}/admin/upload_excel", headers=headers, files=files)
            
        upload_res.raise_for_status()
        print("\nCARGA EXITOSA!")
        print(f"Resumen: {upload_res.json()['stats']}")
        print("\nLas tareas ya deberían aparecer en la App y en el Google Sheet.")
        
    except Exception as e:
        print(f"   -> ERROR al subir archivo: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   -> Detalle: {e.response.text}")

if __name__ == "__main__":
    archivo = "backend/plantilla_planificacion_v2.xlsx"
    if len(sys.argv) > 1:
        archivo = sys.argv[1]
    
    subir_archivo(archivo)
