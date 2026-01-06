
import pandas as pd

def find_id():
    fpath = "c:/Users/chzam/OneDrive/Desktop/cerebro-patio/Cerebro/Detalle Entel.xlsx"
    print(f"Scanning {fpath} for IDs...")
    
    df = pd.read_excel(fpath, header=None, nrows=20)
    
    found_col = None
    
    for col in df.columns:
        # Check first few non-null values
        sample = df[col].dropna().astype(str).tolist()
        for x in sample:
            if x.startswith("569") and len(x) >= 9:
                print(f"POTENTIAL ID FOUND in Column {col} (Index {df.columns.get_loc(col)})")
                print(f"Sample: {x}")
                found_col = col
                break
        if found_col is not None:
            break
            
    if found_col is None:
        print("NO ID COLUMN FOUND (No '569...' pattern detected).")
        # Dump all columns to debug
        print("Columns Dump:")
        for col in df.columns:
            print(f"Col {col}: {df[col].head(3).tolist()}")

if __name__ == "__main__":
    find_id()
