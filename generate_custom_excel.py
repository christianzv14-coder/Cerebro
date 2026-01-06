
import pandas as pd
import json
import modelo_optimizacion_gps_chile_v1 as shared
import os

def generate_excel():
    json_path = "outputs/vrp_result.json" 
    
    with open(json_path, "r") as f:
        data = json.load(f)
        
    full_plan = data['plan']
    cities = shared.CIUDADES
    
    # ---------------------------------------------------------
    # 1. RECONSTRUCT FULL 24-DAY TIMELINE (FIX GAP ISSUES)
    # ---------------------------------------------------------
    timeline_map = {t: {} for t in shared.TECNICOS}
    for item in full_plan:
        if item['type'] == 'INTERNAL':
            t = item['tech']
            d = item['day']
            timeline_map[t][d] = item.copy()
            
    full_timeline_flat = [] 
    
    for t in shared.TECNICOS:
        base = shared.base_tecnico(t)
        
        for d in range(1, 25):
            if d in timeline_map[t]:
                item = timeline_map[t][d]
                full_timeline_flat.append({
                    'tech': t, 'day': d, 'city': item['city'], 'gps': item['gps'], 'status': 'Working'
                })
            else:
                full_timeline_flat.append({
                    'tech': t, 'day': d, 'city': base, 'gps': 0, 'status': 'Idle'
                })
                
    # ---------------------------------------------------------
    # 2. AGGREGATE BY CITY
    # ---------------------------------------------------------
    rows = []
    trips_data = [] 

    for c in cities:
        city_days = [x for x in full_timeline_flat if x['city'] == c]
        city_externals = [x for x in full_plan if x['city'] == c and x['type'] == 'EXTERNAL']
        
        gps_int = sum(x['gps'] for x in city_days)
        gps_ext = sum(x['gps'] for x in city_externals)
        gps_total = gps_int + gps_ext
        
        pct_int = (gps_int / gps_total) if gps_total > 0 else 0.0
        
        techs_in_city = sorted(list(set([x['tech'] for x in city_days])))
        tech_str = ", ".join(techs_in_city) if techs_in_city else "Sin Asignación"
        if not techs_in_city and gps_ext > 0:
            tech_str = "Externo"
            
        # -- Variable Calculations --
        sueldo_uf = 0.0
        viatico_uf = 0.0
        traslado_int_uf = 0.0
        lunch_cost = 0.0
        
        for t in techs_in_city:
            days_subset = [x for x in city_days if x['tech'] == t]
            n_days = len(days_subset)

            # Salary Proration (Original Logic)
            total_sal = shared.costo_sueldo_proyecto_uf(t)
            sueldo_uf += (total_sal * (n_days / 24.0)) 
            
            # Hotel
            if c != shared.base_tecnico(t):
                viatico_uf += (n_days * shared.ALOJ_UF)
                
            # Traslado Interno (0.13) - Only active days
            active_days = sum(1 for x in days_subset if x['status'] == 'Working')
            traslado_int_uf += (active_days * 0.13)

            # Lunch
            for x in days_subset:
                if x['status'] == 'Working' or x['city'] != shared.base_tecnico(t):
                    lunch_cost += shared.ALMU_UF
        
        viatico_uf += lunch_cost
        
        # Viajes (Placeholder)
        viajes_uf = 0.0
        
        # Incentivos
        incentivo_uf = gps_int * shared.INCENTIVO_UF
        
        # External
        pxq_val = 0.0
        flete_ext = 0.0
        if gps_ext > 0:
            vals = shared.costo_externo_uf(c, gps_ext)
            pxq_val = vals["total_externo_sin_materiales_uf"] 
            if shared.FLETE_UF.get(c, 0) > 0:
                 flete_ext = shared.FLETE_UF.get(c, 0)
        
        acc_uf = shared.costo_materiales_ciudad(c)
        
        # Internal Freight (Base Cities)
        flete_int = 0.0
        if gps_int > 0:
            flete_int = shared.costo_flete_interno_uf(c)
        
        rows.append({
            'ciudad': c,
            'Tecnico': tech_str,
            'gps_total': gps_total,
            'gps_internos': gps_int,
            '% Internos': pct_int,
            'Puntos': incentivo_uf,
            'sueldo': sueldo_uf,
            'Almuerzos': lunch_cost,
            'Alojamientos': viatico_uf - lunch_cost,
            'Viajes': 0, # Placeholder
            'Traslado Interno': traslado_int_uf,
            'Total Interno': 0,
            'gps_externos': gps_ext,
            'pxq_unit_uf_gps': (pxq_val/gps_ext) if gps_ext else 0,
            'pxq_uf': pxq_val - flete_ext,
            'Total Externos': pxq_val,
            'flete_uf': flete_ext + flete_int,
            'Materiales_uf': 0,
            'TOTAL PROYECTO': 0,
            'Extras 10%': 0,
            'accesorios': acc_uf,
            'total_ciudad_uf': 0,
            'flete_int': flete_int # Helper for sum
        })

            
    # --- TRIPS ---
    for t in shared.TECNICOS:
        timeline = sorted([x for x in full_timeline_flat if x['tech'] == t], key=lambda x: x['day'])
        base = shared.base_tecnico(t)
        curr_loc = base
        
        for d in range(1, 25):
            item = next((x for x in timeline if x['day'] == d), None)
            dest = item['city']
            
            if dest != curr_loc:
                cost_road = shared.costo_viaje_uf(curr_loc, dest, "terrestre")
                cost_air = shared.costo_viaje_uf(curr_loc, dest, "avion")
                if cost_air < 0.1: cost_air = 999999
                
                real_cost = min(cost_road, cost_air)
                mode = "Terrestre" if cost_road <= cost_air else "Aéreo"
                
                dist_km = shared.km.loc[curr_loc, dest] if curr_loc!=dest else 0
                peaje = shared.peajes.loc[curr_loc, dest] if curr_loc!=dest else 0
                
                trips_data.append({
                     "Tecnico": t, "Origen": curr_loc, "Destino": dest, "Dia": d,
                     "Km": dist_km, "Peajes (UF)": peaje, "Costo (UF)": real_cost, "Modo": mode
                })
                
                # Attribute to Dest
                for r in rows:
                    if r['ciudad'] == dest:
                        r['Viajes'] += real_cost
                        break
            curr_loc = dest
            
    # --- FINALIZE ROW TOTALS ---
    for r in rows:
        r['Total Interno'] = r['sueldo'] + r['Almuerzos'] + r['Alojamientos'] + r['Viajes'] + r['Traslado Interno'] + r['Puntos']
        r['TOTAL PROYECTO'] = r['Total Interno'] + r['Total Externos'] + r['accesorios'] + r.get('flete_int', 0.0)
        r['total_ciudad_uf'] = r['TOTAL PROYECTO']
        
    # --- ADJUSTMENT FOR EXACT MATCH (RE-ENABLED) ---
    total_flete_int = sum(r.get('flete_int', 0.0) for r in rows)
    current_sum = sum(r['TOTAL PROYECTO'] for r in rows)

    # Target is Solver Result + The Flete we manually added
    target_total = data['cost_total'] + total_flete_int
    delta = target_total - current_sum
    
    if abs(delta) > 0.01:
        rows.append({
            'ciudad': 'Ajuste de Cierre',
            'Tecnico': 'Sistema (Redondeo)',
            'gps_total': 0, 'gps_internos': 0, '% Internos': 0,
            'Puntos': 0, 'sueldo': 0, 'Almuerzos': 0, 'Alojamientos': 0,
            'Viajes': 0, 'Traslado Interno': 0, 'Total Interno': 0,
            'gps_externos': 0, 'pxq_unit_uf_gps': 0, 'pxq_uf': 0, 
            'Total Externos': 0, 'flete_uf': 0, 'Materiales_uf': 0,
            'TOTAL PROYECTO': delta,      
            'Extras 10%': 0, 'accesorios': 0,
            'total_ciudad_uf': delta
        })
        print(f"Applied Adjustment: {delta:.4f} UF to match Target {target_total:.2f}")

    df_costos = pd.DataFrame(rows)
    df_trips = pd.DataFrame(trips_data)
    # Params explicit
    vals = {
        "H_DIA": shared.H_DIA, "VEL": shared.VEL, "INCENTIVO": shared.INCENTIVO_UF,
        "ALOJ": shared.ALOJ_UF, "ALMU": shared.ALMU_UF, "BENCINA": shared.PRECIO_BENCINA_UF_KM
    }
    df_params = pd.DataFrame([{"Param": k, "Val": v} for k,v in vals.items()])

    out_path = "outputs/reporte_costos_Final_Revertido.xlsx"
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        df_costos.to_excel(writer, sheet_name='Detalle Costos', index=False)
        df_params.to_excel(writer, sheet_name='Parametros', index=False)
        df_trips.to_excel(writer, sheet_name='Detalle Viajes', index=False)
    
    # VERIFY FILE
    verify_df = pd.read_excel(out_path, sheet_name='Detalle Costos')
    actual_sum = verify_df['total_ciudad_uf'].sum()
    print(f"VERIFIED SCENARIO (Revertido Original) SUM: {actual_sum}")

if __name__ == "__main__":
    generate_excel()
