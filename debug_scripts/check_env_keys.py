
import os

env_path = ".env"
if os.path.exists(env_path):
    print(f"Reading {env_path}")
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            if "=" in line:
                key, _ = line.split("=", 1)
                print(f"KEY FOUND: {key}")
else:
    print(".env not found")
