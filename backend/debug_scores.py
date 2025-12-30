from app.services.sheets_service import get_technician_scores, get_sheet

print("--- DEBUGGING SCORES ---")
try:
    sheet = get_sheet()
    ws = sheet.worksheet("Puntajes")
    all_values = ws.get_all_values()
    print(f"Total rows in Puntajes: {len(all_values)}")
    if len(all_values) > 0:
        print(f"Headers: {all_values[0]}")
    
    # Try to find a technician
    techs = set()
    idx_tech = -1
    for i, h in enumerate(all_values[0]):
        if "tecn" in h.lower() or "técn" in h.lower():
            idx_tech = i
            break
    
    if idx_tech != -1:
        for row in all_values[1:]:
            if len(row) > idx_tech:
                techs.add(row[idx_tech])
        
        print(f"Found {len(techs)} technicians in sheet: {list(techs)[:5]}...")
        
        if techs:
            sample_tech = list(techs)[0]
            print(f"Testing fetch for: '{sample_tech}'")
            result = get_technician_scores(sample_tech)
            print("Result:", result)
    else:
        print("Could not find 'Técnico' column.")

except Exception as e:
    print(f"ERROR: {e}")
