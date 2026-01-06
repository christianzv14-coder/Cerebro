
import pandas as pd
import numpy as np
import os

# 1. Configuración
UF = 39500
CITIES = [
    "Santiago", "Rancagua", "San Antonio", "San Fernando", "Viña del Mar", "Talca",
    "San Felipe", "Copiapo", "Antofagasta", "La Serena", "Calama", "Iquique", "Arica",
    "Temuco", "Concepcion", "Chillan", "Puerto Montt", "Osorno", "Los Angeles",
    "Punta Arenas", "Coyhaique"
]

# Posición aproximada "Km lineales desde Santiago" (Norte negativo, Sur positivo)
# Ajustado para simular rutas reales carretera
POS_KM = {
    "Arica": -2060,
    "Iquique": -1780,
    "Calama": -1570,
    "Antofagasta": -1370,
    "Copiapo": -800,
    "La Serena": -470,
    "San Felipe": -95,
    "Viña del Mar": -120,
    "Santiago": 0,
    "San Antonio": 115, # Ruta 78
    "Rancagua": 85,
    "San Fernando": 140,
    "Talca": 255,
    "Chillan": 400,
    "Concepcion": 500,
    "Los Angeles": 510,
    "Temuco": 670,
    "Osorno": 930,
    "Puerto Montt": 1032,
    "Coyhaique": 1700, # Carretera Austral / Argentina
    "Punta Arenas": 3000 # Ruta por Argentina obligada
}

# Aeropuertos (Si/No, Tiempo Vuelo SCL estimado hrs, Costo Base UF SCL estimado)
AIRPORTS = {
    "Arica":        {"has": True, "time": 2.6, "cost_uf": 5.0},
    "Iquique":      {"has": True, "time": 2.3, "cost_uf": 4.5},
    "Calama":       {"has": True, "time": 2.1, "cost_uf": 4.5},
    "Antofagasta":  {"has": True, "time": 1.9, "cost_uf": 4.0},
    "Copiapo":      {"has": True, "time": 1.2, "cost_uf": 3.5},
    "La Serena":    {"has": True, "time": 1.0, "cost_uf": 3.0},
    "Santiago":     {"has": True, "time": 0.0, "cost_uf": 0.0},
    "Concepcion":   {"has": True, "time": 1.1, "cost_uf": 3.0},
    "Temuco":       {"has": True, "time": 1.3, "cost_uf": 3.5},
    "Puerto Montt": {"has": True, "time": 1.7, "cost_uf": 4.0},
    "Osorno":       {"has": True, "time": 1.6, "cost_uf": 4.0},
    "Coyhaique":    {"has": True, "time": 2.3, "cost_uf": 5.5}, # Balmaceda
    "Punta Arenas": {"has": True, "time": 3.5, "cost_uf": 6.5},
    # Sin aeropuerto comercial directo regular útil para el modelo diario
    "Rancagua":     {"has": False},
    "San Antonio":  {"has": False},
    "San Fernando": {"has": False},
    "Viña del Mar": {"has": False},
    "Talca":        {"has": False},
    "San Felipe":   {"has": False},
    "Chillan":      {"has": False},
    "Los Angeles":  {"has": False},
}

# Generar Matrices
n = len(CITIES)
dist_df = pd.DataFrame(index=CITIES, columns=CITIES).fillna(0.0)
peaje_df = pd.DataFrame(index=CITIES, columns=CITIES).fillna(0.0)
air_cost_df = pd.DataFrame(index=CITIES, columns=CITIES).fillna(0.0)
air_time_df = pd.DataFrame(index=CITIES, columns=CITIES).fillna(0.0)

for c1 in CITIES:
    for c2 in CITIES:
        if c1 == c2:
            continue
            
        # 1. Distancia Terrestre
        # Heuristica simple: diferencia absoluta, ajustada levemente
        raw_dist = abs(POS_KM[c1] - POS_KM[c2])
        
        # Ajustes especificos conocidos
        if (c1, c2) in [("Santiago", "Viña del Mar"), ("Viña del Mar", "Santiago")]: raw_dist = 120
        if (c1, c2) in [("Santiago", "San Antonio"), ("San Antonio", "Santiago")]: raw_dist = 110
        if (c1, c2) in [("Viña del Mar", "San Antonio"), ("San Antonio", "Viña del Mar")]: raw_dist = 90
        
        dist_df.loc[c1, c2] = raw_dist

        # 2. Peajes
        # Asumimos costo medio $25 CLP/km a UF
        clp_peaje = raw_dist * 25
        # Castigo zona sur (>Chillan) mas caro? No, approx parejo
        peaje_df.loc[c1, c2] = round(clp_peaje / UF, 4)

        # 3. Avion
        # Logica: Si ambos tienen aeropuerto, calcular. Si no, costo infinito (1000 UF)
        if AIRPORTS[c1]["has"] and AIRPORTS[c2]["has"]:
            # Tiempo: t(SCL->c1) + t(SCL->c2) + espera escala si no es SCL
            t1 = AIRPORTS[c1].get("time", 0)
            t2 = AIRPORTS[c2].get("time", 0)
            
            if c1 == "Santiago":
                total_time = t2
                total_cost = AIRPORTS[c2].get("cost_uf", 0)
            elif c2 == "Santiago":
                total_time = t1
                total_cost = AIRPORTS[c1].get("cost_uf", 0)
            else:
                # Vuelo con escala en SCL (c1 -> SCL -> c2)
                total_time = t1 + t2 + 1.5 # 1.5 hr escala
                total_cost = AIRPORTS[c1].get("cost_uf", 0) + AIRPORTS[c2].get("cost_uf", 0)
                
            air_time_df.loc[c1, c2] = round(total_time, 2)
            air_cost_df.loc[c1, c2] = round(total_cost, 2)
        else:
            air_time_df.loc[c1, c2] = 24.0 # Penalizar tiempo
            air_cost_df.loc[c1, c2] = 1000.0 # Prohibitivo

path = "data/"
os.makedirs(path, exist_ok=True)

dist_df.to_excel(os.path.join(path, "matriz_distancia_km.xlsx"))
peaje_df.to_excel(os.path.join(path, "matriz_peajes.xlsx"))
air_cost_df.to_excel(os.path.join(path, "matriz_costo_avion.xlsx"))
air_time_df.to_excel(os.path.join(path, "matriz_tiempo_avion.xlsx"))

print("Matrices generated successfully in data/")
