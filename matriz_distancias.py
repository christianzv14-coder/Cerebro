import time
import requests
import pandas as pd

GOOGLE_MAPS_API_KEY = "AIzaSyCl1TqEM40K5NL5fivonE8-XHn_0zdknlo"

# =========================================================
# CIUDADES (LAT / LNG)
# =========================================================
CITIES = {
    "Antofagasta": {"latitude": -23.6509, "longitude": -70.3975},
    "Chillán": {"latitude": -36.6063, "longitude": -72.1034},
    "Concepción": {"latitude": -36.8201, "longitude": -73.0444},
    "Coquimbo": {"latitude": -29.9533, "longitude": -71.3436},
    "Los Ángeles": {"latitude": -37.4694, "longitude": -72.3530},
    "Puerto Montt": {"latitude": -41.4689, "longitude": -72.9411},
    "Valparaíso": {"latitude": -33.0472, "longitude": -71.6127},
    "Rancagua": {"latitude": -34.1708, "longitude": -70.7444},
    "Santiago": {"latitude": -33.4489, "longitude": -70.6693},
    "Curicó": {"latitude": -34.9828, "longitude": -71.2394},
    "Temuco": {"latitude": -38.7359, "longitude": -72.5904},
    "Chiloé (Castro)": {"latitude": -42.4825, "longitude": -73.7624},
    "La Serena": {"latitude": -29.9027, "longitude": -71.2519},
    "Curanilahue": {"latitude": -37.4764, "longitude": -73.3467},
    "Talca": {"latitude": -35.4264, "longitude": -71.6554},
}

# =========================================================
# GOOGLE ROUTES API
# =========================================================
ROUTES_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
HEADERS = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
    "X-Goog-FieldMask": "originIndex,destinationIndex,condition,distanceMeters",
}

def route_matrix_chunk(origin_idx, dest_idx, city_names):
    body = {
        "origins": [
            {"waypoint": {"location": {"latLng": CITIES[city_names[i]]}}}
            for i in origin_idx
        ],
        "destinations": [
            {"waypoint": {"location": {"latLng": CITIES[city_names[j]]}}}
            for j in dest_idx
        ],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_UNAWARE",
        "units": "METRIC",
    }

    r = requests.post(ROUTES_URL, headers=HEADERS, json=body, timeout=90)
    r.raise_for_status()
    return r.json()

def main():
    if "PEGA_AQUI" in GOOGLE_MAPS_API_KEY:
        raise RuntimeError("❌ API KEY no configurada")

    city_names = list(CITIES.keys())
    n = len(city_names)

    matrix_km = [[0.0] * n for _ in range(n)]
    filled = 0
    block = 25  # 25x25 = 625 rutas por llamada

    for oi in range(0, n, block):
        for dj in range(0, n, block):
            origin_idx = list(range(oi, min(oi + block, n)))
            dest_idx = list(range(dj, min(dj + block, n)))

            resp = route_matrix_chunk(origin_idx, dest_idx, city_names)

            print(f"Chunk {oi}-{dj} | rutas: {len(resp)}")

            for e in resp:
                if e.get("condition") == "ROUTE_EXISTS" and "distanceMeters" in e:
                    o = origin_idx[e["originIndex"]]
                    d = dest_idx[e["destinationIndex"]]
                    km = e["distanceMeters"] / 1000.0

                    if km > 0:
                        matrix_km[o][d] = km
                        filled += 1

            time.sleep(0.05)  # rate limit sano

    print("===================================")
    print("Celdas llenadas:", filled)
    print("Ejemplo Santiago → Temuco:", matrix_km[city_names.index("Santiago")][city_names.index("Temuco")])
    print("===================================")

    df = pd.DataFrame(matrix_km, index=city_names, columns=city_names)
    df.to_csv("distancia_km.csv", sep=";", decimal=",", encoding="utf-8-sig")

    print("✅ OK -> distancia_km.csv generado")

if __name__ == "__main__":
    main()
