# ============================
# 6) COSTOS (2 GRÁFICOS)
#    Reglas:
#    - ILIMITADO: $5.874 c/u
#    - ENTEL / ENTEL GLOBAL / ENTEL MANAGER (NO ilimitado): $1.000 + $347 por cada MB sobre 30
#    - Resto compañías: $0
# ============================

st.markdown("---")
st.subheader("💰 Costos estimados por plan (según consumo MB)")

# ---- Detectar columna de plan/compañía (prioridad: SIM, luego L2) ----
plan_col = None
for c in ["SIM", "Sim", "sim", "L2", "l2", "Plan", "PLAN", "Operador", "OPERADOR", "Compañia", "Compañía", "Carrier", "Proveedor"]:
    if c in df_filtrado.columns:
        plan_col = c
        break

if plan_col is None or "Patente" not in df_filtrado.columns or "MB" not in df_filtrado.columns:
    st.warning("No encuentro columnas suficientes para costos. Requiero al menos: 'Patente', 'MB' y una columna tipo 'SIM' o 'L2' para el plan/compañía.")
else:
    # Normalizar MB
    df_cost_base = df_filtrado.copy()
    df_cost_base["MB"] = pd.to_numeric(df_cost_base["MB"], errors="coerce").fillna(0)

    # Tomar "plan" por patente (último registro por Fecha si existe, si no: primero no nulo)
    if "Fecha" in df_cost_base.columns:
        df_cost_base = df_cost_base.sort_values("Fecha")
        plan_por_patente = (
            df_cost_base.dropna(subset=[plan_col])
            .groupby("Patente")[plan_col]
            .last()
        )
    else:
        plan_por_patente = (
            df_cost_base.dropna(subset=[plan_col])
            .groupby("Patente")[plan_col]
            .first()
        )

    # MB total por patente (con filtros aplicados)
    mb_por_patente = df_cost_base.groupby("Patente", as_index=False)["MB"].sum().rename(columns={"MB": "MB_total"})

    # Unir plan + MB
    df_cost = mb_por_patente.set_index("Patente").join(plan_por_patente.rename("Plan")).reset_index()
    df_cost["Plan"] = df_cost["Plan"].fillna("").astype(str)
    df_cost["Plan_UP"] = df_cost["Plan"].str.upper()

    # Reglas de clasificación
    ENTEL_SET = {"ENTEL", "ENTEL GLOBAL", "ENTEL MANAGER"}

    df_cost["es_ilimitado"] = df_cost["Plan_UP"].str.contains("ILIMIT", na=False)  # ILIMITADO, ILIMITADA, etc.
    df_cost["es_entel"] = df_cost["Plan_UP"].isin(ENTEL_SET) | df_cost["Plan_UP"].str.startswith("ENTEL ")

    # Costo por patente
    # - ilimitado: 5874
    # - entel no ilimitado: 1000 + 347 * max(0, MB-30)
    # - resto: 0
    df_cost["MB_sobre_30"] = (df_cost["MB_total"] - 30).clip(lower=0)
    df_cost["costo"] = 0

    df_cost.loc[df_cost["es_ilimitado"], "costo"] = 5874

    mask_entel_limitado = (df_cost["es_entel"]) & (~df_cost["es_ilimitado"])
    df_cost.loc[mask_entel_limitado, "costo"] = 1000 + (df_cost.loc[mask_entel_limitado, "MB_sobre_30"] * 347)

    # ============================
    # GRÁFICO 1: COSTO TOTAL ENTEL LIMITADO vs ENTEL ILIMITADO
    # ============================
    total_entel_ilimitado = df_cost.loc[df_cost["es_entel"] & df_cost["es_ilimitado"], "costo"].sum()
    total_entel_limitado = df_cost.loc[df_cost["es_entel"] & (~df_cost["es_ilimitado"]), "costo"].sum()

    df_totales = pd.DataFrame({
        "Tipo": ["ENTEL LIMITADO", "ENTEL ILIMITADO"],
        "Costo_total_CLP": [total_entel_limitado, total_entel_ilimitado]
    })

    fig_costos_entel = px.bar(
        df_totales,
        x="Tipo",
        y="Costo_total_CLP",
        title="Costo total estimado: Entel Limitado vs Entel Ilimitado (según filtros activos)"
    )
    fig_costos_entel.update_layout(
        xaxis_title="Tipo de plan",
        yaxis_title="Costo total (CLP)"
    )
    st.plotly_chart(fig_costos_entel, use_container_width=True)

    # ============================
    # GRÁFICO 2: PATENTES NO ILIMITADAS con MB > 45
    #           + etiqueta "RECOMENDADO SUBIR A PLAN ILIMITADO"
    # ============================
    st.subheader("🚀 Patentes NO ilimitadas con consumo > 45 MB")
    df_over45 = df_cost[(~df_cost["es_ilimitado"]) & (df_cost["MB_total"] > 45)].copy()
    df_over45["Recomendación"] = "RECOMENDADO SUBIR A PLAN ILIMITADO"

    if df_over45.empty:
        st.success("No hay patentes NO ilimitadas sobre 45 MB con los filtros actuales.")
    else:
        df_over45 = df_over45.sort_values("MB_total", ascending=False)

        # Gráfico de barras por patente (consumo)
        fig_over45 = px.bar(
            df_over45,
            x="Patente",
            y="MB_total",
            hover_data=["Plan", "costo", "Recomendación"],
            title="Patentes NO ilimitadas con consumo > 45 MB (filtros activos)"
        )
        fig_over45.add_hline(
            y=45,
            line_dash="dot",
            annotation_text="Umbral 45 MB",
            annotation_position="top right"
        )
        fig_over45.update_layout(
            xaxis_title="Patente",
            yaxis_title="MB total"
        )
        st.plotly_chart(fig_over45, use_container_width=True)

        # Tabla ejecutiva (para acción)
        st.dataframe(
            df_over45[["Patente", "Plan", "MB_total", "costo", "Recomendación"]],
            use_container_width=True
        )
