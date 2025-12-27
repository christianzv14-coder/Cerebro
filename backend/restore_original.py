import shutil
import os

def restore():
    print("--- RESTORING ORIGINAL EXCEL ---")
    src = "plantilla_backup.xlsx"
    dst = "plantilla_planificacion_v2.xlsx"
    
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"Restored {src} -> {dst}")
    else:
        print(f"ERROR: {src} not found!")

if __name__ == "__main__":
    restore()
