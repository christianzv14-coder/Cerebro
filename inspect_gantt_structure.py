
import pandas as pd

def inspect():
    df = pd.read_excel('temp_gantt.xlsx', header=None, nrows=15)
    
    print("--- GANTH INSPECTION ---")
    for idx, row in df.iterrows():
        # Get non-null values
        vals = [f"Col{i}:{v}" for i, v in enumerate(row) if pd.notna(v)]
        if vals:
            print(f"Row {idx}: {vals}")

if __name__ == "__main__":
    inspect()
