import pandas as pd
import os
import sys

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_RAW = os.path.join(BASE_DIR, 'data', 'ACTIVIDADES ANUALES(ACTIVIDADES_DIARIAS) (1).xlsx')
OUTPUT_TARGET = os.path.join(BASE_DIR, 'data', 'input_actividades.xlsx')
SHEET_NAME = 'ACTIVIDADES ANUALES(ACTIVIDADES'

# Date Filter
START_DATE = '2025-01-01'
END_DATE = '2026-01-08'

def clean_column_name(name):
    return str(name).strip()

def main():
    print("🚀 Iniciando Transformación de Datos Reales...")
    
    if not os.path.exists(INPUT_RAW):
        print(f"❌ Error: No encuentro el archivo: {INPUT_RAW}")
        return

    try:
        # Load Data
        print("📂 Leyendo Excel (esto puede tardar unos segundos)...")
        # Copy to temp to avoid lock
        import shutil
        TEMP = os.path.join(BASE_DIR, 'data', 'temp_process.xlsx')
        shutil.copy2(INPUT_RAW, TEMP)
        
        df = pd.read_excel(TEMP, sheet_name=SHEET_NAME)
        os.remove(TEMP)
        
        # Normalize Columns
        df.columns = [clean_column_name(c) for c in df.columns]
        
        # Identify Key Columns
        col_date = 'fecha'
        col_activity = 'Actividad'
        
        # Find Accessory Range
        try:
            # Flexible search for "Equipo GPS" and "Disco duro"
            start_col = next(c for c in df.columns if 'Equipo GPS' in c)
            end_col = next(c for c in df.columns if 'Disco duro' in c or 'disco duros' in c.lower())
            
            idx_start = df.columns.get_loc(start_col)
            idx_end = df.columns.get_loc(end_col)
            
            accessory_cols = df.columns[idx_start : idx_end + 1]
            print(f"✅ Rango de Materiales detectado: [{start_col}] ... [{end_col}] ({len(accessory_cols)} columnas)")
            
        except StopIteration:
            print("❌ Error: No encontré las columnas 'Equipo GPS' o 'Disco duro'.")
            print("Columnas disponibles:", list(df.columns))
            return

        # Filter Date
        df[col_date] = pd.to_datetime(df[col_date], errors='coerce')
        mask_date = (df[col_date] >= START_DATE) & (df[col_date] <= END_DATE)
        
        # Filter Activity
        mask_act = df[col_activity].astype(str).str.contains('Instala', case=False, na=False)
        
        df_filtered = df[mask_date & mask_act].copy()
        print(f"📉 Filas Filtradas: {len(df_filtered)} (Fecha + Instala)")

        # Process Each Row
        output_rows = []
        
        for idx, row in df_filtered.iterrows():
            materials = []
            
            for acc_col in accessory_cols:
                # EXCLUSION: Skip SONDAS (contains serial numbers, not quantities)
                if 'SONDA' in str(acc_col).upper():
                    continue

                qty = row[acc_col]
                # Validate Numeric
                if pd.notna(qty) and isinstance(qty, (int, float)):
                    if qty > 0:
                        # Validation 0-8
                        if qty > 8:
                            print(f"⚠️ Alerta: Fila {idx} tiene {qty} unidades de {acc_col}. (Posible error > 8)")
                        
                        materials.append(f"{acc_col}:{int(qty)}")
            
            if materials:
                output_rows.append({
                    'fecha': row[col_date],
                    'tipo_actividad': 'INSTALACION_' + str(row[col_activity]).upper().replace(' ', '_'), 
                    # Or just keep it generic "INSTALACION" as requested?
                    # User said: "la columna actividad solo la opcion instalar"
                    # But if we have materials, we technically have "INSTALACION_CUSTOM".
                    # Let's map it to 'INSTALACION' but the 'materiales_usados' is the payload.
                    'tipo_actividad': 'INSTALACION',
                    'cantidad_actividad': 1,
                    'materiales_usados': ", ".join(materials),
                    'cliente': str(row.get('Cliente', 'Unknown')) # Added Cliente
                })

        # Create Output DataFrame
        df_out = pd.DataFrame(output_rows)
        
        # Save
        df_out.to_excel(OUTPUT_TARGET, index=False)
        print(f"✨ Transformación Exitosa!")
        print(f"📄 Archivo generado: {OUTPUT_TARGET}")
        print(f"🔢 Total eventos procesados: {len(df_out)}")

    except Exception as e:
        print(f"💥 Error Crítico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
