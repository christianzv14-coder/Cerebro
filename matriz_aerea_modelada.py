import math
import pandas as pd

# =========================================================
# CONFIG MODELO
# =========================================================
ALPHA_CLP_POR_KM = 110     # costo variable
BETA_FIJO = 20000         # fee base por tramo

# =========================================================
# CIUDADES → AEROPUERTOS (IATA + coordenadas)
# =========================================================
AIRPORTS = {
    "Arica":            {"iata": "ARI", "lat": -18.3485, "lon": -70.3387},
    "Iquique":          {"iata": "IQQ", "lat": -20.5352, "lon": -70.1813},
    "Antofagasta":      {"iata": "ANF", "lat": -23.4445, "lon": -70.4451},
    "Calama":           {"iata": "CJC", "lat": -22.4980, "lon": -68.9030},
    "Copiapó":          {"iata": "CPO", "lat": -27.2969, "lon": -70.4131},
    "La Serena":        {"iata": "LSC", "lat": -29.9162, "lon": -71.1995},
    "Santiago":         {"iata": "SCL", "lat": -33.3929, "lon": -70.7858},
    "Concepción":       {"iata": "CCP", "lat": -36.7727, "lon": -73.0631},
    "Temuco":           {"iata": "ZCO", "lat": -38.7668, "lon": -72.6371},
    "Valdivia":         {"iata": "ZAL", "lat": -39.6500, "lon": -73.0861},
    "Puerto Montt":     {"iata": "PMC", "lat": -41.4389, "lon": -73.0940},
    "Punta Arenas":     {"iata": "PUQ", "lat": -53.0026, "lon": -70.8546},
}

# =========================================================
# RUTAS AÉREAS VÁLIDAS (CHILE DOMÉSTICO)
# =========================================================
VALID_ROUTES = {
    # Hub Santiago
    ("SCL", "ARI"), ("SCL", "IQQ"), ("SCL", "ANF"), ("SCL", "CJC"),
    ("SCL", "CPO"), ("SCL", "LSC"), ("SCL", "CCP"),
    ("SCL", "ZCO"), ("SCL", "ZAL"), ("SCL", "PMC"), ("SCL", "PUQ"),

    # Norte
    ("ANF", "CJC"), ("IQQ", "ANF"),

    # Bidireccionalidad
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

    a = math.sin(dphi / 2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return 2 * R * math.asin(math.sqrt(a))

# =========================================================
# MATRICES
# =========================================================
cities = list(AIRPORTS.keys())
n = len(cities)

matrix_km = [[None]*n for _ in range(n)]
matrix_cost = [[None]*n for _ in range(n)]

for i, ci in enumerate(cities):
    for j, cj in enumerate(cities):
        if i == j:
            matrix_km[i][j] = 0
            matrix_cost[i][j] = 0
            continue

        ai, aj = AIRPORTS[ci]["iata"], AIRPORTS[cj]["iata"]

        if (ai, aj) not in VALID_ROUTES:
            continue  # no existe vuelo

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

print("✅ Matrices aéreas generadas")
