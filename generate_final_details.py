
import json
import pandas as pd
import os

def safe_float(x, default=0.0):
    try:
        return float(x)
    except:
        return default

def norm_city(x):
    return str(x).strip()

def load_data():
    path = "data"
    
    # Load Excel Files
    demanda = pd.read_excel(os.path.join(path, "demanda_ciudades.xlsx"))
    demanda["ciudad"] = demanda["ciudad"].apply(norm_city)
    demanda["vehiculos_1gps"] = demanda["vehiculos_1gps"].fillna(0).astype(float)
    demanda["vehiculos_2gps"] = demanda["vehiculos_2gps"].fillna(0).astype(float)
    
    pxq = pd.read_excel(os.path.join(path, "costos_externos.xlsx"))
    pxq["ciudad"] = pxq["ciudad"].apply(norm_city)
    pxq_map = dict(zip(pxq["ciudad"], pxq["pxq_externo"]))
    
    flete = pd.read_excel(os.path.join(path, "flete_ciudad.xlsx"))
    flete["ciudad"] = flete["ciudad"].apply(norm_city)
    flete_map = dict(zip(flete["ciudad"], flete["costo_flete"]))
    
    kits = pd.read_excel(os.path.join(path, "materiales.xlsx"))
    kits["tipo_kit"] = kits["tipo_kit"].astype(str)
    
    try:
        kit1 = safe_float(kits.loc[kits["tipo_kit"] == "1_GPS", "costo"].values[0], 0.0)
        kit2 = safe_float(kits.loc[kits["tipo_kit"] == "2_GPS", "costo"].values[0], 0.0)
    except:
        kit1 = 0.0
        kit2 = 0.0
        
    return demanda, pxq_map, flete_map, kit1, kit2

def generate_final_report():
    demanda, pxq_map, flete_map, kit1, kit2 = load_data()
    
    with open('outputs/vrp_result.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Filter External assignments per city
    city_external_gps = {}
    for entry in data.get('plan', []):
        if entry.get('type') == 'EXTERNAL':
            c = entry.get('city')
            count = entry.get('gps', 0)
            city_external_gps[c] = city_external_gps.get(c, 0) + count
            
    # --- 1. PXQ EXTERNADO ---
    pxq_rows = []
    for city, count in city_external_gps.items():
        unit_cost = pxq_map.get(city, 0.0)
        pxq_total = unit_cost * count
        
        # Flete logic for external (Usually applies if count > 0)
        # Assuming simple rule: If External exists, charge Flete.
        flete_val = flete_map.get(city, 0.0)
        
        total = pxq_total + flete_val
        
        pxq_rows.append({
            "Ciudad": city,
            "GPS Asignados (Ext)": count,
            "Costo Unitario (PxQ)": unit_cost,
            "Subtotal PxQ (UF)": pxq_total,
            "Costo Flete (UF)": flete_val,
            "Total Externo (UF)": total
        })
        
    # --- 2. ACCESORIOS (MATERIALS) ---
    # Applies to ALL cities (Internal + External) based on demand V1/V2
    # Because materials are consumed regardless of who installs (unless external includes materials? 
    # Usually external is PxQ "Sin Materiales" or "Con"? 
    # Logic in `costo_materiales_ciudad` implies we calculate materials for the City.
    # Logic in `costo_externo_uf` returns `total_externo_sin_materiales_uf`.
    # So Materials are separate and summed for the TOTAL Project.
    
    mat_rows = []
    # Identify all active cities in inputs (demanda)
    # Or just those with >0 GPS
    
    for idx, row in demanda.iterrows():
        c = row['ciudad']
        v1 = row['vehiculos_1gps']
        v2 = row['vehiculos_2gps']
        total_gps = v1 + 2 * v2
        
        if total_gps <= 0:
            continue
            
        cost_v1 = v1 * kit1
        cost_v2 = v2 * kit2
        total_mat = cost_v1 + cost_v2
        
        mat_rows.append({
            "Ciudad": c,
            "Vehiculos 1 GPS": v1,
            "Costo Kit 1 (UF)": kit1,
            "Subtotal Kit 1": cost_v1,
            "Vehiculos 2 GPS": v2,
            "Costo Kit 2 (UF)": kit2,
            "Subtotal Kit 2": cost_v2,
            "Total Materiales (UF)": total_mat
        })
        
    # --- OUTPUT ---
    out_path = "outputs/reporte_final_detalles.xlsx"
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        pd.DataFrame(pxq_rows).to_excel(writer, sheet_name="Detalle PxQ Externos", index=False)
        pd.DataFrame(mat_rows).to_excel(writer, sheet_name="Detalle Materiales", index=False)
        
    print(f"Final Details Report generated: {out_path}")

if __name__ == "__main__":
    generate_final_report()
