import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from app.core.config import settings

# Manual override for the Sheet ID provided by the user
SHEET_ID = "19eXI3AV-S5uzXfwxC9HoGa6FExZ4ZlvmCvK79fbwMts"

def get_client():
    creds_path = "c:/Users/chzam/OneDrive/Desktop/cerebro-patio/Cerebro/backend/actividades-diarias-482221-75ab65299328.json"
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    return gspread.authorize(creds)

def init_sheet():
    client = get_client()
    if not client: return
    
    print(f"Connecting to sheet: {SHEET_ID}...")
    try:
        sheet = client.open_by_key(SHEET_ID)
    except Exception as e:
        print(f"ERROR: Could not open sheet. Make sure the service account email has access (Editor). Error: {e}")
        return

    # 1. Setup Config
    print("Setting up 'Config' tab...")
    try:
        ws_config = sheet.worksheet("Config")
        sheet.del_worksheet(ws_config)
    except: pass
    ws_config = sheet.add_worksheet(title="Config", rows=10, cols=2)
    ws_config.append_row(["Key", "Value"])
    ws_config.append_rows([
        ["Nombre", "Carlos"],
        ["Presupuesto", "3000"]
    ])

    # 2. Setup Presupuesto
    print("Setting up 'Presupuesto' tab...")
    try:
        ws_budget = sheet.worksheet("Presupuesto")
        sheet.del_worksheet(ws_budget)
    except: pass
    ws_budget = sheet.add_worksheet(title="Presupuesto", rows=100, cols=3)
    ws_budget.append_row(["Sección", "Categoría", "Presupuesto"])
    
    hierarchical_data = [
        ["GASTOS FIJOS", "Moni", "0"],
        ["GASTOS FIJOS", "Pago celular", "20"],
        ["GASTOS FIJOS", "Barberia", "30"],
        ["GASTOS FIJOS", "Credito CAE", "50"],
        ["GASTOS FIJOS", "Hogar de Niños", "10"],
        ["GASTOS FIJOS", "Credito Hipotecario", "800"],
        ["GASTOS FIJOS", "Classpass", "40"],
        ["GASTOS FIJOS", "Arriendo", "1000"],
        ["GASTOS FIJOS", "Gastos comunes", "150"],
        ["GASTOS FIJOS", "Luz", "40"],
        ["GASTOS FIJOS", "Agua", "20"],
        ["GASTOS FIJOS", "Agua caliente", "15"],
        ["GASTOS FIJOS", "Internet", "30"],
        ["GASTOS FIJOS", "Francesca", "0"],
        ["COMISIONES - SEGUROS", "Comision tarjeta santander", "10"],
        ["COMISIONES - SEGUROS", "Seguro Proteccion Banco Chile", "5"],
        ["COMISIONES - SEGUROS", "Comision Tarjeta banco chile dias", "5"],
        ["COMISIONES - SEGUROS", "Seguro Autmotriz", "50"],
        ["COMISIONES - SEGUROS", "Seguro de vida", "20"],
        ["TRANSPORTE", "Vencina", "100"],
        ["TRANSPORTE", "Uber/Cabify", "50"],
        ["TRANSPORTE", "Bip", "30"],
        ["TRANSPORTE", "Tag", "40"],
        ["STREAM/APP", "Gmail", "2"],
        ["STREAM/APP", "One drive", "2"],
        ["STREAM/APP", "Uber eats", "0"],
        ["STREAM/APP", "Spotify", "10"],
        ["STREAM/APP", "Disney +", "7"],
        ["STREAM/APP", "Netflix", "12"],
        ["STREAM/APP", "TNT", "10"],
        ["STREAM/APP", "Max", "10"],
        ["STREAM/APP", "ChatGPT", "20"],
        ["COMIDAS", "Bajones varios", "50"],
        ["COMIDAS", "Uber Comidas", "100"],
        ["COMIDAS", "Invitación Mami", "60"],
        ["COMIDAS", "Supermercado", "300"],
        ["VICIOS", "Cervezas", "40"],
        ["VICIOS", "Weed", "40"],
        ["VICIOS", "Pub", "60"],
        ["VICIOS", "Disco", "50"],
        ["VICIOS", "Tabaco", "20"],
        ["OTROS", "Estadio", "30"],
        ["OTROS", "Futbol", "20"],
        ["OTROS", "Padel/Karting", "40"],
        ["OTROS", "Remedios", "30"],
        ["OTROS", "Balu-Gala", "50"],
        ["OTROS", "Improvisado", "100"]
    ]
    ws_budget.append_rows(hierarchical_data)

    # 3. Setup Gastos
    print("Setting up 'Gastos' tab...")
    try:
        ws_gastos = sheet.worksheet("Gastos")
        sheet.del_worksheet(ws_gastos)
    except: pass
    ws_gastos = sheet.add_worksheet(title="Gastos", rows=1000, cols=7)
    ws_gastos.append_row(["Fecha", "Concepto", "Sección", "Categoría", "Monto", "Usuario", "Imagen URL"])
    
    from datetime import date
    today = str(date.today())
    ws_gastos.append_rows([
        [today, "Supermercado Lider", "COMIDAS", "Supermercado", "45", "Carlos", ""],
        [today, "Carga Bip", "TRANSPORTE", "Bip", "10", "Carlos", ""],
        [today, "Spotify Mes", "STREAM/APP", "Spotify", "10", "Carlos", ""]
    ])

    print("\n✅ Sheet initialized successfully!")
    print("Refresh your app to see the data.")

if __name__ == "__main__":
    init_sheet()
