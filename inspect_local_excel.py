import pandas as pd
import os

file_path = "Data_Streamlit.xlsx"
if not os.path.exists(file_path):
    print("File not found.")
else:
    try:
        # Load without header first to see raw structure
        df = pd.read_excel(file_path, header=None, nrows=5)
        print("RAW HEADERS/ROWS:")
        print(df.to_string())
        
        # Determine header row (usually 0)
        df = pd.read_excel(file_path, header=0, nrows=10)
        
        # Find Date Column
        date_cols = [c for c in df.columns if "fecha" in str(c).lower()]
        tech_cols = [c for c in df.columns if "tecnico" in str(c).lower()]
        
        print("\nDETECTED COLUMNS:")
        print(f"Date Cols: {date_cols}")
        print(f"Tech Cols: {tech_cols}")
        
        if date_cols:
            c = date_cols[0]
            print(f"\nSAMPLE DATES ({c}):")
            for val in df[c].head(5):
                print(f"Val: '{val}' (Type: {type(val)})")
                
        if tech_cols:
            c = tech_cols[0]
            print(f"\nSAMPLE TECHS ({c}):")
            for val in df[c].head(5):
                print(f"Val: '{val}'")
                
    except Exception as e:
        print(f"Error reading excel: {e}")
