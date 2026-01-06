
import os
import pandas as pd

def inspect_entel():
    dpath = "c:/Users/chzam/OneDrive/Desktop/cerebro-patio/Cerebro"
    print(f"Listing dir: {dpath}")
    
    files = os.listdir(dpath)
    target = None
    for f in files:
        if "Entel" in f and f.endswith(".xlsx"):
            print(f"Found: {f}")
            target = os.path.join(dpath, f)
            
    if target:
        print(f"Reading: {target}")
        try:
            df = pd.read_excel(target, nrows=15, header=None)
            with open("entel_rows.txt", "w", encoding='utf-8') as f:
                for i, row in df.iterrows():
                    f.write(f"Row {i}: {row.tolist()}\n")
            print("Rows written to entel_rows.txt")
            
        except Exception as e:
            print(f"Error reading: {e}")
    else:
        print("File not found via python listdir.")

if __name__ == "__main__":
    inspect_entel()
