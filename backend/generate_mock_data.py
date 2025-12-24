import pandas as pd
from datetime import date

data = {
    'fecha': [date.today(), date.today(), date.today()],
    'ticket_id': ['TKT-001', 'TKT-002', 'TKT-003'],
    'tecnico_nombre': ['Juan Perez', 'Juan Perez', 'Maria Gonzalez'],
    'patente': ['AB-1234', 'CD-5678', 'EF-9012'],
    'cliente': ['Transportes Fast', 'Logistica Global', 'Chile Trucks'],
    'direccion': ['Av. Kennedy 111', 'Ruta 68 km 10', 'Panamericana Norte 5000'],
    'tipo_trabajo': ['Instalacion GPS', 'Revision Sensor', 'Desinstalacion']
}

df = pd.DataFrame(data)
df.to_excel('mock_data.xlsx', index=False)
print("mock_data.xlsx generated successfully.")
