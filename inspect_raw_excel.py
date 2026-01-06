
import pandas as pd
import os

# We will try to read the temp file if it exists, otherwise the original
files = ["temp_data_source.xlsx", "../Noviembre.xlsx", "Noviembre.xlsx"]
target = None

for f in files:
    if os.path.exists(f):
        target = f
        break

if not target:
    # Try to copy if missing
    os.system('copy /Y "..\\\\Noviembre.xlsx" "temp_debug.xlsx"')
    target = "temp_debug.xlsx"

print(f"Inspecting file: {target}")

try:
    # Read without header to see raw structure
    df = pd.read_excel(target, header=None, nrows=10)
    print("\n--- RAW CONTENT (First 10 rows) ---")
    print(df.to_string())
except Exception as e:
    print(f"Error reading: {e}")
