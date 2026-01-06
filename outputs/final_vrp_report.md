# 🚀 Reporte Final de Optimización (VRP Nuclear)
## 💰 Desglose de Costos (Detallado)
| Ítem | Costo (UF) | % del Total |
| :--- | :--- | :--- |
| 👷 Sueldos (Fijo) | 109.76 | 5.5% |
| 📦 Materiales (Fijo) | 1381.60 | 69.2% |
| 🚌 Logística (Viajes/Hotel/Alm) | 180.09 | 9.0% |
| 🤝 Externalización | 79.62 | 4.0% |
| 🎁 Incentivos (Producción) | 246.21 | 12.3% |
| **TOTAL** | **1997.28** | **100%** |

---
## 📊 Diagrama de Gantt (Flujo de Movimiento)
Visualización de dónde está cada técnico día a día.
```mermaid
gantt
    title 🗓️ Planificación 24 Días
    dateFormat YYYY-MM-DD
    axisFormat %d
    section Wilmer
    Santiago :done, 2024-02-29, 1d
    Viña del Mar :active, 2024-03-01, 6d
    Santiago :done, 2024-03-07, 17d
    San Felipe :active, 2024-03-24, 1d
    section Fabian D.
    Santiago :done, 2024-02-29, 1d
    La Serena :active, 2024-03-01, 5d
    Viña del Mar :active, 2024-03-06, 1d
    Santiago :done, 2024-03-07, 16d
    San Fernando :active, 2024-03-23, 1d
    Talca :active, 2024-03-24, 1d
    section Efrain
    Santiago :done, 2024-02-29, 9d
    Concepcion :active, 2024-03-09, 5d
    Santiago :done, 2024-03-14, 9d
    Viña del Mar :active, 2024-03-23, 1d
    San Felipe :active, 2024-03-24, 1d
    section Jimmy
    Chillan :done, 2024-02-29, 1d
    San Fernando :active, 2024-03-01, 2d
    Rancagua :active, 2024-03-03, 4d
    Chillan :done, 2024-03-07, 3d
    Temuco :active, 2024-03-10, 6d
    Concepcion :active, 2024-03-16, 1d
    Chillan :done, 2024-03-17, 5d
    Los Angeles :active, 2024-03-22, 3d
    section Carlos
    Santiago :done, 2024-02-29, 4d
    San Antonio :active, 2024-03-04, 2d
    Viña del Mar :active, 2024-03-06, 1d
    Santiago :done, 2024-03-07, 8d
    San Fernando :active, 2024-03-15, 1d
    Talca :active, 2024-03-16, 2d
    San Fernando :active, 2024-03-18, 2d
    Santiago :done, 2024-03-20, 5d
    section Orlando
    Calama :done, 2024-02-29, 8d
    Iquique :active, 2024-03-08, 2d
    Antofagasta :active, 2024-03-10, 4d
    Calama :done, 2024-03-14, 11d
```

---
## 📦 Asignaciones Externas (Overflow)
| Ciudad | Cantidad (GPS) |
| :--- | :--- |
| Arica | 4 |
| Copiapo | 8 |
| Coyhaique | 1 |
| Osorno | 8 |
| Puerto Montt | 7 |
| Punta Arenas | 3 |

---
## 📅 Itinerario Detallado por Técnico

### 👷 Wilmer
| Día | Ciudad | Actividad (GPS Inst) |
| :--- | :--- | :--- |
| 0 | Santiago | 🏠 Inicio en Base |
| 1 | Viña del Mar | 🚛 (Terrestre) Viaje desde Santiago <br> 🛠️ Instala 2 |
| 2 | Viña del Mar | 🛠️ Instala 3 |
| 3 | Viña del Mar | 🛠️ Instala 3 |
| 4 | Viña del Mar | 🛠️ Instala 3 |
| 5 | Viña del Mar | 🛠️ Instala 3 |
| 6 | Viña del Mar | 🛠️ Instala 3 |
| 7 | Santiago | 🚛 (Terrestre) Viaje desde Viña del Mar |
| 8 | Santiago | 🏠 En Base (Disponible) |
| 9 | Santiago | 🏠 En Base (Disponible) |
| 10 | Santiago | 🏠 En Base (Disponible) |
| 11 | Santiago | 🏠 En Base (Disponible) |
| 12 | Santiago | 🏠 En Base (Disponible) |
| 13 | Santiago | 🏠 En Base (Disponible) |
| 14 | Santiago | 🏠 En Base (Disponible) |
| 15 | Santiago | 🏠 En Base (Disponible) |
| 16 | Santiago | 🏠 En Base (Disponible) |
| 17 | Santiago | 🏠 En Base (Disponible) |
| 18 | Santiago | 🛠️ Instala 3 |
| 19 | Santiago | 🛠️ Instala 3 |
| 20 | Santiago | 🛠️ Instala 3 |
| 21 | Santiago | 🏠 En Base (Disponible) |
| 22 | Santiago | 🛠️ Instala 3 |
| 23 | Santiago | 🛠️ Instala 3 |
| 24 | San Felipe | 🚛 (Terrestre) Viaje desde Santiago <br> 🛠️ Instala 2 |

### 👷 Fabian D.
| Día | Ciudad | Actividad (GPS Inst) |
| :--- | :--- | :--- |
| 0 | Santiago | 🏠 Inicio en Base |
| 1 | La Serena | 🚛 (Terrestre) Viaje desde Santiago <br> 🛠️ Instala 1 |
| 2 | La Serena | 🛠️ Instala 3 |
| 3 | La Serena | 🛠️ Instala 3 |
| 4 | La Serena | 🛠️ Instala 3 |
| 5 | La Serena | 🛠️ Instala 3 |
| 6 | Viña del Mar | 🚛 (Terrestre) Viaje desde La Serena <br> 🛠️ Instala 3 |
| 7 | Santiago | 🚛 (Terrestre) Viaje desde Viña del Mar |
| 8 | Santiago | 🛠️ Instala 3 |
| 9 | Santiago | 🛠️ Instala 3 |
| 10 | Santiago | 🛠️ Instala 3 |
| 11 | Santiago | 🛠️ Instala 3 |
| 12 | Santiago | 🛠️ Instala 3 |
| 13 | Santiago | 🛠️ Instala 3 |
| 14 | Santiago | 🏠 En Base (Disponible) |
| 15 | Santiago | 🛠️ Instala 3 |
| 16 | Santiago | 🛠️ Instala 3 |
| 17 | Santiago | 🛠️ Instala 3 |
| 18 | Santiago | 🛠️ Instala 3 |
| 19 | Santiago | 🛠️ Instala 3 |
| 20 | Santiago | 🛠️ Instala 3 |
| 21 | Santiago | 🏠 En Base (Disponible) |
| 22 | Santiago | 🛠️ Instala 3 |
| 23 | San Fernando | 🚛 (Terrestre) Viaje desde Santiago <br> 🛠️ Instala 1 |
| 24 | Talca | 🚛 (Terrestre) Viaje desde San Fernando <br> 🛠️ Instala 3 |

### 👷 Efrain
| Día | Ciudad | Actividad (GPS Inst) |
| :--- | :--- | :--- |
| 0 | Santiago | 🏠 Inicio en Base |
| 1 | Santiago | 🛠️ Instala 3 |
| 2 | Santiago | 🛠️ Instala 3 |
| 3 | Santiago | 🛠️ Instala 3 |
| 4 | Santiago | 🛠️ Instala 3 |
| 5 | Santiago | 🛠️ Instala 3 |
| 6 | Santiago | 🛠️ Instala 3 |
| 7 | Santiago | 🏠 En Base (Disponible) |
| 8 | Santiago | 🛠️ Instala 3 |
| 9 | Concepcion | 🚛 (Terrestre) Viaje desde Santiago <br> 🛠️ Instala 1 |
| 10 | Concepcion | 🛠️ Instala 3 |
| 11 | Concepcion | 🛠️ Instala 3 |
| 12 | Concepcion | 🛠️ Instala 3 |
| 13 | Concepcion | 🛠️ Instala 3 |
| 14 | Santiago | 🚛 (Terrestre) Viaje desde Concepcion |
| 15 | Santiago | 🛠️ Instala 3 |
| 16 | Santiago | 🛠️ Instala 3 |
| 17 | Santiago | 🛠️ Instala 3 |
| 18 | Santiago | 🛠️ Instala 3 |
| 19 | Santiago | 🛠️ Instala 3 |
| 20 | Santiago | 🛠️ Instala 3 |
| 21 | Santiago | 🏠 En Base (Disponible) |
| 22 | Santiago | 🛠️ Instala 3 |
| 23 | Viña del Mar | 🚛 (Terrestre) Viaje desde Santiago <br> 🛠️ Instala 3 |
| 24 | San Felipe | 🚛 (Terrestre) Viaje desde Viña del Mar <br> 🛠️ Instala 3 |

### 👷 Jimmy
| Día | Ciudad | Actividad (GPS Inst) |
| :--- | :--- | :--- |
| 0 | Chillan | 🏠 Inicio en Base |
| 1 | San Fernando | 🚛 (Terrestre) Viaje desde Chillan <br> 🛠️ Instala 3 |
| 2 | San Fernando | 🛠️ Instala 3 |
| 3 | Rancagua | 🚛 (Terrestre) Viaje desde San Fernando <br> 🛠️ Instala 1 |
| 4 | Rancagua | 🛠️ Instala 3 |
| 5 | Rancagua | 🛠️ Instala 3 |
| 6 | Rancagua | 🛠️ Instala 3 |
| 7 | Chillan | 🚛 (Terrestre) Viaje desde Rancagua |
| 8 | Chillan | 🏠 En Base (Disponible) |
| 9 | Chillan | 🏠 En Base (Disponible) |
| 10 | Temuco | 🚛 (Terrestre) Viaje desde Chillan <br> 🛠️ Instala 3 |
| 11 | Temuco | 🛠️ Instala 3 |
| 12 | Temuco | 🛠️ Instala 3 |
| 13 | Temuco | 🛠️ Instala 3 |
| 14 | Temuco | 🛌 Descanso / Traslado |
| 15 | Temuco | 🛠️ Instala 3 |
| 16 | Concepcion | 🚛 (Terrestre) Viaje desde Temuco <br> 🛠️ Instala 3 |
| 17 | Chillan | 🚛 (Terrestre) Viaje desde Concepcion |
| 18 | Chillan | 🛠️ Instala 1 |
| 19 | Chillan | 🛠️ Instala 3 |
| 20 | Chillan | 🛠️ Instala 3 |
| 21 | Chillan | 🏠 En Base (Disponible) |
| 22 | Los Angeles | 🚛 (Terrestre) Viaje desde Chillan <br> 🛠️ Instala 2 |
| 23 | Los Angeles | 🛠️ Instala 3 |
| 24 | Los Angeles | 🛠️ Instala 3 |

### 👷 Carlos
| Día | Ciudad | Actividad (GPS Inst) |
| :--- | :--- | :--- |
| 0 | Santiago | 🏠 Inicio en Base |
| 1 | Santiago | 🛠️ Instala 3 |
| 2 | Santiago | 🛠️ Instala 3 |
| 3 | Santiago | 🛠️ Instala 3 |
| 4 | San Antonio | 🚛 (Terrestre) Viaje desde Santiago <br> 🛠️ Instala 2 |
| 5 | San Antonio | 🛠️ Instala 3 |
| 6 | Viña del Mar | 🚛 (Terrestre) Viaje desde San Antonio <br> 🛠️ Instala 3 |
| 7 | Santiago | 🚛 (Terrestre) Viaje desde Viña del Mar |
| 8 | Santiago | 🛠️ Instala 3 |
| 9 | Santiago | 🛠️ Instala 3 |
| 10 | Santiago | 🛠️ Instala 3 |
| 11 | Santiago | 🛠️ Instala 3 |
| 12 | Santiago | 🛠️ Instala 3 |
| 13 | Santiago | 🛠️ Instala 3 |
| 14 | Santiago | 🏠 En Base (Disponible) |
| 15 | San Fernando | 🚛 (Terrestre) Viaje desde Santiago <br> 🛠️ Instala 3 |
| 16 | Talca | 🚛 (Terrestre) Viaje desde San Fernando <br> 🛠️ Instala 3 |
| 17 | Talca | 🛠️ Instala 3 |
| 18 | San Fernando | 🚛 (Terrestre) Viaje desde Talca <br> 🛠️ Instala 3 |
| 19 | San Fernando | 🛠️ Instala 3 |
| 20 | Santiago | 🚛 (Terrestre) Viaje desde San Fernando <br> 🛠️ Instala 3 |
| 21 | Santiago | 🏠 En Base (Disponible) |
| 22 | Santiago | 🛠️ Instala 3 |
| 23 | Santiago | 🛠️ Instala 3 |
| 24 | Santiago | 🛠️ Instala 3 |

### 👷 Orlando
| Día | Ciudad | Actividad (GPS Inst) |
| :--- | :--- | :--- |
| 0 | Calama | 🏠 Inicio en Base |
| 1 | Calama | 🏠 En Base (Disponible) |
| 2 | Calama | 🏠 En Base (Disponible) |
| 3 | Calama | 🏠 En Base (Disponible) |
| 4 | Calama | 🏠 En Base (Disponible) |
| 5 | Calama | 🏠 En Base (Disponible) |
| 6 | Calama | 🏠 En Base (Disponible) |
| 7 | Calama | 🏠 En Base (Disponible) |
| 8 | Iquique | 🚛 (Terrestre) Viaje desde Calama <br> 🛠️ Instala 1 |
| 9 | Iquique | 🛠️ Instala 3 |
| 10 | Antofagasta | 🚛 (Terrestre) Viaje desde Iquique <br> 🛠️ Instala 1 |
| 11 | Antofagasta | 🛠️ Instala 3 |
| 12 | Antofagasta | 🛠️ Instala 3 |
| 13 | Antofagasta | 🛠️ Instala 3 |
| 14 | Calama | 🚛 (Terrestre) Viaje desde Antofagasta |
| 15 | Calama | 🏠 En Base (Disponible) |
| 16 | Calama | 🏠 En Base (Disponible) |
| 17 | Calama | 🏠 En Base (Disponible) |
| 18 | Calama | 🏠 En Base (Disponible) |
| 19 | Calama | 🏠 En Base (Disponible) |
| 20 | Calama | 🏠 En Base (Disponible) |
| 21 | Calama | 🏠 En Base (Disponible) |
| 22 | Calama | 🏠 En Base (Disponible) |
| 23 | Calama | 🛠️ Instala 1 |
| 24 | Calama | 🛠️ Instala 3 |