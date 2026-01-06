
import folium
from folium.plugins import HeatMap
import pandas as pd

def generate_map():
    # 1. Data Dictionary (Region: Count)
    data_dict = {
        'Antofagasta': 269,
        'Arica y Parinacota': 39,
        'Atacama': 61,
        'Aysén': 7,
        'Biobío': 54,
        'Coquimbo': 59,
        'La Araucanía': 45,
        "O'Higgins": 38,
        'Los Lagos': 70,
        'Los Ríos': 17,
        'Magallanes': 4,
        'Maule': 65,
        'Metropolitana': 680,
        'Ñuble': 19,
        'Tarapacá': 64,
        'Valparaíso': 91
    }

    # 2. Centroids Dictionary (Approx Lat/Lon for each Region Capital/Center)
    centroids = {
        'Arica y Parinacota': [-18.4746, -70.29792],
        'Tarapacá': [-20.21326, -70.15027],
        'Antofagasta': [-23.65236, -70.3954],
        'Atacama': [-27.36652, -70.3323],
        'Coquimbo': [-29.95332, -71.33947],
        'Valparaíso': [-33.04723, -71.61268],
        'Metropolitana': [-33.44889, -70.66926],
        "O'Higgins": [-34.17083, -70.74444],
        'Maule': [-35.4264, -71.65542],
        'Ñuble': [-36.60636, -72.10237],
        'Biobío': [-36.82699, -73.04977],
        'La Araucanía': [-38.73965, -72.6053],
        'Los Ríos': [-39.81422, -73.24589],
        'Los Lagos': [-41.4693, -72.94237],
        'Aysén': [-45.57524, -72.06619],
        'Magallanes': [-53.16383, -70.91706]
    }

    # 3. Create List of [Lat, Lon, Weight]
    heat_data = []
    
    # We replicate points to simulate "Density" better for the heatmap algorithm
    # OR we just pass the weight. Folium HeatMap supports 'weights'.
    # Format: [lat, lon, weight]
    
    for region, count in data_dict.items():
        # Match keys (some normalization needed)
        # Check standard keys
        key_found = region
        if "Aysén" in region: key_found = 'Aysén'
        if "General Carlos" in region: key_found = 'Aysén'
        if "Libertador" in region: key_found = "O'Higgins"
        if "Metropolitana" in region: key_found = 'Metropolitana'
        if "Magallanes" in region: key_found = 'Magallanes'

        if key_found in centroids:
            lat, lon = centroids[key_found]
            # HeatMap expects float weight.
            # To make it look "Hot" like the examples, we need to balance the radius and blur.
            # High counts (680) should burn red. Low counts (4) should be faint blue/green.
            heat_data.append([lat, lon, count])
        else:
            print(f"Warning: No centroid for {region}")

    # 4. Generate Map
    # Start centered on Chile
    m = folium.Map(location=[-35.6751, -71.543], zoom_start=5, tiles='CartoDB dark_matter')

    # Add HeatMap Layer
    HeatMap(
        heat_data,
        name='Mapa de Calor GPS',
        min_opacity=0.4,
        max_val=680, # Set to max count to scale colors properly
        radius=25,
        blur=15, 
        max_zoom=10, 
    ).add_to(m)

    # Add Circles (Bubbles) for clarity on exact numbers (Optional, but users like data)
    for row in heat_data:
        popup_text = f"GPS: {row[2]}"
        folium.CircleMarker(
            location=[row[0], row[1]],
            radius=5,
            color='white',
            weight=1,
            fill=True,
            fill_opacity=0.2,
            popup=popup_text
        ).add_to(m)

    out_path = "outputs/mapa_chile_real.html"
    m.save(out_path)
    print(f"Map generated: {out_path}")

if __name__ == "__main__":
    generate_map()
