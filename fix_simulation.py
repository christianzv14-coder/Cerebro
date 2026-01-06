
import os

target_file = "modelo_optimizacion_gps_chile_v1.py"

new_function_code = r'''def simulate_tech_schedule(tecnico: str, cities_list: list[str], gps_asignados: dict[str, int]):
    base = base_tecnico(tecnico)
    hd = horas_diarias(tecnico)
    gpd = gps_por_dia(tecnico)
    dias_cap = dias_disponibles_proyecto(tecnico)

    if hd <= 1e-9 or gpd <= 0 or dias_cap <= 0:
        return [], {"total_uf": 1e18}, False

    day = 1
    sleep_city = base

    plan = []
    cost = {"travel_uf": 0.0, "aloj_uf": 0.0, "alm_uf": 0.0, "inc_uf": 0.0, "sueldo_uf": 0.0, "flete_uf": 0.0}

    sueldo_proy = costo_sueldo_proyecto_uf(tecnico)
    sueldo_dia = sueldo_proy / max(1, dias_cap) 

    pending = {c: int(max(0, gps_asignados.get(c, 0))) for c in cities_list}

    def can_install_today(time_left_h: float) -> int:
        return int(math.floor(time_left_h / max(1e-9, TIEMPO_INST_GPS_H)))

    # LOOP GENERAL POR CIUDAD
    cities_idx = 0
    
    while cities_idx < len(cities_list) and day <= (dias_cap + 5): 
        c = cities_list[cities_idx]
        
        if pending.get(c, 0) <= 0:
            cities_idx += 1
            continue
            
        if day > dias_cap:
            break

        # --- CHECK SUNDAY (Day 7, 14, 21...) ---
        if day % 7 == 0:
            if sleep_city != base:
                cost["aloj_uf"] += ALOJ_UF
                cost["alm_uf"] += ALMU_UF
            
            plan.append({
                "tecnico": tecnico, "dia": day, "ciudad_trabajo": sleep_city,
                "horas_instal": 0.0, "gps_inst": 0, "viaje_modo_manana": None, 
                "duerme_en": sleep_city, "nota": "DOMINGO (Descanso)"
            })
            day += 1
            continue

        # --- DÍA LABORAL ---
        tv = 0.0
        modo_in = None
        
        if sleep_city != c:
            modo_in = choose_mode(sleep_city, c)
            tv = t_viaje(sleep_city, c, modo_in)
            cv = costo_viaje_uf(sleep_city, c, modo_in)
            
            if tv > hd:
                cost["travel_uf"] += cv
                if flete_aplica(c, base, modo_in):
                   cost["flete_uf"] += safe_float(FLETE_UF.get(c, 0.0), 0.0)
                cost["travel_uf"] += 0.13
                
                cost["alm_uf"] += ALMU_UF
                cost["sueldo_uf"] += sueldo_dia
                cost["aloj_uf"] += ALOJ_UF
                
                sleep_city = c
                plan.append({
                    "tecnico": tecnico, "dia": day, "ciudad_trabajo": c,
                    "horas_instal": 0.0, "gps_inst": 0,
                    "viaje_modo_manana": modo_in, "viaje_h_manana": tv,
                    "duerme_en": c, "nota": "Día Solo Viaje (>8h)"
                })
                day += 1
                continue
            else:
                cost["travel_uf"] += cv
                if flete_aplica(c, base, modo_in):
                    cost["flete_uf"] += safe_float(FLETE_UF.get(c, 0.0), 0.0)
                cost["travel_uf"] += 0.13
        
        time_left = max(0.0, hd - tv)
        gps_can = can_install_today(time_left)
        gps_inst = min(pending[c], gps_can)
        
        horas_instal = gps_inst * TIEMPO_INST_GPS_H
        pending[c] -= gps_inst
        cost["inc_uf"] += INCENTIVO_UF * gps_inst
        
        cost["alm_uf"] += ALMU_UF
        cost["sueldo_uf"] += sueldo_dia
        
        sleep_city = c
        if sleep_city != base:
            cost["aloj_uf"] += ALOJ_UF
            
        plan.append({
            "tecnico": tecnico, "dia": day, "ciudad_trabajo": c,
            "horas_instal": horas_instal, "gps_inst": int(gps_inst),
            "viaje_modo_manana": modo_in, "viaje_h_manana": tv,
            "duerme_en": sleep_city, "nota": ""
        })
        day += 1

    # --- RETORNO A BASE ---
    if sleep_city != base:
        modo_ret = choose_mode(sleep_city, base)
        tv_ret = t_viaje(sleep_city, base, modo_ret)
        cv_ret = costo_viaje_uf(sleep_city, base, modo_ret)

        cost["travel_uf"] += cv_ret
        if tv_ret > hd:
             cost["aloj_uf"] += ALOJ_UF
        
        plan.append({
            "tecnico": tecnico, "dia": day, "ciudad_trabajo": base,
            "horas_instal": 0.0, "gps_inst": 0, "viaje_modo_manana": modo_ret, 
            "viaje_h_manana": tv_ret, "duerme_en": base, "nota": "Retorno a Base"
        })

    feasible = all(pending[c] <= 0 for c in cities_list)
    cost["total_uf"] = sum(v for k, v in cost.items() if k != "total_uf")
    
    return plan, cost, feasible'''

# Read Original
with open(target_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find start and end of function
start_line = -1
end_line = -1

for i, line in enumerate(lines):
    if line.strip().startswith("def simulate_tech_schedule("):
        start_line = i
    if start_line != -1 and line.strip().startswith("def allocate_gps_work_factible("):
        end_line = i
        break

if start_line != -1 and end_line != -1:
    print(f"Replacing lines {start_line} to {end_line}")
    # Keep lines before start
    new_lines = lines[:start_line]
    # Insert new code
    new_lines.append(new_function_code + "\n\n")
    # Keep lines after end (allocate_gps...)
    new_lines.extend(lines[end_line:])
    
    with open(target_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("Replacement success.")
else:
    print("Could not find function boundaries.")
