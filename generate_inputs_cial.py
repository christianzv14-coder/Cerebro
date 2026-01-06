
import pandas as pd
import os

UF = 39500

# 1. DEMANDA
demanda_data = [
    ["Rancagua", 10, 0],
    ["Santiago", 135, 0],
    ["San Antonio", 5, 0],
    ["San Fernando", 16, 0],
    ["Viña del Mar", 26, 0],
    ["Talca", 9, 0],
    ["San Felipe", 5, 0],
    ["Copiapo", 8, 0],
    ["Antofagasta", 10, 0],
    ["La Serena", 13, 0], 
    ["Calama", 4, 0],
    ["Iquique", 4, 0],
    ["Arica", 4, 0],
    ["Temuco", 15, 0],
    ["Concepcion", 16, 0],
    ["Chillan", 7, 0],
    ["Puerto Montt", 7, 0],
    ["Osorno", 8, 0],
    ["Los Angeles", 8, 0],
    ["Punta Arenas", 3, 0],
    ["Coyhaique", 1, 0]
]
df_dem = pd.DataFrame(demanda_data, columns=["ciudad", "vehiculos_1gps", "vehiculos_2gps"])

# 2. TECNICOS
# Lista corregida según imagen del usuario
tech_data = [
    ["Luis", "Santiago", 14.7, 1.0],
    ["Wilmer", "Santiago", 14.7, 1.0],
    ["Fabian D.", "Santiago", 14.7, 1.0],
    ["Efrain", "Santiago", 14.7, 1.0],
    ["Jimmy", "Chillan", 14.7, 1.0], 
    ["Carlos", "Santiago", 14.7, 1.0], # Assuming Santiago unless specified
    ["Orlando", "Calama", 14.7, 1.0]
]
df_tech = pd.DataFrame(tech_data, columns=["tecnico", "ciudad_base", "sueldo_uf", "hh_semana_proyecto"])

# 3. PARAMETROS
param_data = [
    ["semanas_proyecto", 4.0],
    ["dias_semana", 6.0],
    ["horas_jornada", 8.0], # 100% de 8 horas
    ["incentivo_por_gps", 0.87], # ACTUALIZADO 0.87
    ["alojamiento_uf_noche", 1.1],
    ["almuerzo_uf_dia", 0.5],
    ["precio_bencina_uf_km", 0.00342], # ACTUALIZADO 1300CLP/10kmL / 38000 = 0.00342
    ["tiempo_instalacion_gps", 2.5], 
    ["hh_mes", 180.0]
]
df_param = pd.DataFrame(param_data, columns=["parametro", "valor"])

# 4. MATERIALES (Kits)
# "kits vale 1381,6 UF totales / 314 = 4.40 UF/u"
kit_data = [
    ["1_GPS", 4.40],
    ["2_GPS", 8.80]
]
df_kit = pd.DataFrame(kit_data, columns=["tipo_kit", "costo"])

# 5. COSTOS EXTERNOS (PxQ)
# Convertir Pesos a UF
pxq_clp = {
    "Santiago": 108000,
    "Rancagua": 65000,
    "San Antonio": 65000,
    "San Fernando": 65000,
    "Viña del Mar": 65000,
    "Talca": 80000,
    "San Felipe": 65000,
    "Copiapo": 65000,
    "Antofagasta": 100000,
    "La Serena": 70000,
    "Calama": 100000,
    "Iquique": 100000,
    "Arica": 65000,
    "Temuco": 67000,
    "Concepcion": 70000,
    "Chillan": 67000,
    "Puerto Montt": 100000,
    "Osorno": 116000,
    "Los Angeles": 70000,
    "Punta Arenas": 100000,
    "Coyhaique": 100000
}

pxq_rows = []
for city, clp in pxq_clp.items():
    uf_val = round(clp / float(38300.0), 4) # Assuming ~38300 UF or using variable UF if defined
    pxq_rows.append([city, uf_val])

df_pxq = pd.DataFrame(pxq_rows, columns=["ciudad", "pxq_externo"])

# 6. FLETE
# Tabla especifica proporcionada por el usuario (UF)
flete_data_user = {
    "Antofagasta": 1.3,
    "Arica": 1.7,
    "Coronel": 0.4,
    "Calama": 1.5,
    "Caldera": 0.4,
    "Castro": 0.4,
    "Puerto Aysen": 1.7,
    "Chillan": 0.4,
    "Concepcion": 0.4,
    "Copiapo": 0.4,
    "Coquimbo": 0.4,
    "Iquique": 1.5,
    "Lautaro": 0.4,
    "Linares": 0.4,
    "Los Angeles": 0.4,
    "Mejillones": 0.4,
    "Osorno": 0.4,
    "Ovalle": 0.4,
    "Pichirropulli": 0.4,
    "Puerto Montt": 0.4,
    "Puerto Natales": 1.7,
    "Puerto Williams": 1.7,
    "Punta Arenas": 1.7,
    "Romeral": 0.3,
    "San Antonio": 0.3,
    "San Fernando": 0.3,
    "San Vicente": 0.3,
    "Santiago": 0.0,
    "Talca": 0.4,
    "Valdivia": 0.4,
    "Valparaiso": 0.3,
    "Viña del Mar": 0.3, # Asumiendo igual a Valpo
    "La Serena": 0.4, # Asumiendo igual a Coquimbo/Ovalle 0.4
    "San Felipe": 0.3, # Asumiendo zona central interior
    "Rancagua": 0.3, # Zona central
    "Temuco": 0.4, # Zona sur
    "Coyhaique": 1.7 # Zona austral (Puerto Aysen ref)
}

flete_rows = []
for c in df_dem["ciudad"]:
    # Buscar exacto o default 0.4
    cost = flete_data_user.get(c, 0.4)
    # Ajustes manuales si nombre no coincide exacto
    if c == "La Serena": cost = 0.4 
    if c == "Coyhaique": cost = 1.7
    flete_rows.append([c, cost])

df_flete = pd.DataFrame(flete_rows, columns=["ciudad", "costo_flete"])


path = "data/"
os.makedirs(path, exist_ok=True)

df_dem.to_excel(os.path.join(path, "demanda_ciudades.xlsx"), index=False)
df_tech.to_excel(os.path.join(path, "tecnicos_internos.xlsx"), index=False)
df_param.to_excel(os.path.join(path, "parametros.xlsx"), index=False)
df_kit.to_excel(os.path.join(path, "materiales.xlsx"), index=False)
df_pxq.to_excel(os.path.join(path, "costos_externos.xlsx"), index=False)
df_flete.to_excel(os.path.join(path, "flete_ciudad.xlsx"), index=False)

print("Primary inputs generated in data/")
