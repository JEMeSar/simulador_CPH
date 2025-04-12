import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
from datetime import date
import os

st.set_page_config(page_title="Simulador de Carrera Profesional", layout="wide")

# Encabezado
col1, col2, col3 = st.columns([1, 6, 1])
with col1:
    st.image("logo_izquierda.png", width=120)
with col2:
    st.title("Simulador de Carrera Profesional Horizontal")
with col3:
    st.image("logo_derecha.png", width=100)

# Sidebar inputs
st.sidebar.header("Configuración inicial")
n_grados = st.sidebar.number_input("Nº de grados de carrera (GDP)", min_value=1, max_value=10, value=4)


# Opciones de asignación por CD
modo_asignacion = st.sidebar.radio("Modo de asignación por CD", ["Manual", "Proporcional desde CD14 por grado"], index=1)
cd_niveles = list(range(14, 31))
asignaciones_por_cd = {grado: {} for grado in range(1, n_grados + 1)}

if modo_asignacion == "Manual":
    st.sidebar.subheader("Asignación fija por CD y Grado (manual)")
    for grado in range(1, n_grados + 1):
        st.sidebar.markdown(f"**Grado {grado}**")
        for cd in cd_niveles:
            key = f"asignacion_cd_{cd}_grado_{grado}"
            cantidad = st.sidebar.number_input(f"CD {cd} - Grado {grado}", min_value=0.0, value=0.0, step=100.0, key=key)
            asignaciones_por_cd[grado][cd] = cantidad
else:
    st.sidebar.subheader("Asignación proporcional desde CD14 por grado")
    incremento = st.sidebar.number_input("Incremento proporcional por CD", min_value=0.0, value=0.02, step=0.01)
    for grado in range(1, n_grados + 1):
        base = st.sidebar.number_input(f"Asignación base para CD14 - Grado {grado}", min_value=0.0, value=1000.0, step=100.0, key=f"base_grado_{grado}")
        for i, cd in enumerate(cd_niveles):
            asignaciones_por_cd[grado][cd] = round(base * ((1 + incremento) ** i), 2)


# PESTAÑAS PRINCIPALES
tab1, tab2, tab3 = st.tabs(["Simulación de carrera", "Distribución de plantilla", "Resultados"])

# -------- TAB 1: SIMULACIÓN DE CARRERA --------
with tab1:
    st.header("Años necesarios para cada grado (GDP)")
    años_por_grado = []
    for i in range(n_grados):
        años = st.number_input(f"Años para grado {i+1}", min_value=1, value=5, key=f"años_{i}")
        años_por_grado.append(años)

    st.subheader("Visualización de los tramos de carrera")
    x_vals = [0]
    y_vals = ["Inicio"]
    cumulative = 0
    for i, años in enumerate(años_por_grado):
        cumulative += años
        x_vals.append(cumulative)
        y_vals.append(f"Grado {i+1}")

    fig_timeline, ax_timeline = plt.subplots(figsize=(10, 2))
    colors = sns.color_palette("tab10", n_colors=len(x_vals) - 1)
    for i in range(1, len(x_vals)):
        ax_timeline.hlines(y=1, xmin=x_vals[i-1], xmax=x_vals[i], color=colors[i-1], linewidth=6)
        ax_timeline.text((x_vals[i-1]+x_vals[i])/2, 1.05, y_vals[i], ha='center', va='bottom', fontsize=9)
        ax_timeline.text(x_vals[i-1], 0.98, f"{x_vals[i-1]}", ha='center', va='top', fontsize=8)
        ax_timeline.text(x_vals[i], 0.98, f"{x_vals[i]}", ha='center', va='top', fontsize=8)

    ax_timeline.set_xlim(0, x_vals[-1] + 1)
    ax_timeline.set_ylim(0.95, 1.15)
    ax_timeline.axis('off')
    ax_timeline.set_title("Años por grado")
    st.pyplot(fig_timeline)

    img_path = "secuencia_temp.png"
    fig_timeline.savefig(img_path, bbox_inches="tight")

    st.header("Carga de datos de empleados")
    uploaded_file = st.file_uploader("Selecciona un archivo Excel con columnas: REF, fanti, CD", type=["xlsx"])

    empleados_por_cd_grado = {grado: {cd: 0 for cd in cd_niveles} for grado in range(1, n_grados + 1)}

    if uploaded_file:
        try:
            df_empleados = pd.read_excel(uploaded_file)
            df_empleados['fanti'] = pd.to_datetime(df_empleados['fanti'], errors='coerce')
            fecha_hoy = pd.Timestamp.today()
            df_empleados['antigüedad_años'] = (fecha_hoy - df_empleados['fanti']).dt.days // 365

            limites = [0]
            acumulado = 0
            for años in años_por_grado:
                acumulado += años
                limites.append(acumulado)

            def asignar_grado(antiguedad):
                for i in range(len(limites)-1):
                    if limites[i] <= antiguedad < limites[i+1]:
                        return i + 1
                return n_grados

            df_empleados['Grado'] = df_empleados['antigüedad_años'].apply(asignar_grado)
            resumen = df_empleados.groupby(['Grado', 'CD']).size().reset_index(name='Personas')
            for _, row in resumen.iterrows():
                grado = row['Grado']
                cd = row['CD']
                if grado in empleados_por_cd_grado and cd in empleados_por_cd_grado[grado]:
                    empleados_por_cd_grado[grado][cd] += row['Personas']

            st.success("Datos de empleados procesados y asignados automáticamente.")
            st.dataframe(df_empleados[['REF', 'fanti', 'CD', 'antigüedad_años', 'Grado']])
        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

# -------- TAB 2: DISTRIBUCIÓN DE PLANTILLA --------
with tab2:
    st.subheader("Distribución por CD y Grado (número de personas)")

    personas_por_cd_grado = {}
    total_personas = 0

    tabla_personas = pd.DataFrame(index=cd_niveles)
    for grado in range(1, n_grados + 1):
        tabla_personas[f"Grado {grado}"] = [empleados_por_cd_grado[grado].get(cd, 0) for cd in cd_niveles]
    tabla_personas["Total"] = tabla_personas.sum(axis=1)
    st.dataframe(tabla_personas)

    st.header("Edición manual del número de personas por CD en cada grado (GDP)")

    for grado in range(1, n_grados + 1):
        st.subheader(f"Grado {grado}")
        personas_por_cd_grado[grado] = {}
        columnas = st.columns(3)
        for idx, cd in enumerate(cd_niveles):
            col = columnas[idx % 3]
            key = f"cd_{cd}_grado_{grado}"
            default_val = empleados_por_cd_grado[grado][cd] if uploaded_file else 0
            with col:
                personas = st.number_input(f"CD {cd}", min_value=0, value=default_val, key=key)
            personas_por_cd_grado[grado][cd] = personas
            total_personas += personas

# -------- TAB 3: RESULTADOS --------
with tab3:
    st.header("Resultados")
    resultados = []
    unitarios = []
    coste_total = 0

    for grado, cds in personas_por_cd_grado.items():
        for cd, personas in cds.items():
            if personas > 0:
                asignacion_unitaria = asignaciones_por_cd.get(grado, {}).get(cd, 0)
                asignacion_total = personas * asignacion_unitaria
                coste_total += asignacion_total
                unitarios.append({
                    "Grado": grado,
                    "CD": cd,
                    "Asignación anual": asignacion_unitaria,
                    "Asignación mensual": asignacion_unitaria / 12
                })
                resultados.append({
                    "Grado": grado,
                    "CD": cd,
                    "Personas": personas,
                    "Asignación unitaria": asignacion_unitaria,
                    "Asignación total": asignacion_total
                })

    resultados_df = pd.DataFrame(resultados) if resultados else pd.DataFrame()

    if resultados:
        tabla_importes = pd.DataFrame(index=cd_niveles)
        for grado in range(1, n_grados + 1):
            tabla_importes[f"Grado {grado}"] = [
                personas_por_cd_grado[grado].get(cd, 0) * asignaciones_por_cd[grado].get(cd, 0) for cd in cd_niveles
            ]
        tabla_importes["Total"] = tabla_importes.sum(axis=1)

        st.subheader("Coste total del escenario")
        st.metric(label="Coste total (€)", value=f"{coste_total:,.2f}")

        unitarios_df = pd.DataFrame(unitarios)
        st.subheader("Importe unitario anual y mensual por CD y Grado (GDP)")
        st.dataframe(unitarios_df)

        st.subheader("Costes por CD y Grado (€)")
        st.dataframe(tabla_importes)

        if st.button("Generar informe PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.image("logo_izquierda.png", x=10, y=10, w=30)
            pdf.image("logo_derecha.png", x=170, y=10, w=30)

            pdf.ln(30)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Informe de Simulación de cotes de Carrera Profesional", ln=True, align='C')
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 10, f"Fecha: {date.today().strftime('%d/%m/%Y')}", ln=True)

            pdf.ln(5)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"Coste total del escenario: {coste_total:,.2f} euros", ln=True)
            pdf.cell(0, 10, f"Número total de empleados: {total_personas}", ln=True)

            pdf.ln(3)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Configuración del escenario", ln=True)
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, f"Número de grados: {n_grados}", ln=True)
            pdf.cell(0, 8, f"Años por grado: {', '.join(str(a) for a in años_por_grado)}", ln=True)
            pdf.cell(0, 8, f"Modo de asignación: {modo_asignacion}", ln=True)

            pdf.ln(3)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Importes para CD14 por grado", ln=True)
            pdf.set_font("Arial", '', 10)
            for grado in range(1, n_grados + 1):
                pdf.cell(0, 8, f"Grado {grado}: {asignaciones_por_cd[grado][14]:,.2f} euros", ln=True)

            pdf.ln(3)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 10, "Gráfico de secuencia acumulada", ln=True)
            pdf.image(img_path, w=180)

            pdf.add_page()
            pdf.image("logo_izquierda.png", x=10, y=10, w=30)
            pdf.image("logo_derecha.png", x=170, y=10, w=30)
            pdf.ln(30)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Importes asignados por CD y Grado (euros)", ln=True)
            col_widths = [15] + [18] * n_grados + [20]

            pdf.set_font("Arial", 'B', 9)
            pdf.cell(col_widths[0], 6, "CD", border=1)
            for grado in range(1, n_grados + 1):
                pdf.cell(col_widths[grado], 6, f"G{grado}", border=1)
            pdf.cell(col_widths[-1], 6, "Total", border=1)
            pdf.ln()
            pdf.set_font("Arial", '', 9)
            for index, row in tabla_importes.iterrows():
                pdf.cell(col_widths[0], 6, str(index), border=1)
                for i in range(n_grados):
                    pdf.cell(col_widths[i + 1], 6, f"{row[i]:,.2f}", border=1)
                pdf.cell(col_widths[-1], 6, f"{row[-1]:,.2f}", border=1)
                pdf.ln()

            pdf.add_page()
            pdf.image("logo_izquierda.png", x=10, y=10, w=30)
            pdf.image("logo_derecha.png", x=170, y=10, w=30)
            pdf.ln(30)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Coste unitario anual y mensual por CD y Grado:", ln=True)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(20, 6, "Grado", border=1)
            pdf.cell(20, 6, "CD", border=1)
            pdf.cell(40, 6, "Anual (euros)", border=1)
            pdf.cell(40, 6, "Mensual (euros)", border=1)
            pdf.ln()
            pdf.set_font("Arial", '', 9)
            for row in unitarios:
                pdf.cell(20, 6, str(row['Grado']), border=1)
                pdf.cell(20, 6, str(row['CD']), border=1)
                pdf.cell(40, 6, f"{row['Asignación anual']:,.2f}", border=1)
                pdf.cell(40, 6, f"{row['Asignación mensual']:,.2f}", border=1)
                pdf.ln()

            informe_path = "informe_simulacion.pdf"
            pdf.output(informe_path)
            with open(informe_path, "rb") as f:
                st.download_button("Descargar informe PDF", data=f, file_name=informe_path, mime="application/pdf")


