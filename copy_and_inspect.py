
import pandas as pd
import shutil
import os

def copy_and_inspect():
    src = "c:/Users/chzam/OneDrive/Desktop/cerebro-patio/Cerebro/Detalle Entel.xlsx"
    dst = "c:/Users/chzam/OneDrive/Desktop/cerebro-patio/Cerebro/temp_entel_copy.xlsx"
    
    print(f"Copying {src} to {dst}...")
    try:
        shutil.copy(src, dst)
        print("Copy successful.")
        
        print("Reading copy...")
        df = pd.read_excel(dst, nrows=5)
        print("\n--- COLUMNS ---")
        for c in df.columns:
            print(f"'{c}'")
        print("\n--- FIRST 3 ROWS ---")
        print(df.head(3).to_string())
        
        # Cleanup
        os.remove(dst)
        print("Cleanup successful.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    copy_and_inspect()
