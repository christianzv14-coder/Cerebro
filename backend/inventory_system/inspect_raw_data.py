import pandas as pd
import shutil
import os

ORIGINAL = r"backend/inventory_system/data/ACTIVIDADES ANUALES(ACTIVIDADES_DIARIAS) (1).xlsx"
TEMP = r"backend/inventory_system/data/temp_read.xlsx"

try:
    shutil.copy2(ORIGINAL, TEMP)
    shutil.copy2(ORIGINAL, TEMP)
    
    xls = pd.ExcelFile(TEMP)
    print("Hojas encontradas:", xls.sheet_names)
    
    sheet_name = 'ACTIVIDADES ANUALES(ACTIVIDADES'
    df = pd.read_excel(TEMP, sheet_name=sheet_name, nrows=1)
    
    print("ALL COLUMNS:")
    print(list(df.columns))
    
    del df
    xls.close()
    
    # Cleanup
    try:
        os.remove(TEMP)
    except:
        pass
except Exception as e:
    print(e)
