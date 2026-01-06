
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

def generate_heatmap_mpl():
    data = {
        'Región': [
            'Antofagasta', 'Arica y Parinacota', 'Atacama', 
            'Aysén del Gral. C. Ibáñez', 'Biobío', 'Coquimbo', 
            'La Araucanía', "Libertador Gral. B. O'Higgins", 'Los Lagos', 
            'Los Ríos', 'Magallanes y Antártica', 'Maule', 
            'Metropolitana de Santiago', 'Ñuble', 'Tarapacá', 'Valparaíso'
        ],
        'GPS Count': [
            269, 39, 61, 
            7, 54, 59, 
            45, 38, 70, 
            17, 4, 65, 
            680, 19, 64, 91
        ]
    }
    
    df = pd.DataFrame(data)
    df = df.sort_values('GPS Count', ascending=True) # Sort for chart
    
    # Setup Plot
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Create Colormap
    norm = mcolors.Normalize(vmin=df['GPS Count'].min(), vmax=df['GPS Count'].max())
    cmap = plt.cm.Reds
    
    # Plot Horizontal Bars
    bars = ax.barh(df['Región'], df['GPS Count'], color=cmap(norm(df['GPS Count'])))
    
    # Add Text Labels
    for bar in bars:
        width = bar.get_width()
        label_x_pos = width + 10 if width < 600 else width - 50
        color = 'black' if width < 600 else 'white'
        ax.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{int(width)}', 
                va='center', fontweight='bold', color=color)
        
    # Styling
    ax.set_title('Distribución de GPS por Región (Mapa de Calor)', fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel('Cantidad de Dispositivos', fontsize=12)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Add Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label('Intensidad (Cantidad)', rotation=270, labelpad=15)
    
    # Save
    out_path = "outputs/mapa_calor_gps_chile.png"
    plt.savefig(out_path, bbox_inches='tight', dpi=300)
    print(f"Heatmap saved to: {out_path}")

if __name__ == "__main__":
    generate_heatmap_mpl()
