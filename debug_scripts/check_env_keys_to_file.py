
import os

env_path = ".env"
with open("env_keys.txt", "w") as outfile:
    if os.path.exists(env_path):
        outfile.write(f"Reading {env_path}\n")
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    key, _ = line.split("=", 1)
                    outfile.write(f"{key}\n")
    else:
        outfile.write(".env not found\n")
