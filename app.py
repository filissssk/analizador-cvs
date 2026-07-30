import streamlit as st
import pandas as pd
import base64
import json
from groq import Groq
from pdf_utils import extraer_texto_pdf

st.set_page_config(page_title="Analizador de CVs", page_icon=" ", layout="wide")

st.title("Selección Inteligente de CVs")
st.write("Analiza, evalúa y clasifica candidaturas con Inteligencia Artificial.")

# --- BARRA LATERAL ---
st.sidebar.header("Configuración de IA")
api_key = st.sidebar.text_input("Ingresa API Key:", type="password")

st.sidebar.header("Filtros de Selección")
puesto = st.sidebar.text_input("Puesto a evaluar:", value=" ")
exp_minima = st.sidebar.slider("Años de experiencia deseados:", 0, 10, 2)
palabras_input = st.sidebar.text_input("🔍 Requisitos / Palabras clave:", value=" ")

# --- FUNCIÓN CONECTADA A GROQ ---
def analizar_cv_con_ia(texto_cv, puesto_evaluar, exp_req, requisitos, api_key):
    try:
        client = Groq(api_key=api_key)
        
        prompt = f"""
        Eres un reclutador experto de Selección y Recursos Humanos.
        Analiza el siguiente texto extraído de un currículum para el puesto de: "{puesto_evaluar}".
        
        Criterios adicionales:
        - Años de experiencia deseados: {exp_req}
        - Requisitos/Habilidades requeridas: {requisitos}

        Debes responder ÚNICAMENTE con un objeto JSON válido (sin texto antes ni después) con la siguiente estructura exacta:
        {{
            "nombre_candidato": "Nombre del candidato o 'No identificado'",
            "email": "email o 'No encontrado'",
            "telefono": "teléfono o 'No encontrado'",
            "anos_experiencia": número entero con los años reales de experiencia estimados,
            "tiene_titulacion": true o false,
            "puntuacion_match": número entero entre 0 y 100 indicando qué tan bien encaja con el puesto,
            "resumen_ejecutivo": "Un resumen breve de 2-3 frases sobre los puntos fuertes y débiles del candidato.",
            "habilidades_clave": ["lista", "de", "habilidades", "detectadas"]
        }}

        Texto del CV:
        {texto_cv}
        """
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        
        respuesta_texto = chat_completion.choices[0].message.content
        return json.loads(respuesta_texto)
        
    except Exception as e:
        st.error(f"Error al analizar con Groq: {e}")
        return None

def mostrar_pdf_preview(bytes_data):
    base64_pdf = base64.b64encode(bytes_data).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="500" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# --- CARGADOR DE ARCHIVOS ---
archivos_pdf = st.file_uploader("Sube los CVs en formato PDF", type=["pdf"], accept_multiple_files=True)

if archivos_pdf:
    if not api_key:
        st.warning("⚠️ Por favor, ingresa tu Groq API Key en la barra lateral para iniciar el análisis.")
    else:
        st.info(f"Procesando {len(archivos_pdf)} currículums con la IA de Groq...")
        
        lista_candidatos = []
        
        for archivo in archivos_pdf:
            bytes_pdf = archivo.getvalue()
            texto_completo = extraer_texto_pdf(bytes_pdf)
            
            with st.spinner(f"Analizando {archivo.name}..."):
                datos_ia = analizar_cv_con_ia(texto_completo, puesto, exp_minima, palabras_input, api_key)
            
            if datos_ia:
                lista_candidatos.append({
                    "Nombre Archivo": archivo.name,
                    "Candidato": datos_ia.get("nombre_candidato", "No identificado"),
                    "Puntuación (%)": datos_ia.get("puntuacion_match", 0),
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
            lista_candidatos = sorted(lista_candidatos, key=lambda x: x["Puntuación (%)"], reverse=True)

            # TABLA EDITABLE Y EXPORTABLE
            st.markdown("---")
            st.subheader("📊 Tabla Comparativa Generada por IA")
            
            df_exportar = pd.DataFrame(lista_candidatos).drop(columns=["Texto", "Bytes"])
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
                    
                    st.write("**🤖 Resumen Ejecutivo de la IA:**")
                    st.info(cand["Resumen IA"])
                    
                    st.write(f"**💡 Habilidades Detectadas:** {cand['Habilidades']}")
                    
                    tab_pdf, tab_texto = st.tabs(["👁️ Vista Previa del PDF", "📄 Texto Extraído"])
                    with tab_pdf:
                        mostrar_pdf_preview(cand["Bytes"])
                    with tab_texto:
                        st.text_area("Texto bruto", cand["Texto"], height=150, key=f"cv_{i}")
