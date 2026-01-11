
# ==============================================================================
# CONFIGURACIÓN GLOBAL DEL SISTEMA DE INVENTARIO
# ==============================================================================

# NIVEL DE SERVICIO DESEADO
# Define la probabilidad de NO tener quiebre de stock.
# 0.95 = 95% de confianza (Z Score ~ 1.645)
SERVICE_LEVEL = 0.95

# LEAD TIME (Tiempo de Reposición)
# Tiempo promedio en SEMANAS que tarda un proveedor en entregar.
# TODO: Parametrizar esto por Proveedor/SKU en el futuro.
DEFAULT_LEAD_TIME_WEEKS = 2

# PERIODICIDAD
# Frecuencia de agregación de la demanda.
TIME_FREQUENCY = 'W-MON'  # Semanal, comenzando Lunes

# FORECASTING
# Cuántos periodos hacia el futuro predecir.
FORECAST_HORIZON_WEEKS = 12

# BOM (Bill of Materials) POR DEFECTO
# Estructura provisional para mapear actividades a consumo.
# En producción, esto debería venir de una DB maestra.
DEFAULT_BOM = {
    'INSTALACION': [
        {'sku': 'GPS_UNIT_STD', 'qty': 1.0},
        {'sku': 'SIMCARD_M2M', 'qty': 1.0},
        {'sku': 'CABLE_POWER', 'qty': 1.0},
        {'sku': 'PRECINTO', 'qty': 2.0}
    ],
    'REVISION': [
        # Asume consumo menor por reparaciones
        {'sku': 'CABLE_POWER', 'qty': 0.2}, # 20% de veces se cambia cable
        {'sku': 'PRECINTO', 'qty': 1.0}      # Siempre se rompe precinto
    ],
    'RETIRO': [
        # Retiro genera inventario re-utilizable (logística inversa)
        # Por ahora lo modelamos como consumo negativo O ignoramos?
        # User prompt dice: "Consumen inventario físico".
        # Retiro CONSUME insumos de retiro (cinta, etc) pero RECUPERA GPS.
        # Asumiremos solo consumo de insumos por ahora para simplificar riesgo de quiebre.
        {'sku': 'CINTA_AISLANTE', 'qty': 0.1}
    ]
}
