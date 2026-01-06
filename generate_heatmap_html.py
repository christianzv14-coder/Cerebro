
# Script to generate HTML Heatmap
data = [
    ('Metropolitana de Santiago', 680),
    ('Antofagasta', 269),
    ('Valparaíso', 91),
    ('Los Lagos', 70),
    ('Maule', 65),
    ('Tarapacá', 64),
    ('Atacama', 61),
    ('Coquimbo', 59),
    ('Biobío', 54),
    ('La Araucanía', 45),
    ('Arica y Parinacota', 39),
    ("Libertador Gral. B. O'Higgins", 38),
    ('Ñuble', 19),
    ('Los Ríos', 17),
    ('Aysén', 7),
    ('Magallanes', 4)
]

max_val = 680

html_content = """
<!DOCTYPE html>
<html>
<head>
<style>
    body { font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; background-color: #f9f9f9; }
    .chart-container { width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    h2 { text-align: center; color: #333; margin-bottom: 30px; }
    .row { display: flex; align-items: center; margin-bottom: 12px; }
    .label { width: 250px; text-align: right; padding-right: 15px; font-weight: 600; color: #555; }
    .bar-container { flex-grow: 1; background-color: #eee; border-radius: 4px; overflow: hidden; }
    .bar { height: 24px; border-radius: 4px; transition: width 0.5s; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; color: white; font-size: 12px; font-weight: bold; }
    .value { width: 50px; padding-left: 10px; font-weight: bold; color: #333; }
</style>
</head>
<body>

<div class="chart-container">
    <h2>Distribución Regional de GPS (Entel)</h2>
"""

for region, count in data:
    # Calculate width percentage
    width_pct = (count / max_val) * 100
    # Calculate color intensity (Red)
    # Base red is 255, 0, 0. We want lighter redness for lower values.
    # Actually, let's use a fixed nice gradient or HSL.
    # High value = Dark Red. Low value = Light Salmon.
    opacity = 0.3 + (0.7 * (count / max_val))
    color = f"rgba(220, 53, 69, {opacity})"
    
    html_content += f"""
    <div class="row">
        <div class="label">{region}</div>
        <div class="bar-container">
            <div class="bar" style="width: {width_pct}%; background-color: {color};">
                {count if width_pct > 10 else ''}
            </div>
        </div>
        <div class="value">{count}</div>
    </div>
    """

html_content += """
    <div style="margin-top: 20px; text-align: center; font-size: 12px; color: #777;">
        Total Dispositivos: 1,513 | Fuente: Detalle Entel
    </div>
</div>

</body>
</html>
"""

with open("outputs/mapa_calor_gps.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("HTML generated at outputs/mapa_calor_gps.html")
