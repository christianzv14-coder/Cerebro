from datetime import datetime

# Tabla de Puntos (Keyword -> Points)
# Orden: Buscar coincidencias más largas primero o específicas para evitar falsos positivos
# (Ej: "CABLE CAMARA" vs "CAMARA").
# Se usará búsqueda case-insensitive.

POINTS_TABLE = [
    # --- INSTALACION ---
    # Sensores / Alta prioridad
    ("SENSOR DE RETROCESO ADICIONAL", 30),
    ("SENSOR DE RETROCESO", 50), # Check full match vs partial
    ("SENSOR JCY450", 30),
    ("SENSOR DE PUERTA", 15), # Standard
    ("SENSOR PTA ADICIONAL", 10),
    ("SENSOR PTA", 13), # "SENSOR PTA" (13) vs "SENSOR PTA ADICIONAL" (10) -> Order matters!
    
    # Camaras / MDVR
    ("MDVR ADICIONAL", 10),
    ("MDVR", 25),
    ("CAMARA ADAS", 15),
    ("ADAS", 15), # Loose match for ADAS
    ("CAMARA DMS", 15),
    ("DMS", 15), # Loose match for DMS
    ("CAMARA AUXILIAR", 10),
    ("V4", 10), # Mapped as CAMARA AUXILIAR
    ("CAMARA BOL", 15),
    ("CAMARA DASHCAM", 15),
    
    # Cables
    ("CABLE SENSOR DE RETROCESO ADICIONAL", 3),
    ("CABLE SENSOR DE RETROCESO", 5),
    ("CABLE CAMARA ADAS", 3),
    ("CABLE CAMARA DMS", 3),
    ("CABLE CAMARA BOL", 3),
    ("CABLE CAMARA DASHCAM", 3),
    ("CABLE CAMARA", 3),
    ("CABLE IBUTTON", 3),
    ("CABLE BUZZER", 3),
    ("CABLE SONDA", 3), # "CABLE SONDA" matches before "SONDA"

    # Sondas
    ("SONDA TEMPERATURA ADICIONAL", 5),
    ("SONDA TEMPERATURA", 15),
    
    # Otros Accesorios
    ("BOTON TABLERO", 9),
    ("BOTON PANICO", 8),
    ("CORTA CORRIENTE", 10),
    ("IBUTTON", 12),
    ("BUZZER", 5),
    ("TAG", 10),
    
    # --- REVISION ---
    # Revisión items usually start with "REVISION" or "Revision" in the item name provided
    ("REVISION SONDA TEMPERATURA", 10),
    ("REVISION CAMARA ADAS", 9), # Specific before general
    ("REVISION CAMARA DMS", 9),
    ("REVISION CAMARA", 10),
    ("REVISION MDVR", 15),
    ("REVISION CORTA CORRIENTE", 8),
    ("REVISION IBUTTON", 8),
    ("REVISION BUZZER", 8),
    ("REVISION TAG", 8),
    ("REVISION BOTON PANICO", 8),
    ("Revision ADAS", 9),
    ("Revision DMS", 9),
    ("Revision JC450", 14),
    ("Revision DASHCAM", 14),
    ("Revision SENSOR DE RETROCESO", 50),
]

def calculate_base_points(accesorios_str, tipo_trabajo=""):
    """
    Parses the accessories string (comma separated) and sums points.
    If tipo_trabajo is 'SOPORTE' or 'REVISION', tries to match 'REVISION [Item]' first.
    Returns: (total_points, list_of_items_found)
    """
    if not accesorios_str:
        return 0, []
    
    items_raw = [x.strip() for x in accesorios_str.split(',')]
    total_points = 0
    items_found = []
    
    # Analyze Work Type
    is_review_mode = False
    if tipo_trabajo:
        tt_clean = tipo_trabajo.strip().upper()
        if "SOPORTE" in tt_clean or "REVISION" in tt_clean or "MANTENCION" in tt_clean:
            is_review_mode = True

    for item in items_raw:
        item_upper = item.upper()
        best_match = None
        best_points = 0
        
        # If in Review/Support mode, try finding "REVISION [Item]" match first
        match_found_as_review = False
        if is_review_mode:
            # Try to force a "REVISION " prefix match
            # We look for keys in table that are "REVISION + item"
            # But the item string might not match exactly.
            # Strategy: Iterate table, if key starts with REVISION, check if rest of key matches item
            
            for key, points in POINTS_TABLE:
                if not key.startswith("REVISION"): continue
                
                # key is e.g. "REVISION MDVR"
                # item is "MDVR"
                # Does "REVISION MDVR" contain "MDVR"? Yes.
                # But we want to match the ITEM against the KEY suffix.
                
                # Simpler: If the ITEM name is found in the KEY (which is a known REVISION key)
                # usage: item="MDVR", key="REVISION MDVR". 
                # check: if "MDVR" in "REVISION MDVR"? YES.
                
                # Careful: item="CABLE" vs key="REVISION CABLE..."
                
                if item_upper in key.upper(): 
                    # We found a REVISION key that matches our item.
                    best_match = key
                    best_points = points
                    match_found_as_review = True
                    break # Stop looking, we found the specific revision price
        
        if match_found_as_review:
             total_points += best_points
             items_found.append(f"{best_match}({best_points})")
             continue

        # Standard Match (Iterate mapping to find match)
        # Used if:
        # 1. Not in review mode (Standard Installation)
        # 2. In review mode, but no specific "REVISION X" price exists (Fallback to standard? or 0?)
        #    Usually fallback to standard is risky (gives full price).
        #    User said: "Soporte es lo mismo que revisión".
        #    If no revision price, maybe it defaults to a low generic?
        #    Let's stick to standard behavior for now if no revision specific found, 
        #    BUT usually we should have defined all.
        
        for key, points in POINTS_TABLE:
            # Skip REVISION keys if we are in Installation mode (unless item explicitly says REVISION)
            if not is_review_mode and key.startswith("REVISION") and "REVISION" not in item_upper:
                continue

            if key.upper() in item_upper:
                best_match = key
                best_points = points
                break 
        
        if best_match:
            total_points += best_points
            items_found.append(f"{best_match}({best_points})")
        else:
            items_found.append(f"{item}(0?)")
            
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
