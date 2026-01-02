import os

env_path = ".env"
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        lines = f.readlines()
    
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("DATABASE_URL="):
            new_lines.append("DATABASE_URL=sqlite:///./sql_app.db\n")
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        new_lines.append("DATABASE_URL=sqlite:///./sql_app.db\n")
        
    with open(env_path, "w") as f:
        f.writelines(new_lines)
    print("Updated DATABASE_URL to SQLite")
else:
    print(".env NOT FOUND")
