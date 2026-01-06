import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

def generate_gantt():
    input_file = "outputs/detalle_rutas_granular_desglosado.xlsx"
    output_file = "outputs/carta_gantt_proyecto.html"
    
    print(f"Reading {input_file}...")
    df = pd.read_excel(input_file)
    
    # Project Start Date
    start_date_project = datetime(2025, 1, 13) # Next Monday assumption
    
    gantt_data = []
    
    # Process per Technician
    techs = df['Técnico'].unique()
    
    for tech in techs:
        tech_rows = df[df['Técnico'] == tech].reset_index(drop=True)
        current_date = start_date_project
        
        for idx, row in tech_rows.iterrows():
            city = row['Destino']
            days = row['Días']
            gps = row['GPS']
            
            # Skip initialization rows (Base -> Base with 0 days)
            # But keep "Retorno" to show end of project
            
            if days > 0:
                end_date = current_date + timedelta(days=days)
                
                # Activity entry
                gantt_data.append({
                    'Task': f"{city} ({int(gps)} GPS)",
                    'Start': current_date,
                    'Finish': end_date,
                    'Técnico': tech,
                    'City': city,
                    'Description': f"Instalación {int(gps)} GPS en {city}"
                })
                
                current_date = end_date
                
            elif "Retorno" in str(city):
                # Mark the return trip (maybe 1 day for visualization or just a milestone?)
                # Let's add a 1 day travel block for return
                end_date = current_date + timedelta(days=1)
                gantt_data.append({
                    'Task': "Retorno a Base",
                    'Start': current_date,
                    'Finish': end_date,
                    'Técnico': tech,
                    'City': 'Viaje',
                    'Description': f"Retorno a Base ({int(row['Km'])} km)"
                })
                current_date = end_date

    if not gantt_data:
        print("No data found for Gantt!")
        return

    df_gantt = pd.DataFrame(gantt_data)
    
    # Create Plotly Timeline
    fig = px.timeline(df_gantt, x_start="Start", x_end="Finish", y="Técnico", color="Técnico",
                      hover_data=['Description', 'Task'], text="Task",
                      title="Carta Gantt - Proyecto GPS (Inicio: 13-Ene-2025)")
    
    fig.update_yaxes(autorange="reversed") # Techs top to bottom
    fig.update_layout(
        xaxis_title="Fecha",
        showlegend=True,
        height=400 + (len(techs) * 50)
    )
    
    print(f"Saving Gantt to {output_file}...")
    fig.write_html(output_file)
    print("Done.")

if __name__ == "__main__":
    generate_gantt()
