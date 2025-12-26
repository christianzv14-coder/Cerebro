import os
import json
import re

def fix():
    print("=== FINAL FIX: CEREBRO PATIO ===")
    
    # 1. Look for the JSON file
    json_files = [f for f in os.listdir(".") if f.endswith(".json") and "actividades-diarias" in f]
    if not json_files:
        print("ERROR: No encontré el archivo JSON de Google Sheets en esta carpeta.")
        return
    
    target_json = json_files[0]
    print(f"Detectado archivo de credenciales: {target_json}")
    
    with open(target_json, "r") as f:
        creds_content = f.read().strip()
    
    # 2. Read .env
    if not os.path.exists(".env"):
        print("ERROR: No encontré el archivo .env")
        return
        
    with open(".env", "r") as f:
        env_lines = f.readlines()
    
    new_lines = []
    found = False
    for line in env_lines:
        if line.startswith("GOOGLE_SHEETS_CREDENTIALS_JSON="):
            # Replace exactly
            new_lines.append(f"GOOGLE_SHEETS_CREDENTIALS_JSON='{creds_content}'\n")
            found = True
        else:
            new_lines.append(line)
            
    if not found:
        new_lines.append(f"GOOGLE_SHEETS_CREDENTIALS_JSON='{creds_content}'\n")

    # 3. Write .env
    with open(".env", "w") as f:
        f.writelines(new_lines)
    
    print("\n¡ÉXITO! El archivo .env ha sido actualizado con el CONTENIDO del JSON.")
    print("Nota: Ya no importa si usas Neon o Local, el servidor ahora tiene las llaves para Google Sheets.")
    print("\nPRÓXIMOS PASOS:")
    print("1. Reinicia el servidor: python -m uvicorn app.main:app --reload --port 8000")
    print("2. Corre el simulador: ..\\venv\\Scripts\\python.exe simulate_signature.py")

if __name__ == "__main__":
    fix()
