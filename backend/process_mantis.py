
import pandas as pd
import os

# MAPPING CONFIG
# Mantis Column -> Planilla Column
COLUMN_MAPPING = {
    "ID": "ticket_id",
    "Categoría": "tipo_trabajo",
    "Dirección Visita": "direccion",
    "Patente Móvil": "patente",
    "Cuenta Position": "cliente",
    "Prioridad": "Prioridad",
    "Accesorios": "Accesorios",
    "Comuna Visita": "Comuna", 
    "Región Visita": "Region"
}

# Final desired columns
FINAL_COLUMNS = [
    "fecha",           
    "ticket_id",       
    "Prioridad",       
    "tipo_trabajo",    
    "Accesorios",      
    "direccion",       
    "Comuna",          
    "Region",          
    "tecnico_nombre",  
    "patente",         
    "cliente"          
]

def automator():
    print("--- MANTIS TO PLANILLA AUTOMATION ---")
    
    # Auto-detect latest 'Coordinados' file in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = script_dir
    
    if not os.path.exists(base_dir):
        print(f"Error: Directory '{base_dir}' does not exist.")
        return

    files = [f for f in os.listdir(base_dir) if f.startswith("Coordinados") and f.endswith(".xlsx")]
    
    if not files:
        print(f"Error: No files starting with 'Coordinados' found in '{base_dir}'.")
        return

    # Sort by modification time (newest first)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(base_dir, x)), reverse=True)
    input_file = os.path.join(base_dir, files[0])
    print(f"Using newest input file: {input_file}")
    
    output_file = os.path.join(base_dir, "plantilla_planificacion_v2.xlsx")

    try:
        df = pd.read_excel(input_file)
        print(f"Loaded {len(df)} rows from {input_file}")
        print("Original Headers:", df.columns.tolist())
        
        # 1. Rename columns
        # Check if columns exist before renaming to warn
        for src in COLUMN_MAPPING.keys():
            if src not in df.columns:
                print(f"WARNING: Source column '{src}' not found in Excel.")
        
        df_renamed = df.rename(columns=COLUMN_MAPPING)
        
        # 2. Add empty manual columns
        if "fecha" not in df_renamed.columns:
            df_renamed["fecha"] = ""
        if "tecnico_nombre" not in df_renamed.columns:
            df_renamed["tecnico_nombre"] = ""
            
        # 3. Select columns
        available = df_renamed.columns.tolist()
        selected_cols = []
        for col in FINAL_COLUMNS:
            if col in available:
                selected_cols.append(col)
            else:
                print(f"Warning: Destination column '{col}' missing. Adding empty.")
                df_renamed[col] = "" 
                selected_cols.append(col)
                
        final_df = df_renamed[selected_cols]
        
        # 4. Save
        final_df.to_excel(output_file, index=False)
        
        print(f"SUCCESS: Created '{output_file}' with {len(final_df)} rows.")
        print("Final Headers:", final_df.columns.tolist())
        
        # Auto-open the file
        print(f"Opening {output_file}...")
        try:
            os.startfile(output_file)
        except Exception as e:
            print(f"Could not auto-open file: {e}")
        
    except PermissionError:
        print(f"\nERROR DE PERMISO: No puedo escribir en '{output_file}'.")
        print(" -> POR FAVOR CIERRA EL ARCHIVO EXCEL SI LO TIENES ABIERTO.\n")
    except Exception as e:
        print(f"Error transforming file: {e}")

if __name__ == "__main__":
    automator()
