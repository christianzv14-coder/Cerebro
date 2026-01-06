
# Script to generate Vertical "Chile Strip" Heatmap Analysis

regions_ordered = [
    ("Arica y Parinacota", 39),
    ("Tarapacá", 64),
    ("Antofagasta", 269),
    ("Atacama", 61),
    ("Coquimbo", 59),
    ("Valparaíso", 91),
    ("Metropolitana de Santiago", 680),
    ("Libertador Gral. B. O'Higgins", 38),
    ("Maule", 65),
    ("Ñuble", 19),
    ("Biobío", 54),
    ("La Araucanía", 45),
    ("Los Ríos", 17),
    ("Los Lagos", 70),
    ("Aysén", 7),
    ("Magallanes", 4)
]

max_val = 680
min_val = 4

def get_color(val):
    # HSL: Red is 0. Yellow/Green is 120.
    # We want Heatmap: Yellow (low) to Red (high).
    # Hue: 50 (Yellow) -> 0 (Red).
    ratio = (val - min_val) / (max_val - min_val)
    hue = 50 - (50 * ratio)
    lightness = 70 - (20 * ratio) # Darker red for high density
    return f"hsl({hue}, 100%, {lightness}%)"

def get_width_pct(val):
    # Scale width slightly by value for emphasizing "Bulge" (Population centers)
    # Min width 60%, Max width 100%
    ratio = (val - min_val) / (max_val - min_val)
    return 60 + (40 * ratio)

html = """
<!DOCTYPE html>
<html>
<head>
<style>
    body { font-family: 'Segoe UI', sans-serif; background: #222; color: #fff; display: flex; justify-content: center; padding: 40px; }
    .map-container { width: 400px; text-align: center; }
    h1 { margin-bottom: 10px; font-weight: 300; letter-spacing: 2px; }
    .subtitle { font-size: 14px; color: #aaa; margin-bottom: 30px; }
    .region-block {
        margin: 2px auto;
        padding: 8px;
        border-radius: 4px;
        color: #000;
        font-weight: bold;
        font-size: 11px;
        text-shadow: 0 1px 0 rgba(255,255,255,0.4);
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        transition: transform 0.2s;
        cursor: pointer;
        position: relative;
    }
    .region-block:hover { transform: scale(1.05); z-index: 10; }
    .tooltip {
        display: none; position: absolute; left: 110%; top: 50%; transform: translateY(-50%);
        background: #fff; color: #000; padding: 5px 10px; border-radius: 4px;
        white-space: nowrap; font-size: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    .region-block:hover .tooltip { display: block; }
    
    .legend { margin-top: 30px; display: flex; justify-content: space-between; font-size: 10px; color: #aaa; }
    .gradient-bar { height: 10px; background: linear-gradient(to right, hsl(50,100%,70%), hsl(0,100%,50%)); border-radius: 5px; margin-top: 5px; }
</style>
</head>
<body>

<div class="map-container">
    <h1>CHILE HEATMAP</h1>
    <div class="subtitle">Distribución de Flota GPS por Geografía</div>
"""

for reg, val in regions_ordered:
    color = get_color(val)
    width = get_width_pct(val)
    
    # Special styling for RM to make it look "Dense"
    border = "2px solid #fff" if reg.startswith("Metropolitana") else "none"
    
    html += f"""
    <div class="region-block" style="background: {color}; width: {width}%; border: {border};">
        {reg}
        <div class="tooltip">📡 {val} GPS</div>
    </div>
    """

html += """
    <div class="legend">
        <span>Baja Densidad</span>
        <span>Alta Densidad (RM)</span>
    </div>
    <div class="gradient-bar"></div>
    <div style="margin-top: 20px; font-size: 12px; color: #888;">Ordenado Geográficamente (Norte a Sur)</div>
</div>

</body>
</html>
"""

with open("outputs/mapa_chile_visual.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Heatmap generated at outputs/mapa_chile_visual.html")
