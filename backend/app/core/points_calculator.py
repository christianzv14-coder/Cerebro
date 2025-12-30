from datetime import datetime

# Tabla de Puntos (Keyword -> Points)
# Orden: Buscar coincidencias más largas primero o específicas para evitar falsos positivos
# (Ej: "CABLE CAMARA" vs "CAMARA").
# Se usará búsqueda case-insensitive.


# --- CONFIGURATION TABLES (From User Images) ---

# Table 1: Base Points by Task Type
TASK_BASE_SCORES = {
    "REINSTALACION": 10,
    "INSTALACION": 7,
    "RETIRO": 5,
    "REVISION": 3,
    # Fallbacks/Synonyms
    "MANTENCION": 3,
    "SOPORTE": 3,
    "DESINSTALACION": 5
}

# Table 2: Accessory Points
# Order matters for partial matches? We'll use exact match preference or careful ordering.
POINTS_TABLE = [
    # High Value / Complex
    ("PANEL SOLAR", 32),
    ("CABLE RIZZO", 25),
    ("MDVR", 25),
    ("JC450", 20),
    ("DASHCAM", 20),
    
    # Cameras & Sensors
    ("CAMARA DE FRIO", 15),
    ("CAIQUEN", 15),
    ("ADAS", 15),
    ("DMS", 15),
    ("CAMARA AUXILIAR", 13),
    ("IBUTTON", 10),
    ("GPS CANBUS", 10),
    ("CORTA CORRIENTE", 8),
    ("SONDA TEMPERATURA", 8),
    
    # GPS Unit
    ("GPS", 2), # Value updated per user feedback
    
    # Peripherals
    ("BOTON PISO", 6),
    ("SENSOR PTA", 6),
    ("JAMMER", 5),
    ("SEÑUELO", 5),
    ("BUZZER", 4),
    
    # Low Value / Cables / Additionals
    ("SONDA TEMPERATURA ADICIONAL", 3),
    ("SENSOR PTA ADICIONAL", 3),
    ("BOTON TABLERO", 2),
    
    # Cables (Not in image but likely needed to avoid 0 if present? defaulting to low)
    # Keeping legacy cable values for safety or removing if user implies ONLY table counts?
    # User said: "los accesorios son fijos". I will keep common cables low just in case.
    ("CABLE", 1), 
]

def get_task_base_score(tipo_trabajo: str) -> int:
    """
    Determines the base score for the activity type.
    """
    if not tipo_trabajo: 
        return 0
    
    tt_normalized = tipo_trabajo.strip().upper()
    
    # Direct lookup or substring match
    # "Instalacion GPS" contains "INSTALACION" -> 7
    
    best_score = 0
    # Priority: REINSTALACION > INSTALACION > RETIRO > REVISION
    # Because "Reinstalacion" contains "Instalacion", check it first!
    
    priority_order = ["REINSTALACION", "INSTALACION", "RETIRO", "DESINSTALACION", "REVISION", "MANTENCION", "SOPORTE"]
    
    for key in priority_order:
        if key in tt_normalized:
            return TASK_BASE_SCORES.get(key, 0)
            
    return 0

def calculate_base_points(accesorios_str, tipo_trabajo=""):
    """
    New Logic: 
    Total = Task_Base_Score + Sum(Accessories)
    """
    # 1. Calculate Task Base Score
    task_score = get_task_base_score(tipo_trabajo)
    
    items_found = []
    items_found.append(f"BASE ACTIVIDAD({task_score})")
    
    acc_points = 0
    
    # 2. Calculate Accessories Score
    if accesorios_str:
        items_raw = [x.strip() for x in accesorios_str.split(',')]
        
        for item in items_raw:
            if not item: continue
            
            item_upper = item.upper()
            match_name = None
            match_points = 0
            
            # Find best match in POINTS_TABLE
            for key, points in POINTS_TABLE:
                # Use strict substring match: key must be in item OR item must be in key?
                # Usually item in excel is "GPS", key is "GPS".
                # If Excel says "GPS Telemetria", and key is "GPS".
                
                # Check 1: Key inside Item (e.g. key="GPS" in item="GPS Nuevo")
                if key in item_upper:
                    match_name = key
                    match_points = points
                    break
                
                # Check 2: Item inside Key? (e.g. item="Solar" in key="PANEL SOLAR") - Riskier.
                
            if match_name:
                acc_points += match_points
                items_found.append(f"{match_name}({match_points})")
            else:
                items_found.append(f"{item}(0?)")
    
    total_points = task_score + acc_points
    return total_points, items_found


def calculate_final_score(row_data, tech_count):
    """
    row_data: dict with keys 'Accesorios', 'Region', 'Fecha Plan', 'Tipo Trabajo'
    tech_count: int, number of techs on this ticket
    
    Returns: dict with calculation details
    """
    accesorios = str(row_data.get('Accesorios', ''))
    region = str(row_data.get('Region', '')).upper()
    fecha_str = str(row_data.get('Fecha Plan', ''))
    tipo_trabajo = str(row_data.get('Tipo Trabajo', '') if row_data.get('Tipo Trabajo') else row_data.get('tipo_trabajo', ''))
    
    # 1. Base Points
    base_points, details = calculate_base_points(accesorios, tipo_trabajo)
    
    # 2. Multipliers
    mult_region_val = 1.0
    # Logic: "Fuera de región". Assuming "Metropolitana" is standard.
    # Note: Sometimes it's "Rm", "R. Metropolitana", "Region Metropolitana".
    # Safe check: if NOT contains "METROPOLITANA" and NOT "RM"?
    # Or just check if valid string exists and isn't RM.
    if region and "METROPOLITANA" not in region and "RM" not in region:
        mult_region_val = 1.30
        
    mult_weekend_val = 1.0
    is_weekend = False
    try:
        # Parse date. Formats can be tricky. "2025-01-01" or "01/01/2025".
        # sheets_service uses normalize_sheet_date to YYYY-MM-DD.
        if '-' in fecha_str:
            dt = datetime.strptime(fecha_str, "%Y-%m-%d")
            # weekday: 0=Mon, 5=Sat, 6=Sun
            if dt.weekday() >= 5:
                mult_weekend_val = 1.25
                is_weekend = True
    except:
        pass # Date parse fail -> No weekend multiplier
        
    # 3. Calculation
    # Do we multiply first or divide first? 
    # User: "Los puntos se reparten... Ahora viene la magia: los multiplicadores... se multiplican"
    # User Example: "Si la pega valse 100 puntos y fueron 2 tecnicos: Cada uno recibe 50... Si la pega tiene condiciones... se multiplican"
    # Order: (Base / Techs) * Multipliers ? Or (Base * Multipliers) / Techs?
    # User said: "Si una pega vale 100... Cada uno recibe 50... Si fuera de region +30%".
    # 50 * 1.3 = 65.
    # (100 * 1.3) / 2 = 65. Math is same.
    
    gross_points = base_points * mult_region_val * mult_weekend_val
    final_points = gross_points / max(1, tech_count)
    
    # Rounding? Let's keep 2 decimals.
    
    money = final_points * 570
    
    return {
        "base_points": base_points,
        "items": "; ".join(details),
        "mult_region": mult_region_val,
        "mult_weekend": mult_weekend_val,
        "tech_count": tech_count,
        "final_points": round(final_points, 2),
        "money": int(money)
    }
