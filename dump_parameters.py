
import pandas as pd
import os
import modelo_optimizacion_gps_chile_v1 as model

def dump_params():
    output = []
    output.append("=== PARÁMETROS GENERALES (parametros.xlsx) ===")
    param_df = pd.read_excel("data/parametros.xlsx")
    output.append(param_df.to_string())
    
    output.append("\n=== COSTOS MATERIALES (materiales.xlsx) ===")
    kits = pd.read_excel("data/materiales.xlsx")
    output.append(kits.to_string())

    output.append("\n=== TÉCNICOS INTERNOS (tecnicos_internos.xlsx) ===")
    techs = pd.read_excel("data/tecnicos_internos.xlsx")
    output.append(techs[['tecnico', 'ciudad_base', 'sueldo_uf', 'hh_semana_proyecto']].to_string())

    output.append("\n=== COSTOS EXTERNOS (costos_externos.xlsx) - 5 Examples ===")
    pxq = pd.read_excel("data/costos_externos.xlsx")
    output.append(pxq.head(5).to_string())

    output.append("\n=== FLETES (flete_ciudad.xlsx) - 5 Examples ===")
    flete = pd.read_excel("data/flete_ciudad.xlsx")
    output.append(flete.head(5).to_string())
    
    output.append("\n=== MODEL CONSTANTS ===")
    output.append(f"H_DIA: {model.H_DIA}")
    output.append(f"TIEMPO_INST: {model.TIEMPO_INST_GPS_H}")
    output.append(f"DIAS_PROYECTO: {model.DIAS_MAX}")
    output.append(f"INCENTIVO: {model.INCENTIVO_UF}")
    output.append(f"VIATICO_ALOJ: {model.ALOJ_UF}")
    output.append(f"VIATICO_ALM: {model.ALMU_UF}")
    output.append(f"BENCINA_KM: {model.PRECIO_BENCINA_UF_KM}")
    
    with open("parameters_dump.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    print("Dump created.")

if __name__ == "__main__":
    dump_params()
