import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date

# ============================
# CONFIGURACIÓN GENERAL
# ============================
st.set_page_config(
    page_title="Predictivo MB por Patente",
    page_icon="📊",
    layout="wide"
)

# ============================
# SISTEMA DE LOGIN
# ============================
USUARIO_CORRECTO = "Position"
CLAVE_CORRECTA = "101004"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Acceso Restricto - Panel MB Position GPS")

    usuario = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if usuario == USUARIO_CORRECTO and clave == CLAVE_CORRECTA:
            st.session_state.logged_in = True
            st.success("Acceso concedido.")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")

    st.stop()

# ============================
# PARÁMETROS GENERALES
# ============================
UMBRAL_MB = 30  # límite por patente

st.title("📊 Predictivo MB por Patente (Límite 30 MB)")
st.markdown("---")

# ============================
# CARGA DEL ARCHIVO
# ============================
@st.cache_data
def load_data():
    df0 = pd.read_excel("Reporte_exceso_reg.xlsx")
    if "Fecha" in df0.columns:
        df0["Fecha"] = pd.to_datetime(df0["Fecha"], errors="coerce")
    return df0

df = load_data()

# ============================
# WIDGETS DE FILTROS (SIDEBAR)
# ============================
st.sidebar.header("Filtros")

# ---- 1) RANGO DE FECHA ----
fecha_ini, fecha_fin = None, None
if "Fecha" in df.columns:
    min_date = df["Fecha"].min()
    max_date = df["Fecha"].max()

    if pd.notna(min_date) and pd.notna(max_date):
        rango_fecha = st.sidebar.date_input(
            "Rango de Fecha",
            (min_date.date(), max_date.date()),
            key="f_fecha"
        )

        if isinstance(rango_fecha, tuple):
            if len(rango_fecha) == 2:
                fecha_ini, fecha_fin = rango_fecha
            elif len(rango_fecha) == 1:
                fecha_ini = fecha_fin = rango_fecha[0]
        elif isinstance(rango_fecha, date):
            fecha_ini = fecha_fin = rango_fecha
else:
    rango_fecha = None

# ---- 2) CUENTA ----
cuentas_sel = []
if "Cuenta" in df.columns:
    opciones_cuenta = df["Cuenta"].dropna().unique().tolist()
    cuentas_sel = st.sidebar.multiselect(
        "Cuenta",
        opciones_cuenta,
        key="f_cuenta"
    )

# ============================
# 3) FILTROS EXTRA SOLO CATEGÓRICOS (SIN RANGOS)
#    - Dist GPS queda como filtro normal (si viene como texto será categórico)
#    - Se eliminan sliders/rangos para: L2, SIM, Cant. de Registros, Cant. de Alarmas, Tam Log, MB
# ============================
EXCLUDE_COLS = {"Fecha", "Cuenta", "Patente"}

NO_RANGOS = {
    "L2", "l2",
    "SIM", "Sim", "sim",
    "CANT. DE REGISTROS", "Cant. de Registros", "Cant. de registros",
    "CANT. DE ALARMAS", "Cant. de Alarmas", "Cant. de alarmas",
    "TAM LOG", "Tam Log", "tam log", "TAM_LOG", "Tam_Log",
    "MB", "mb",
}

filtros_cat = {}

for col in df.columns:
    if col in EXCLUDE_COLS:
        continue

    s = df[col]

    # Categóricos
    if pd.api.types.is_object_dtype(s) or pd.api.types.is_categorical_dtype(s) or pd.api.types.is_bool_dtype(s):
        opciones = s.dropna().astype(str).unique().tolist()
        if not opciones:
            continue

        seleccion = st.sidebar.multiselect(
            col,
            sorted(opciones),
            key=f"f_cat_{col}"
        )
        if seleccion:
            filtros_cat[col] = seleccion

    # Numéricos que quieres SIN rangos: se filtran por selección exacta (multiselect)
    elif col in NO_RANGOS:
        opciones = pd.to_numeric(s, errors="coerce").dropna().unique().tolist()
        if not opciones:
            continue
        opciones = sorted(opciones)

        seleccion = st.sidebar.multiselect(
            col,
            opciones,
            key=f"f_cat_num_{col}"
        )
        if seleccion:
            filtros_cat[col] = seleccion

# ============================
# APLICAR FILTROS (SIN PATENTE)
# ============================
df_filtrado = df.copy()

# Fecha
if fecha_ini is not None and fecha_fin is not None and "Fecha" in df_filtrado.columns:
    mask_fecha = (
        (df_filtrado["Fecha"].dt.date >= fecha_ini) &
        (df_filtrado["Fecha"].dt.date <= fecha_fin)
    )
    df_filtrado = df_filtrado[mask_fecha]

# Cuenta
if cuentas_sel and "Cuenta" in df_filtrado.columns:
    df_filtrado = df_filtrado[df_filtrado["Cuenta"].isin(cuentas_sel)]

# Otros filtros categóricos / numéricos exactos
for col, valores in filtros_cat.items():
    if col not in df_filtrado.columns:
        continue

    if col in NO_RANGOS:
        df_filtrado[col] = pd.to_numeric(df_filtrado[col], errors="coerce")
        df_filtrado = df_filtrado[df_filtrado[col].isin(valores)]
    else:
        df_filtrado = df_filtrado[df_filtrado[col].astype(str).isin([str(v) for v in valores])]

# Base para opciones de patente
df_base_para_patente = df_filtrado.copy()

# ---- 4) PATENTE EN SIDEBAR ----
patente_sel = None
if "Patente" in df_base_para_patente.columns:
    patentes_disponibles = (
        df_base_para_patente["Patente"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    patentes_disponibles = sorted(patentes_disponibles)

    opciones_patente = ["(Todas)"] + patentes_disponibles
    patente_elegida = st.sidebar.selectbox(
        "Patente",
        opciones_patente,
        key="f_patente"
    )

    if patente_elegida != "(Todas)":
        patente_sel = patente_elegida
        df_filtrado["Patente"] = df_filtrado["Patente"].astype(str)
        df_filtrado = df_filtrado[df_filtrado["Patente"] == patente_sel]

# ============================
# 1) RESUMEN POR CUENTA
# ============================
st.subheader("📊 Resumen por Cuenta: Patentes sobre 30 MB")

resumen_patentes = pd.DataFrame()
resumen_cuenta = pd.DataFrame()

if {"Cuenta", "Patente", "Fecha", "MB"}.issubset(df_filtrado.columns):

    base = df_filtrado[["Cuenta", "Patente", "Fecha", "MB"]].copy()
    base["MB"] = pd.to_numeric(base["MB"], errors="coerce").fillna(0)
    base = base.dropna(subset=["Cuenta", "Patente", "Fecha"])

    if base.empty:
        st.info("No hay datos para calcular el resumen con los filtros actuales.")
    else:

        def resumen_por_patente(gr):
            gr = gr.sort_values("Fecha")
            mb = gr["MB"]
            consumo_total = mb.sum()
            dias = gr["Fecha"].dt.date.nunique()
            consumo_prom = (consumo_total / dias) if dias > 0 else 0

            hoy_local = gr["Fecha"].max()
            if hoy_local.month == 12:
                fin_mes_local = datetime(hoy_local.year, 12, 31)
            else:
                fin_mes_local = datetime(hoy_local.year, hoy_local.month + 1, 1) - timedelta(days=1)

            dias_rest = max(0, (fin_mes_local.date() - hoy_local.date()).days)
            proy = consumo_total + consumo_prom * dias_rest

            ya_pasada = consumo_total >= UMBRAL_MB
            pasara = (proy > UMBRAL_MB) and (consumo_total < UMBRAL_MB)

            dia_exceso_local = pd.NaT
            if consumo_prom > 0:
                if consumo_total >= UMBRAL_MB:
                    dia_exceso_local = hoy_local
                elif proy > UMBRAL_MB:
                    mb_faltante = UMBRAL_MB - consumo_total
                    dias_hasta_exceso = mb_faltante / consumo_prom
                    dia_exceso_local = hoy_local + timedelta(days=float(dias_hasta_exceso))

            return pd.Series({
                "consumo_total": consumo_total,
                "proy_final": proy,
                "ya_pasada": ya_pasada,
                "pasara": pasara,
                "dia_exceso": dia_exceso_local
            })

        resumen_patentes = (
            base
            .groupby(["Cuenta", "Patente"], as_index=False)
            .apply(resumen_por_patente)
        )

        if isinstance(resumen_patentes.index, pd.MultiIndex):
            resumen_patentes = resumen_patentes.reset_index(drop=True)

        resumen_cuenta = (
            resumen_patentes
            .groupby("Cuenta", as_index=False)
            .agg(
                patentes_total=("Patente", "nunique"),
                patentes_sobre_30_actual=("ya_pasada", "sum"),
                patentes_sobre_30_proyectado=("pasara", "sum"),
            )
        )

        resumen_cuenta = resumen_cuenta.sort_values(
            ["patentes_sobre_30_actual", "patentes_sobre_30_proyectado"],
            ascending=False
        )

        st.dataframe(resumen_cuenta, use_container_width=True)

        st.caption(
            "• **patentes_sobre_30_actual**: ya superaron los 30 MB en el período filtrado.  \n"
            "• **patentes_sobre_30_proyectado**: aún no pasan los 30 MB, pero se proyecta que los superen antes de fin de mes."
        )
else:
    st.warning("No se encontraron las columnas 'Cuenta', 'Patente', 'Fecha' y 'MB' necesarias para el resumen por cuenta.")

# ============================
# 2) TABLAS DETALLADAS: PATENTES EN RIESGO
# ============================
st.markdown("## 🔍 Detalle de Patentes en Riesgo")

if not resumen_patentes.empty:

    st.subheader("🚨 Patentes que YA pasaron los 30 MB")

    df_ya_pasadas = resumen_patentes[resumen_patentes["ya_pasada"] == True][
        ["Cuenta", "Patente", "consumo_total"]
    ].sort_values(["Cuenta", "consumo_total"], ascending=[True, False])

    if df_ya_pasadas.empty:
        st.success("Ninguna patente ha superado los 30 MB.")
    else:
        st.dataframe(df_ya_pasadas, use_container_width=True)

    st.subheader("⚠️ Patentes que POR PREDICCIÓN pasarán los 30 MB este mes")

    df_proyectadas = resumen_patentes[resumen_patentes["pasara"] == True].copy()

    if df_proyectadas.empty:
        st.success("Ninguna patente se proyecta que supere los 30 MB.")
    else:
        df_proyectadas["Día_exceso_mes"] = pd.to_datetime(df_proyectadas["dia_exceso"], errors="coerce").dt.day

        df_proyectadas_v = df_proyectadas[
            ["Cuenta", "Patente", "consumo_total", "proy_final", "Día_exceso_mes"]
        ].sort_values(["Cuenta", "proy_final"], ascending=[True, False])

        st.dataframe(df_proyectadas_v, use_container_width=True)
        st.caption("Columna **Día_exceso_mes**: día del mes estimado en que la patente superará los 30 MB.")
else:
    st.info("No se pudo generar el detalle porque el resumen está vacío.")

st.markdown("---")

# ============================
# 3) MB ACUM + RESTANTE PARA ESA PATENTE
# ============================
st.subheader("📊 MB Acum y MB Restante por Patente (límite 30 MB)")

if {"Patente", "MB"}.issubset(df_filtrado.columns) and patente_sel is not None:

    df_filtrado["MB"] = pd.to_numeric(df_filtrado["MB"], errors="coerce").fillna(0)

    df_pat = df_filtrado.groupby("Patente", as_index=False)["MB"].sum()
    df_pat["MB Acum"] = df_pat["MB"]
    df_pat["MB Restante"] = (UMBRAL_MB - df_pat["MB Acum"]).clip(lower=0)

    df_pat_sel = df_pat[df_pat["Patente"] == patente_sel]

    fig_stack = px.bar(
        df_pat_sel,
        x="Patente",
        y=["MB Acum", "MB Restante"],
        barmode="stack",
        title=f"MB Acumulado vs MB Restante para Patente {patente_sel} (capacidad {UMBRAL_MB} MB)",
    )

    fig_stack.update_layout(
        xaxis_title="Patente",
        yaxis_title="MB",
        xaxis_tickangle=0,
        legend_title_text=""
    )

    st.plotly_chart(fig_stack, use_container_width=True)
else:
    if patente_sel is None:
        st.info("Selecciona una patente en el filtro lateral para ver el gráfico de acumulado.")
    else:
        st.warning("No se encontraron las columnas necesarias 'Patente' y 'MB' para el gráfico de acumulado.")

st.markdown("---")

# ============================
# 4) PREDICTIVO PARA LA MISMA PATENTE
# ============================
st.subheader("🔮 Predictivo de Consumo por Patente")

if patente_sel is not None and {"Patente", "Fecha", "MB"}.issubset(df_filtrado.columns):

    df_p = df_filtrado[df_filtrado["Patente"] == patente_sel].copy()

    if df_p.empty:
        st.info("No hay datos para la patente seleccionada con los filtros actuales.")
    else:
        df_p["MB"] = pd.to_numeric(df_p["MB"], errors="coerce").fillna(0)
        df_p = df_p.dropna(subset=["Fecha"])
        df_p = df_p.sort_values("Fecha")

        df_p["Acum_real"] = df_p["MB"].cumsum()

        dias_distintos = df_p["Fecha"].dt.date.nunique()
        consumo_total = df_p["MB"].sum()
        consumo_prom = (consumo_total / dias_distintos) if dias_distintos > 0 else 0

        hoy = df_p["Fecha"].max()
        if hoy.month == 12:
            fin_mes = datetime(hoy.year, 12, 31)
        else:
            fin_mes = datetime(hoy.year, hoy.month + 1, 1) - timedelta(days=1)

        dias_restantes = max(0, (fin_mes.date() - hoy.date()).days)
        proyeccion_total = consumo_total + consumo_prom * dias_restantes

        dia_exceso = None
        if consumo_prom > 0:
            mb_faltante = UMBRAL_MB - consumo_total
            if mb_faltante <= 0:
                dia_exceso = hoy
            else:
                dias_hasta_exceso = mb_faltante / consumo_prom
                dia_exceso = hoy + timedelta(days=float(dias_hasta_exceso))

        fig_pred = go.Figure()

        fig_pred.add_trace(go.Scatter(
            x=df_p["Fecha"],
            y=df_p["Acum_real"],
            mode="lines+markers",
            name="Acumulado Real"
        ))

        if consumo_prom > 0 and dias_restantes > 0:
            fechas_proy = pd.date_range(hoy, fin_mes, freq="D")
            base_acum = df_p["Acum_real"].iloc[-1]
            valores_proy = base_acum + consumo_prom * (fechas_proy - hoy).days

            fig_pred.add_trace(go.Scatter(
                x=fechas_proy,
                y=valores_proy,
                mode="lines",
                name="Proyección",
                line=dict(dash="dash")
            ))

        fig_pred.add_hline(
            y=UMBRAL_MB,
            line=dict(color="red", dash="dot"),
            annotation_text=f"Límite {UMBRAL_MB} MB",
            annotation_position="top right"
        )

        fig_pred.update_layout(
            title=f"Predictivo de Consumo para Patente {patente_sel}",
            xaxis_title="Fecha",
            yaxis_title="MB Acumulado"
        )

        st.plotly_chart(fig_pred, use_container_width=True)

        st.markdown("### 📌 Resumen del Modelo Predictivo")
        st.write(f"**Consumo total actual:** {consumo_total:.2f} MB")
        st.write(f"**Consumo diario promedio:** {consumo_prom:.2f} MB/día")
        st.write(f"**MB proyectado al fin de mes:** {proyeccion_total:.2f} MB")

        if consumo_prom == 0:
            st.info("No hay suficiente variación de consumo para proyectar tendencia.")
        else:
            if proyeccion_total > UMBRAL_MB:
                if dia_exceso is not None:
                    st.error(
                        f"⚠️ Se proyecta que la patente superará los 30 MB este mes. "
                        f"Día estimado de sobreconsumo: **{dia_exceso.date()}** "
                        f"(día {dia_exceso.day} del mes)."
                    )
                else:
                    st.error("⚠️ Se proyecta que la patente superará los 30 MB este mes.")
            else:
                st.success("✅ No se proyecta que la patente supere el límite de 30 MB este mes.")
else:
    if patente_sel is None:
        st.info("Selecciona una patente en el filtro lateral para ver el análisis predictivo.")
    else:
        st.warning("No se encontraron las columnas 'Patente', 'Fecha' y 'MB' necesarias para el predictivo.")

# ============================
# 6) COSTOS (2 GRÁFICOS)
# ============================
st.markdown("---")
st.subheader("💰 Costos estimados por plan (según consumo MB)")

# Detectar columna de plan/compañía (prioridad: SIM, luego L2)
plan_col = None
for c in ["SIM", "Sim", "sim", "L2", "l2", "Plan", "PLAN", "Operador", "OPERADOR", "Compañia", "Compañía", "Carrier", "Proveedor"]:
    if c in df_filtrado.columns:
        plan_col = c
        break

if plan_col is None or "Patente" not in df_filtrado.columns or "MB" not in df_filtrado.columns:
    st.warning("No encuentro columnas suficientes para costos. Requiero al menos: 'Patente', 'MB' y una columna tipo 'SIM' o 'L2' para el plan/compañía.")
else:
    df_cost_base = df_filtrado.copy()
    df_cost_base["MB"] = pd.to_numeric(df_cost_base["MB"], errors="coerce").fillna(0)

    # Plan por patente: último registro por Fecha (si existe), si no: primero no nulo
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

    # MB total por patente
    mb_por_patente = df_cost_base.groupby("Patente", as_index=False)["MB"].sum().rename(columns={"MB": "MB_total"})

    df_cost = mb_por_patente.set_index("Patente").join(plan_por_patente.rename("Plan")).reset_index()
    df_cost["Plan"] = df_cost["Plan"].fillna("").astype(str)
    df_cost["Plan_UP"] = df_cost["Plan"].str.upper()

    ENTEL_SET = {"ENTEL", "ENTEL GLOBAL", "ENTEL MANAGER"}

    df_cost["es_ilimitado"] = df_cost["Plan_UP"].str.contains("ILIMIT", na=False)
    df_cost["es_entel"] = df_cost["Plan_UP"].isin(ENTEL_SET) | df_cost["Plan_UP"].str.startswith("ENTEL ")

    df_cost["MB_sobre_30"] = (df_cost["MB_total"] - 30).clip(lower=0)
    df_cost["costo"] = 0

    # ILIMITADO: 5874
    df_cost.loc[df_cost["es_ilimitado"], "costo"] = 5874

    # ENTEL (NO ilimitado): 1000 + 347 por MB sobre 30
    mask_entel_limitado = (df_cost["es_entel"]) & (~df_cost["es_ilimitado"])
    df_cost.loc[mask_entel_limitado, "costo"] = 1000 + (df_cost.loc[mask_entel_limitado, "MB_sobre_30"] * 347)

    # GRÁFICO 1: COSTO TOTAL ENTEL LIMITADO vs ENTEL ILIMITADO
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

    # GRÁFICO 2: PATENTES NO ILIMITADAS con MB > 45 + recomendación
    st.subheader("🚀 Patentes NO ilimitadas con consumo > 45 MB")
    df_over45 = df_cost[(~df_cost["es_ilimitado"]) & (df_cost["MB_total"] > 45)].copy()
    df_over45["Recomendación"] = "RECOMENDADO SUBIR A PLAN ILIMITADO"

    if df_over45.empty:
        st.success("No hay patentes NO ilimitadas sobre 45 MB con los filtros actuales.")
    else:
        df_over45 = df_over45.sort_values("MB_total", ascending=False)

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

        st.dataframe(
            df_over45[["Patente", "Plan", "MB_total", "costo", "Recomendación"]],
            use_container_width=True
        )
