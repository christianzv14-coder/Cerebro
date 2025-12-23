import pandas as pd
import numpy as np

# ==========================
# PARAMETROS PEAJES
# ==========================
CLP_POR_KM = 35
TAG_SANTIAGO = 4000  # se suma si origen o destino es Santiago

# ==========================
# NOMBRES / ALIAS
# Ajusta si tus columnas/filas en distancia_km.csv usan otro texto
# ==========================
ALIASES = {
    # Variantes sin tilde -> con tilde
    "Valparaiso": "Valparaíso",
    "Curico": "Curicó",

    # Caso "Chiloé": en la matriz suele venir como "Chiloé (Castro)" si usaste el proxy
    "Chiloe": "Chiloé",
    "Chiloé": "Chiloé (Castro)",

    # Por si tu CSV trae "Castro" directo
    "Castro": "Chiloé (Castro)",
}

# Lista objetivo (orden deseado en la salida)
TARGET_CITIES = [
    "Antofagasta",
    "Chillán",
    "Concepción",
    "Coquimbo",
    "Los Ángeles",
    "Puerto Montt",
    "Valparaíso",
    "Rancagua",
    "Santiago",
    "Curicó",
    "Temuco",
    "Chiloé",
    "La Serena",
    "Curanilahue",
    "Talca",
]

def canon(name: str) -> str:
    return ALIASES.get(name, name)

def main():
    # --------------------------
    # 1) Cargar matriz km
    # --------------------------
    df_km = pd.read_csv(
        "distancia_km.csv",
        sep=";",
        decimal=",",
        index_col=0,
        encoding="utf-8-sig"
    )

    # Normaliza nombres en el df (por si hay diferencias de tildes/alias)
    df_km.index = df_km.index.map(lambda x: canon(str(x).strip()))
    df_km.columns = [canon(str(c).strip()) for c in df_km.columns]

    # --------------------------
    # 2) Armar matriz objetivo (reindex)
    # --------------------------
    tgt = [canon(x) for x in TARGET_CITIES]

    # Consolidar posibles duplicados por alias (ej: Chiloé -> Chiloé (Castro))
    seen = set()
    tgt_unique = []
    label_map = []
    for original in TARGET_CITIES:
        c = canon(original)
        if c not in seen:
            seen.add(c)
            tgt_unique.append(c)
            label_map.append(original)

    df_km2 = df_km.reindex(index=tgt_unique, columns=tgt_unique)

    # --------------------------
    # 3) Calcular peajes
    # --------------------------
    # Regla: si km es NaN o 0 (sin ruta), dejamos NaN (y 0 en diagonal)
    peajes = df_km2.astype(float) * CLP_POR_KM

    # TAG Santiago (si Santiago existe en index)
    if "Santiago" in peajes.index:
        s = "Santiago"
        for city in peajes.columns:
            if city == s:
                continue
            if pd.notna(peajes.loc[s, city]) and peajes.loc[s, city] > 0:
                peajes.loc[s, city] = peajes.loc[s, city] + TAG_SANTIAGO
            if pd.notna(peajes.loc[city, s]) and peajes.loc[city, s] > 0:
                peajes.loc[city, s] = peajes.loc[city, s] + TAG_SANTIAGO

    # Diagonal 0
    np.fill_diagonal(peajes.values, 0)

    # Redondeo a CLP
    peajes = peajes.round(0)

    # --------------------------
    # 4) Exportar
    # --------------------------
    peajes.to_csv("matriz_peajes_clp.csv", sep=";", decimal=",", encoding="utf-8-sig")
    print("OK -> matriz_peajes_clp.csv generado")

    # Reporte de control (qué faltó)
    missing_rows = peajes.index[peajes.isna().all(axis=1)].tolist()
    missing_cols = peajes.columns[peajes.isna().all(axis=0)].tolist()
    if missing_rows or missing_cols:
        print("WARNING: ciudades sin datos (no encontradas en distancia_km.csv o sin rutas):")
        print(" - filas:", missing_rows)
        print(" - cols:", missing_cols)

if __name__ == "__main__":
    main()
