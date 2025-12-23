import math
import pandas as pd

# =========================================================
# CONFIG MODELO
# =========================================================
ALPHA_CLP_POR_KM = 110     # costo variable
BETA_FIJO = 20000         # fee base por tramo

# =========================================================
# CIUDADES (TU LISTA) → "AEROPUERTO" ASIGNADO
# Nota operativa:
# - Varias ciudades NO tienen vuelo comercial directo.
# - Para que puedas construir una matriz, las mapeo a su aeropuerto más cercano/usable.
# - Si dos ciudades comparten el mismo aeropuerto (ej: Valparaíso y Santiago -> SCL),
#   NO se considera "vuelo" entre ellas (queda None).
# =========================================================
AIRPORTS = {
    # Norte
    "Antofagasta":   {"iata": "ANF", "lat": -23.4445,   "lon": -70.4451},

    # Centro / Centro Sur
    "La Serena":     {"iata": "LSC", "lat": -29.9162,   "lon": -71.1995},
    "Coquimbo":      {"iata": "LSC", "lat": -29.9162,   "lon": -71.1995},   # comparte LSC

    "Santiago":      {"iata": "SCL", "lat": -33.3890,   "lon": -70.7847},
    "Valparaíso":    {"iata": "SCL", "lat": -33.3890,   "lon": -70.7847},   # proxy: SCL
    "Rancagua":      {"iata": "SCL", "lat": -33.3890,   "lon": -70.7847},   # proxy: SCL

    "Concepción":    {"iata": "CCP", "lat": -36.771389, "lon": -73.0625},
    "Chillán":       {"iata": "CCP", "lat": -36.771389, "lon": -73.0625},   # proxy: CCP
    "Curanilahue":   {"iata": "CCP", "lat": -36.771389, "lon": -73.0625},   # proxy: CCP

    "Temuco":        {"iata": "ZCO", "lat": -38.9259,   "lon": -72.6515},

    "Los Ángeles":   {"iata": "LSQ", "lat": -37.401699, "lon": -72.425400}, # María Dolores (LSQ)

    "Talca":         {"iata": "TLX", "lat": -35.3778,   "lon": -71.6017},   # Panguilemo (TLX)
    "Curicó":        {"iata": "TLX", "lat": -35.3778,   "lon": -71.6017},   # proxy: TLX

    # Sur
    "Puerto Montt":  {"iata": "PMC", "lat": -41.438975, "lon": -73.095042},

    # Chiloé
    "Chiloé":        {"iata": "MHC", "lat": -42.34611,  "lon": -73.71389},  # Mocopulli (MHC)
}

# =========================================================
# RUTAS AÉREAS VÁLIDAS (DOMÉSTICO) – versión simple
# - Considera principalmente HUB Santiago (SCL) con el resto.
# - Si quieres agregar rutas regionales (ej CCP<->PMC), las sumas abajo.
# =========================================================
VALID_ROUTES = {
    ("SCL", "ANF"),
    ("SCL", "LSC"),
    ("SCL", "CCP"),
    ("SCL", "ZCO"),
    ("SCL", "LSQ"),
    ("SCL", "TLX"),
    ("SCL", "PMC"),
    ("SCL", "MHC"),

    # Opcionales (si quieres permitirlas):
    # ("CCP", "PMC"),
    # ("CCP", "ZCO"),
}

# hacer simétricas
VALID_ROUTES = VALID_ROUTES.union({(b, a) for (a, b) in VALID_ROUTES})

# =========================================================
# FUNCIONES
# =========================================================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

# =========================================================
# MATRICES
# =========================================================
cities = list(AIRPORTS.keys())
n = len(cities)

matrix_km = [[None] * n for _ in range(n)]
matrix_cost = [[None] * n for _ in range(n)]

for i, ci in enumerate(cities):
    for j, cj in enumerate(cities):
        if i == j:
            matrix_km[i][j] = 0
            matrix_cost[i][j] = 0
            continue

        ai, aj = AIRPORTS[ci]["iata"], AIRPORTS[cj]["iata"]

        # Si comparten el mismo aeropuerto asignado, no hay "vuelo" entre ciudades
        if ai == aj:
            continue

        # Si no es ruta válida, se deja None (tu modelo luego puede fill con Big-M)
        if (ai, aj) not in VALID_ROUTES:
            continue

        d = haversine(
            AIRPORTS[ci]["lat"], AIRPORTS[ci]["lon"],
            AIRPORTS[cj]["lat"], AIRPORTS[cj]["lon"]
        )

        cost = ALPHA_CLP_POR_KM * d + BETA_FIJO

        matrix_km[i][j] = round(d, 1)
        matrix_cost[i][j] = round(cost)

# =========================================================
# EXPORT
# =========================================================
df_km = pd.DataFrame(matrix_km, index=cities, columns=cities)
df_cost = pd.DataFrame(matrix_cost, index=cities, columns=cities)

df_km.to_csv("matriz_aerea_km.csv", sep=";", decimal=",", encoding="utf-8-sig")
df_cost.to_csv("matriz_aerea_costo_clp.csv", sep=";", decimal=",", encoding="utf-8-sig")

print("✅ Matrices aéreas generadas: matriz_aerea_km.csv | matriz_aerea_costo_clp.csv")
