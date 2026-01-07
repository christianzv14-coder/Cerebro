
import pandas as pd
import generate_unified_gantt as g

rb, eb = g.load_data()
df_rb = pd.DataFrame(rb)
df_eb = pd.DataFrame(eb)

report = []
report.append("# Desglose de Distribución de Trabajo - Enero 2026\n")

report.append("## 1. Resumen de Demanda Total")
report.append(f"- **Rabie (Servicios Fijos):** {df_rb['Qty'].sum()}")
report.append(f"- **Entel (Backlog):** {df_eb['Qty'].sum()}")
report.append(f"- **TOTAL GENERAL:** {df_rb['Qty'].sum() + df_eb['Qty'].sum()}\n")

report.append("## 2. Capacidad y Asignación")
report.append("- **Regla de Negocio:** 1 técnico = 1 servicio por día (Máximo Realismo).")
report.append("- **Técnicos Internos:** 7 titulares (Luis, Efrain, Carlos, Wilmer, Fabian, Jimmy, Orlando).")
report.append("- **Slots Internos Disponibles (12 al 31 Ene):** 126 slots (18 días * 7 técnicos).")
report.append("- **Uso de Internos:** 100% (Todos los técnicos están ocupados todos los días).\n")

report.append("## 3. Detalle por Región (Backlog Entel)")
for _, row in df_eb.sort_values('Qty', ascending=False).iterrows():
    report.append(f"- **{row['City']}:** {row['Qty']} servicios (Prioridad {row['Priority']})")

report.append("\n## 4. Uso de Técnicos Externos")
report.append("- Debido al alto volumen (1408 servicios), se requieren técnicos externos.")
report.append("- **Servicios Externos:** 1282 (1408 - 126).")
report.append("- **Promedio de Externos Necesarios por Día:** ~71 técnicos adicionales diarios.\n")

report.append("## 5. Cobertura Temporal")
report.append("- El plan ahora cubre **TODO el mes hasta el 31 de Enero**.")
report.append("- No hay días libres; se trabaja de Lunes a Sábado aprovechando cada slot para reducir el backlog.")

with open('outputs/distribucion_detalle.md', 'w', encoding='utf-8') as f:
    f.write("\n".join(report))

print("[SUCCESS] Detailed report generated at outputs/distribucion_detalle.md")
