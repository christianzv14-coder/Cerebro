import time
import math
import requests
import pandas as pd

GOOGLE_MAPS_API_KEY = "AIzaSyCl1TqEM40K5NL5fivonE8-XHn_0zdknlo"

CITIES = {
    "Antofagasta": {"latitude": -23.6509, "longitude": -70.3975},
    "Arica": {"latitude": -18.4783, "longitude": -70.3126},
    "Coronel": {"latitude": -37.0167, "longitude": -73.1333},
    "Calama": {"latitude": -22.4559, "longitude": -68.9306},
    "Caldera": {"latitude": -27.0697, "longitude": -70.8171},
    "Castro": {"latitude": -42.4825, "longitude": -73.7624},
    "Puerto Chacabuco": {"latitude": -45.4631, "longitude": -72.8266},
    "Chillán": {"latitude": -36.6063, "longitude": -72.1034},
    "Concepción": {"latitude": -36.8201, "longitude": -73.0444},
    "Copiapó": {"latitude": -27.3668, "longitude": -70.3314},
    "Coquimbo": {"latitude": -29.9533, "longitude": -71.3436},
    "Iquique": {"latitude": -20.2307, "longitude": -70.1357},
    "Lautaro": {"latitude": -38.5339, "longitude": -72.4481},
    "Linares": {"latitude": -35.8464, "longitude": -71.5937},
    "Los Ángeles": {"latitude": -37.4694, "longitude": -72.3530},
    "Mejillones": {"latitude": -23.1014, "longitude": -70.4486},
    "Osorno": {"latitude": -40.5739, "longitude": -73.1335},
    "Ovalle": {"latitude": -30.5983, "longitude": -71.1990},
    "Pichirropulli": {"latitude": -39.8778, "longitude": -72.5606},
    "Puerto Montt": {"latitude": -41.4689, "longitude": -72.9411},
    "Puerto Natales": {"latitude": -51.7236, "longitude": -72.4875},
    "Puerto Williams": {"latitude": -54.9333, "longitude": -67.6167},
    "Punta Arenas": {"latitude": -53.1638, "longitude": -70.9171},
    "Romeral": {"latitude": -34.9635, "longitude": -71.1262},
    "San Antonio": {"latitude": -33.5933, "longitude": -71.6217},
    "San Fernando": {"latitude": -34.5844, "longitude": -70.9890},
    "San Vicente": {"latitude": -34.4389, "longitude": -71.0789},
    "Santiago": {"latitude": -33.4489, "longitude": -70.6693},
    "Talca": {"latitude": -35.4264, "longitude": -71.6554},
    "Valdivia": {"latitude": -39.8142, "longitude": -73.2459},
    "Valparaíso": {"latitude": -33.0472, "longitude": -71.6127},
}

# =========================================================
# ROUTES API
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
    if "TU_API_KEY" in GOOGLE_MAPS_API_KEY:
        raise RuntimeError("❌ No pegaste la API KEY")

    city_names = list(CITIES.keys())
    n = len(city_names)

    matrix_km = [[0.0] * n for _ in range(n)]

    # CONTADOR BRUTAL
    filled = 0

    block = 25  # 25x25 = 625 elementos

    for oi in range(0, n, block):
        for dj in range(0, n, block):
            origin_idx = list(range(oi, min(oi + block, n)))
            dest_idx = list(range(dj, min(dj + block, n)))

            resp = route_matrix_chunk(origin_idx, dest_idx, city_names)

            print(f"Chunk {oi}-{dj} | items: {len(resp)} | ejemplo: {resp[0] if resp else 'VACÍO'}")

            for e in resp:
                if e.get("condition") == "ROUTE_EXISTS" and "distanceMeters" in e:
                    o = origin_idx[e["originIndex"]]
                    d = dest_idx[e["destinationIndex"]]
                    km = e["distanceMeters"] / 1000.0

                    if km > 0:
                        matrix_km[o][d] = km
                        filled += 1

            time.sleep(0.05)

    print("===================================")
    print("Celdas llenadas (km > 0):", filled)
    print("Ejemplo Antofagasta → Arica:", matrix_km[0][1])
    print("===================================")

    df = pd.DataFrame(matrix_km, index=city_names, columns=city_names)
    df.to_csv("distancia_km.csv", sep=";", decimal=",", encoding="utf-8-sig")

    print("✅ OK -> distancia_km.csv generado")

if __name__ == "__main__":
    main()
