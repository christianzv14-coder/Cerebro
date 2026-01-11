
import pandas as pd
import os

# Create data directory if not exists
os.makedirs('data', exist_ok=True)

data = [
    # INSTALACION (Complex)
    {'tipo_actividad': 'INSTALACION', 'sku': 'GPS_UNIT_STD', 'cantidad': 1.0},
    {'tipo_actividad': 'INSTALACION', 'sku': 'SIMCARD_M2M', 'cantidad': 1.0},
    {'tipo_actividad': 'INSTALACION', 'sku': 'CABLE_POWER_3M', 'cantidad': 1.0},
    {'tipo_actividad': 'INSTALACION', 'sku': 'FUSE_HOLDER', 'cantidad': 1.0},
    {'tipo_actividad': 'INSTALACION', 'sku': 'FUSE_2A', 'cantidad': 2.0}, # Uno de repuesto
    {'tipo_actividad': 'INSTALACION', 'sku': 'CINTA_AISLANTE_M', 'cantidad': 0.05}, # Metros?
    {'tipo_actividad': 'INSTALACION', 'sku': 'PRECINTO_SEGURIDAD', 'cantidad': 4.0},
    {'tipo_actividad': 'INSTALACION', 'sku': 'RELE_CORTE', 'cantidad': 1.0},
    {'tipo_actividad': 'INSTALACION', 'sku': 'SOCKET_RELE', 'cantidad': 1.0},
    
    # REVISION (Maintenance)
    {'tipo_actividad': 'REVISION', 'sku': 'FUSE_2A', 'cantidad': 1.0}, # Falla comun
    {'tipo_actividad': 'REVISION', 'sku': 'CINTA_AISLANTE_M', 'cantidad': 0.02},
    {'tipo_actividad': 'REVISION', 'sku': 'PRECINTO_SEGURIDAD', 'cantidad': 1.0}, # Romper para abrir
    
    # RETIRO (Recovery/Consumption)
    {'tipo_actividad': 'RETIRO', 'sku': 'CINTA_AISLANTE_M', 'cantidad': 0.05},
    {'tipo_actividad': 'RETIRO', 'sku': 'CAJA_EMBALAJE', 'cantidad': 1.0}, # Insumo de retiro
]

df = pd.DataFrame(data)
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'maestro_bom.xlsx')
df.to_excel(OUTPUT_FILE, index=False)
print(f"Template BOM created at {OUTPUT_FILE}")
