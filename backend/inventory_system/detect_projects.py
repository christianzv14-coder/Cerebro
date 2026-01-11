
import pandas as pd
import numpy as np
import os
import sys
from backend.inventory_system import preprocessing, config

# Setup Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'input_actividades.xlsx')

def main():
    print("🚀 PROTOTIPO: Detección de Ciclos de Proyecto por Cliente")
    print("-" * 60)
    
    # 1. Load Data
    print("📂 Cargando Datos...")
    df_raw = pd.read_excel(DATA_FILE)
    df_raw['fecha'] = pd.to_datetime(df_raw['fecha'])
    
    # 2. Precompute Material Quantities per Row (Expand "Buzzer:12")
    # We need a clean DataFrame: [Date, SKU, Client, Qty]
    print("🔨 Procesando cantidades por cliente...")
    
    expanded_rows = []
    
    for idx, row in df_raw.iterrows():
        cli = str(row.get('cliente', 'Unknown')).strip()
        date = row['fecha'] # Use 'fecha' directly (Monday)
        mat_str = str(row.get('materiales_usados', ''))
        
        # Simple parse
        pieces = mat_str.split(',')
        for p in pieces:
            if ':' in p:
                try:
                    sku_name, qty_str = p.split(':')
                    sku = sku_name.strip()
                    qty = float(qty_str)
                    
                    expanded_rows.append({
                        'fecha': date,
                        'sku': sku,
                        'cliente': cli,
                        'cantidad': qty
                    })
                except:
                    pass
                    
    df_expanded = pd.DataFrame(expanded_rows)
    
    if df_expanded.empty:
        print("❌ Error: No se pudo expandir la data.")
        return

    # 3. Calculate Global SKU Averages (Baseline)
    # Average = Total Qty / Total Weeks in Dataset (approx 52?)
    # Or Average of Weekly Aggregates? Let's use Weekly Mean.
    
    # Aggregate by SKU/Week first
    df_sku_weekly = df_expanded.groupby(['sku', pd.Grouper(key='fecha', freq='W-MON')])['cantidad'].sum().reset_index()
    sku_stats = df_sku_weekly.groupby('sku')['cantidad'].mean().to_dict()
    
    print("\n📊 Promedios Globales por SKU (Threshold):")
    for s, v in list(sku_stats.items())[:5]: # Show top 5
        print(f"   - {s}: {v:.2f}")
        
    # 4. Detect Cycles per Client
    print("\n🕵️ Buscando Ciclos > 1 Semana...")
    
    # Aggregate by [SKU, Client, Week]
    df_client_weekly = df_expanded.groupby(['sku', 'cliente', pd.Grouper(key='fecha', freq='W-MON')])['cantidad'].sum().reset_index()
    
    detected_projects = []
    
    for sku in df_client_weekly['sku'].unique():
        threshold = sku_stats.get(sku, 0)
        if threshold == 0: continue
        
        df_sku = df_client_weekly[df_client_weekly['sku'] == sku]
        
        for cli in df_sku['cliente'].unique():
            # Get timeline for this client/sku sorted
            timeline = df_sku[df_sku['cliente'] == cli].sort_values('fecha')
            
            # Logic: Contiguous sequences > Threshold
            current_sequence = []
            
            for _, row in timeline.iterrows():
                qty = row['cantidad']
                date = row['fecha']
                
                if qty > threshold:
                    # Check continuity with previous item in sequence
                    if not current_sequence:
                        current_sequence.append({'date': date, 'qty': qty})
                    else:
                        last_date = current_sequence[-1]['date']
                        # Check if this week is exactly 1 week after last_date
                        # (Allowing for missing zero-weeks? The user said "time stable". 
                        # Usually "contiguous" implies 7 days diff. If there's a gap, it's a break.)
                        if (date - last_date).days <= 7:
                            current_sequence.append({'date': date, 'qty': qty})
                        else:
                            # Break in continuity -> Process previous sequence
                            if len(current_sequence) > 1:
                                detected_projects.append({
                                    'sku': sku,
                                    'client': cli,
                                    'start': current_sequence[0]['date'],
                                    'end': current_sequence[-1]['date'],
                                    'weeks': len(current_sequence),
                                    'total_qty': sum(x['qty'] for x in current_sequence)
                                })
                            current_sequence = [{'date': date, 'qty': qty}] # Start new
                else:
                     # Drop below threshold -> End sequence
                    if len(current_sequence) > 1:
                        detected_projects.append({
                            'sku': sku,
                            'client': cli,
                            'start': current_sequence[0]['date'],
                            'end': current_sequence[-1]['date'],
                            'weeks': len(current_sequence),
                             'total_qty': sum(x['qty'] for x in current_sequence)
                        })
                    current_sequence = []
            
            # Flush final sequence
            if len(current_sequence) > 1:
                detected_projects.append({
                    'sku': sku,
                    'client': cli,
                    'start': current_sequence[0]['date'],
                    'end': current_sequence[-1]['date'],
                    'weeks': len(current_sequence),
                    'total_qty': sum(x['qty'] for x in current_sequence)
                })

    # 5. Report Results
    if detected_projects:
        print(f"\n✅ Se detectaron {len(detected_projects)} Proyectos (Ciclos > 1 semana):")
        df_proj = pd.DataFrame(detected_projects)
        # Sort by Weeks Desc
        df_proj = df_proj.sort_values('weeks', ascending=False)
        
        print(df_proj[['sku', 'client', 'weeks', 'total_qty', 'start']].head(15).to_string())
    else:
        print("\n⚠️ No se detectaron proyectos con esta lógica (Todos fueron spikes de 1 semana o < Promedio).")

if __name__ == "__main__":
    main()
