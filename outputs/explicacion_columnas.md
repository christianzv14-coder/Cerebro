
# 📘 Diccionario de Cálculos: Reporte de Costos

Este documento detalla la lógica exacta ("Fórmula del Sistema") utilizada para generar cada columna del Excel de Costos, junto con un ejemplo práctico.

---

## 🌎 Ejemplo de Referencia
Supongamos una **Ciudad "Antofagasta"** con:
- **Demanda:** 10 vehículos (todos de 1 GPS).
- **Asignación:** El técnico "Orlando" viaja allí, instala 8 GPS. Quedan 2 para externos.
- **Tiempos:** Orlando trabaja 3 días en la ciudad y duerme 2 noches allí.

---

## 🏗️ Desglose de Columnas

### 1. gps_total
- **Definición:** La demanda total de GPS a instalar en esa ciudad.
- **Fórmula:** `(Vehículos 1 GPS * 1) + (Vehículos 2 GPS * 2)`
- **Fuente:** Archivo `demanda_ciudades.xlsx`.

### 2. gps_internos
- **Definición:** Cantidad de GPS instalados por técnicos propios (Luis, Orlando, etc.) según el modelo óptimo.
- **Fórmula:** Suma de `plan['gps']` para todos los días que un técnico interno está en esa ciudad.
- **Ejemplo:** Si Orlando instala 3 el día 1, 3 el día 2, y 2 el día 3 -> `8`.

### 3. % Internos
- **Definición:** Porcentaje de cobertura propia.
- **Fórmula:** `gps_internos / gps_total`
- **Ejemplo:** `8 / 10 = 80%`.

### 4. Puntos (Incentivo)
- **Definición:** Pago variable al técnico por producción.
- **Fórmula:** `gps_internos * INCENTIVO_UF`
- **Valor Actual:** **1.04 UF** por GPS.
- **Ejemplo:** `8 GPS * 1.04 UF = 8.32 UF`.

### 5. sueldo
### 5. sueldo
- **Definición:** Costo del sueldo fijo mensual del técnico, asignado al proyecto.
- **Lógica Detallada:** El sueldo mensual del técnico se transforma a un costo diario (dividiendo por 30). Luego, se multiplica por los **24 días** de duración del operativo.
    - *Nota:* No es un pago extra al técnico, sino la imputación contable de "ocupar" a ese personal durante el proyecto.
- **Fórmula:** `(Sueldo Líquido Mes / 30) * 24`.

### 6. Almuerzos
- **Definición:** Subsidio diario de alimentación (Colación completa: Almuerzo + Cena).
- **Valor:** **0.5 UF** por día.
- **Regla de Pago:**
    1.  **Días Trabajados:** Se paga siempre que el técnico marque actividad laboral, esté en su base o fuera.
    2.  **Días Libres (Fuera de Base):** Si el técnico está en una ciudad distinta a su residencia (pernoctando), también recibe alimentación aunque sea domingo o feriado no trabajado.
- **Fórmula:** `(Días Trabajados + Días Descanso Fuera de Base) * 0.5 UF`.

### 7. Alojamientos (Viático)
- **Definición:** Costo exclusivo de pernoctación (Hotel/Cabaña).
- **Regla:** Se paga si `Ciudad Actual != Ciudad Base`.
- **Diferencia:** No incluye alimentación, ya que "Almuerzos" (0.5 UF) cubre la comida completa.
- **Valor:** **1.1 UF** / noche (ajustado desde 2.0).
- **Fórmula:** `(Días Pernoctando * 1.1 UF)`.

### 8. Viajes
- **Definición:** Costo de traslado Hacia o Desde la ciudad.
- **Fórmula:**
    - **Terrestre:** `(Km Distancia * 0.00342 UF/Km) + Peajes`.
    - **Aéreo:** Costo del pasaje (matriz `matriz_costo_avion.xlsx`).
- **Atribución:** El costo del viaje se carga a la **Ciudad de Destino**.

### 9. Traslado Interno
- **Definición:** Movilidad menor dentro de la ciudad (taxi/uber/bencina local).
- **Fórmula:** `Días Trabajados * 0.13 UF`.

### 10. gps_externos
- **Definición:** Lo que no alcanzaron a hacer los internos (Overflow).
- **Fórmula:** `gps_total - gps_internos`.
- **Ejemplo:** `10 - 8 = 2`.

### 11. pxq_uf (Costo Servicio Externo)
- **Definición:** Pago al proveedor externo por instalación.
- **Fórmula:** `gps_externos * Tarifa_PXQ_Ciudad`.
- **Fuente:** `costos_externos.xlsx`.

### 12. flete_uf
- **Definición:** Costo de envío de materiales (kits GPS) a la zona.
- **Regla:** Se cobra si hay instalaciones Externas **O** si hay instalaciones Internas en **Bases Remotas** (ej. Calama, Chillán) donde el técnico reside y requiere envío de stock.
- **Fórmula:** Valor fijo de `flete_ciudad.xlsx`.

### 13. Materiales_uf
- **Definición:** Costo del hardware (GPS, Cables, Relay).
- **Fórmula:** `(Vehiculos_1GPS * Costo_Kit1) + (Vehiculos_2GPS * Costo_Kit2)`.
- **Nota:** El material siempre lo paga el proyecto, es un costo hundido.

### 14. TOTAL PROYECTO
- **Definición:** Suma final de la fila.
- **Fórmula:** `Total Interno + Total Externo + Materiales`.

---

## 🔍 Ajuste de Cierre (Fila Final)
Dado que el Optimizador matemático trabaja con decimales de alta precisión y el Excel suma componentes redondeados, se agrega una fila final.
- **Fila "Ajuste de Cierre":** Es la diferencia `Costo_Objetivo_Optimizador - Suma_Excel`.
- **Propósito:** Garantizar que el reporte cuadre al 100% con el número auditado.
