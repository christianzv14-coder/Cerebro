import sqlite3
import os

db_path = r"c:\Users\chzam\OneDrive\Desktop\cerebro-patio\Cerebro\backend\sql_app.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, concept, amount, date FROM expenses ORDER BY id DESC LIMIT 20")
    rows = cursor.fetchall()
    print("Recent Expenses:")
    for row in rows:
        print(row)
    conn.close()
else:
    print(f"DB not found at {db_path}")
