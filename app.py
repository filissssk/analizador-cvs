import streamlit as st
import pandas as pd
import base64
import json
from groq import Groq
from pdf_utils import extraer_texto_pdf

st.set_page_config(page_title="Analizado de CVs", page_icon=" ", layout="wide")

st.title("Selección Inteligente de CVs")
st.write("Analiza, evalúa y clasifica candidaturas con Inteligencia Artificial.")

# --- BARRA LATERAL ---
st.sidebar.header("🔑 Configuración de IA")
api_key = st.sidebar.text_input("Ingresa API Key:", type="password")

st.sidebar.header("Filtros de Selección")
puesto = st.sidebar.text_input("Puesto a evaluar:", value="", placeholder="Ej: Contable, Desarrollador, Comercial...")
exp_minima = st.sidebar.slider("Años de experiencia deseados:", 0, 10, 0)
palabras_input = st.sidebar.text_input("🔍 Requisitos / Palabras clave:", value="", placeholder="Ej: Python, Excel, Inglés...")

# --- EXTRAER DATOS DEL CV CON IA (SE EJECUTA 1 SOLA VEZ POR CV) ---
@st.cache_data(show_spinner=False)
def extraer_datos_cv_con_ia(texto_cv, api_key):
    try:
        client = Groq(api_key=api_key)
        
        prompt = f"""
        Eres un extractor de datos de Recursos Humanos.
        Analiza el siguiente texto de un currículum y extrae la información clave en JSON.

        Debes responder ÚNICAMENTE con un objeto JSON válido con esta estructura exactas:
        {{
            "nombre_candidato": "Nombre completo o 'No identificado'",
            "email": "email o 'No encontrado'",
            "telefono": "teléfono o 'No encontrado'",
            "anos_experiencia": número entero estimado de años de experiencia laboral total,
            "tiene_titulacion": true o false (si cuenta con estudios universitarios/superiores/grado/máster),
            "resumen_ejecutivo": "Un resumen breve de 2 frases sobre el perfil del candidato.",
            "habilidades_clave": ["lista", "de", "habilidades", "tecnologias", "idiomas"]
        }}

        TEXTO DEL CV:
        {texto_cv}
        """
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"}
        )
        
        return json.loads(chat_completion.choices[0].message.content)
        
    except Exception as e:
        st.error(f"Error al analizar con Groq: {e}")
        return None

# --- CÁLCULO DE SCORE INSTANTÁNEO EN LOCAL ---
def calcular_match_local(datos_ia, texto_cv, puesto_req, exp_req, requisitos_req):
    hay_filtros = bool(puesto_req.strip() or requisitos_req.strip() or exp_req > 0)
    
    # Si no hay ningún filtro introducido por el usuario -> 100%
    if not hay_filtros:
        return 100

    puntos = 0
    max_puntos = 0

    # 1. Puesto de trabajo (30 Puntos)
    if puesto_req.strip():
        max_puntos += 30
        puesto_palabras = [p.lower() for p in puesto_req.split() if len(p) > 2]
        menciones = sum(1 for p in puesto_palabras if p in texto_cv.lower())
        if menciones > 0:
            puntos += 30

    # 2. Experiencia (30 Puntos)
    if exp_req > 0:
        max_puntos += 30
        exp_candidato = datos_ia.get("anos_experiencia", 0)
        puntos += 30 * min(1.0, exp_candidato / exp_req)

    # 3. Palabras clave / Requisitos (40 Puntos)
    if requisitos_req.strip():
        max_puntos += 40
        req_lista = [r.strip().lower() for r in requisitos_req.split(",") if r.strip()]
        if req_lista:
            encontradas = sum(1 for r in req_lista if r in texto_cv.lower() or any(r in h.lower() for h in datos_ia.get("habilidades_clave", [])))
            puntos += 40 * (encontradas / len(req_lista))

    if max_puntos == 0:
        return 100

    return int((puntos / max_puntos) * 100)

def mostrar_pdf_preview(bytes_data, nombre_archivo="cv.pdf"):
    try:
        base64_pdf = base64.b64encode(bytes_data).decode('utf-8')
        
        # Enlace directo para abrir o descargar
        pdf_href = f'<a href="data:application/pdf;base64,{base64_pdf}" target="_blank" download="{nombre_archivo}" style="display:inline-block; padding:8px 16px; background-color:#4CAF50; color:white; text-decoration:none; border-radius:4px; margin-bottom:10px;">📄 Abrir / Descargar PDF en nueva pestaña</a>'
        st.markdown(pdf_href, unsafe_allow_html=True)
        
        # Visor embebido mejorado con HTML object
        pdf_display = f'<object data="data:application/pdf;base64,{base64_pdf}" type="application/pdf" width="100%" height="600px"><p>Tu navegador no soporta la vista previa integrada. Usa el botón de arriba para abrir el PDF.</p></object>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception:
        st.warning("No se pudo cargar la vista previa del PDF original.")
    

# --- CARGADOR DE ARCHIVOS ---
archivos_pdf = st.file_uploader("Sube los CVs en formato PDF", type=["pdf"], accept_multiple_files=True)

if archivos_pdf:
    if not api_key:
        st.warning("⚠️ Por favor, ingresa tu Groq API Key en la barra lateral para iniciar el análisis.")
    else:
        lista_candidatos = []
        
        for idx, archivo in enumerate(archivos_pdf):
            bytes_pdf = archivo.getvalue()
            texto_completo = extraer_texto_pdf(bytes_pdf)
            
            with st.spinner(f"Analizando [{idx+1}/{len(archivos_pdf)}] {archivo.name}..."):
                datos_ia = extraer_datos_cv_con_ia(texto_completo, api_key)
            
            if datos_ia:
                # Calcular la puntuación de forma ultra-rápida según los filtros actuales
                score = calcular_match_local(datos_ia, texto_completo, puesto, exp_minima, palabras_input)
                
                lista_candidatos.append({
                    "id": idx,
                    "Nombre Archivo": archivo.name,
                    "Candidato": datos_ia.get("nombre_candidato", "No identificado"),
                    "Puntuación (%)": score,
                    "Años Exp.": datos_ia.get("anos_experiencia", 0),
                    "Titulación": "Sí" if datos_ia.get("tiene_titulacion") else "No",
                    "Email": datos_ia.get("email", "No encontrado"),
                    "Teléfono": datos_ia.get("telefono", "No encontrado"),
                    "Resumen IA": datos_ia.get("resumen_ejecutivo", ""),
                    "Habilidades": ", ".join(datos_ia.get("habilidades_clave", [])),
                    "Texto": texto_completo,
                    "Bytes": bytes_pdf
                })

        if lista_candidatos:
            # Ordenar ranking por puntuación
            lista_candidatos = sorted(lista_candidatos, key=lambda x: x["Puntuación (%)"], reverse=True)

            # TABLA COMPARATIVA
            st.markdown("---")
            st.subheader("📊 Tabla Comparativa Generada por IA")
            
            df_exportar = pd.DataFrame(lista_candidatos).drop(columns=["id", "Texto", "Bytes"])
            df_editado = st.data_editor(df_exportar, width="stretch", num_rows="fixed")
            
            csv_data = df_editado.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar Reporte Completo (CSV)",
                data=csv_data,
                file_name="analisis_cv_ia.csv",
                mime="text/csv"
            )

            # DESGLOSE INDIVIDUAL
            st.markdown("---")
            st.subheader("Evaluación Detallada")
            
            for i, cand in enumerate(lista_candidatos, start=1):
                score = cand["Puntuación (%)"]
                badge = "🟢 TOP MATCH" if score >= 80 else ("🟡 POTENCIAL" if score >= 50 else "🔴 NO ENCAJA")

                with st.expander(f"#{i} {badge} | {score}% — {cand['Candidato']} ({cand['Nombre Archivo']})"):
                    st.progress(score / 100)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Email", cand["Email"])
                    col2.metric("Teléfono", cand["Teléfono"])
                    col3.metric("Experiencia IA", f"{cand['Años Exp.']} años")
                    col4.metric("Titulación", cand["Titulación"])
                    
                    st.write("**Resumen Ejecutivo de la IA:**")
                    st.info(cand["Resumen IA"])
                    
                    st.write(f"** Habilidades Detectadas:** {cand['Habilidades']}")
                    
                    tab_pdf, tab_texto = st.tabs(["👁️ Vista Previa del PDF", "📄 Texto Extraído"])
                    with tab_pdf:
                    mostrar_pdf_preview(cand["Bytes"], cand["Nombre Archivo"])
                    with tab_texto:
                        st.text_area("Texto bruto leído por la app", cand["Texto"], height=200, key=f"cv_text_{cand['id']}")
