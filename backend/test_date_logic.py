
import pandas as pd
from datetime import datetime

def test_date_parsing():
    # Simulate user data
    data = {
        'fecha': ['29-12-2025', '29/12/2025', '2025-12-29'],
        'ticket_id': [1, 2, 3]
    }
    df = pd.DataFrame(data)
    print("Original DF:")
    print(df)
    
    # Simulate backend logic (guessing what it is, need to confirm with view_file)
    try:
        # Usually we use pd.to_datetime
        df['fecha_parsed'] = pd.to_datetime(df['fecha'], dayfirst=True)
        print("\nParsed with dayfirst=True:")
        print(df['fecha_parsed'])
    except Exception as e:
        print(f"Parse Error: {e}")

if __name__ == "__main__":
    test_date_parsing()
