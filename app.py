import streamlit as st
import pandas as pd
import base64
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from groq import Groq
from pdf_utils import extraer_texto_pdf

st.set_page_config(page_title="Analizador de CVs Pro", page_icon="🧠", layout="wide")

# --- AJUSTE DE TAMAÑO DE LETRA EN MÉTRICAS ---
st.markdown("""
    <style>
    [data-testid="stMetricLabel"] { font-size: 13px !important; }
    [data-testid="stMetricValue"] { font-size: 16px !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🧠 Selección Inteligente de CVs")
st.write("Analiza, evalúa y clasifica candidaturas con Inteligencia Artificial.")

# --- BARRA LATERAL ---
st.sidebar.header("🔑 Configuración de IA")

api_key_secret = st.secrets.get("GROQ_API_KEY", "")
if api_key_secret:
    api_key = api_key_secret
    st.sidebar.success("✅ API Key cargada automáticamente")
else:
    api_key = st.sidebar.text_input("Ingresa tu Groq API Key:", type="password")

st.sidebar.header("🎯 Filtros de Selección")
puesto = st.sidebar.text_input("Puesto a evaluar:", value="", placeholder="Ej: Profesor de Marketing, Contable...")
ubicacion_input = st.sidebar.text_input("📍 Ubicación / Ciudad:", value="", placeholder="Ej: Murcia, Elche, Alicante...")
exp_minima = st.sidebar.slider("Años de experiencia deseados:", 0, 10, 0)
palabras_input = st.sidebar.text_input("🔍 Requisitos / Palabras clave / Titulación:", value="", placeholder="Ej: Máster, Python, Inglés...")


# --- EXTRAER DATOS DEL CV CON IA (1 SOLA VEZ CON CACHÉ) ---
@st.cache_data(show_spinner=False)
def extraer_datos_cv_con_ia(texto_cv, api_key):
    try:
        client = Groq(api_key=api_key)
        
        prompt = f"""
        Eres un extractor de datos de Recursos Humanos.
        Analiza el siguiente texto de un currículum y extrae la información clave en JSON.

        Debes responder ÚNICAMENTE con un objeto JSON válido con esta estructura exacta:
        {{
            "nombre_candidato": "Nombre completo o 'No identificado'",
            "email": "email o 'No encontrado'",
            "telefono": "teléfono o 'No encontrado'",
            "ubicacion_candidato": "Ciudad, provincia o dirección detectada o 'No especificada'",
            "anos_experiencia": número entero estimado de años de experiencia laboral total,
            "tiene_master": true o false (true si posee Máster, Postgrado o Maestría),
            "tiene_titulacion": true o false (estudios universitarios/superiores/grado),
            "experiencias_desglosadas": [
                {{
                    "puesto_empresa": "Nombre del puesto y/o empresa",
                    "duracion": "Duración o fechas (Ej: 2 años / 2020-2022)"
                }}
            ],
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


# --- CÁLCULO DE MATCH LOCAL ---
def calcular_match_local(datos_ia, texto_cv, puesto_req, ubicacion_req, exp_req, requisitos_req):
    hay_filtros = bool(puesto_req.strip() or ubicacion_req.strip() or requisitos_req.strip() or exp_req > 0)
    if not hay_filtros:
        return 100

    puntos = 0
    max_puntos = 0

    if puesto_req.strip():
        max_puntos += 30
        puesto_palabras = [p.lower() for p in puesto_req.split() if len(p) > 2]
        menciones = sum(1 for p in puesto_palabras if p in texto_cv.lower())
        if menciones > 0:
            puntos += 30

    if ubicacion_req.strip():
        max_puntos += 20
        ub_buscada = ubicacion_req.strip().lower()
        ub_detectada = datos_ia.get("ubicacion_candidato", "").lower()
        if ub_buscada in ub_detectada or ub_buscada in texto_cv.lower():
            puntos += 20

    if exp_req > 0:
        max_puntos += 25
        exp_candidato = datos_ia.get("anos_experiencia", 0)
        puntos += 25 * min(1.0, exp_candidato / exp_req)

    if requisitos_req.strip():
        max_puntos += 25
        req_lista = [r.strip().lower() for r in requisitos_req.split(",") if r.strip()]
        
        puntos_req = 0
        for r in req_lista:
            if "master" in r or "máster" in r:
                if datos_ia.get("tiene_master"):
                    puntos_req += 1
            elif r in texto_cv.lower() or any(r in h.lower() for h in datos_ia.get("habilidades_clave", [])):
                puntos_req += 1
                
        puntos += 25 * (puntos_req / len(req_lista))

    if max_puntos == 0:
        return 100

    return int((puntos / max_puntos) * 100)


def mostrar_pdf_preview(bytes_data, nombre_archivo="cv.pdf"):
    try:
        base64_pdf = base64.b64encode(bytes_data).decode('utf-8')
        pdf_href = f'<a href="data:application/pdf;base64,{base64_pdf}" target="_blank" download="{nombre_archivo}" style="display:inline-block; padding:8px 16px; background-color:#2e7d32; color:white; text-decoration:none; border-radius:6px; margin-bottom:12px; font-weight:bold;">📄 Abrir / Descargar PDF en nueva pestaña</a>'
        st.markdown(pdf_href, unsafe_allow_html=True)
        
        pdf_display = f'<object data="data:application/pdf;base64,{base64_pdf}" type="application/pdf" width="100%" height="600px"><p>Tu navegador no soporta la vista previa integrada. Usa el botón de arriba para abrir el PDF.</p></object>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception:
        st.warning("No se pudo cargar la vista previa del PDF original.")


# --- FUNCIÓN PARA PROCESAR UN SÓLO CV (PARA USAR EN PARALELO) ---
def procesar_un_cv(archivo, idx, api_key, puesto, ubicacion_input, exp_minima, palabras_input):
    bytes_pdf = archivo.getvalue()
    texto_completo = extraer_texto_pdf(bytes_pdf)
    datos_ia = extraer_datos_cv_con_ia(texto_completo, api_key)
    
    if datos_ia:
        score = calcular_match_local(datos_ia, texto_completo, puesto, ubicacion_input, exp_minima, palabras_input)
        return {
            "id": idx,
            "Nombre Archivo": archivo.name,
            "Candidato": datos_ia.get("nombre_candidato", "No identificado"),
            "Puntuación (%)": score,
            "Ubicación": datos_ia.get("ubicacion_candidato", "No especificada"),
            "Años Exp.": datos_ia.get("anos_experiencia", 0),
            "Desglose Experiencia": datos_ia.get("experiencias_desglosadas", []),
            "Máster": "Sí" if datos_ia.get("tiene_master") else "No",
            "Titulación": "Sí" if datos_ia.get("tiene_titulacion") else "No",
            "Email": datos_ia.get("email", "No encontrado"),
            "Teléfono": datos_ia.get("telefono", "No encontrado"),
            "Resumen IA": datos_ia.get("resumen_ejecutivo", ""),
            "Habilidades": ", ".join(datos_ia.get("habilidades_clave", [])),
            "Texto": texto_completo,
            "Bytes": bytes_pdf
        }
    return None


# --- CARGADOR DE ARCHIVOS ---
archivos_pdf = st.file_uploader("Sube los CVs en formato PDF", type=["pdf"], accept_multiple_files=True)

if archivos_pdf:
    if not api_key:
        st.warning("⚠️ Por favor, ingresa tu Groq API Key en la barra lateral para iniciar el análisis.")
    else:
        lista_candidatos = []
        
        # Barra de progreso para informar al usuario
        progreso = st.progress(0)
        estado_texto = st.empty()
        total_archivos = len(archivos_pdf)
        
        estado_texto.info(f"⚡ Analizando {total_archivos} CVs en paralelo...")
        
        # PROCESAMIENTO EN PARALELO HASTA 5 CVS AL MISMO TIEMPO
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(
                    procesar_un_cv, archivo, idx, api_key, puesto, ubicacion_input, exp_minima, palabras_input
                )
                for idx, archivo in enumerate(archivos_pdf)
            ]
            
            completados = 0
            for future in as_completed(futures):
                res = future.result()
                if res:
                    lista_candidatos.append(res)
                completados += 1
                progreso.progress(completados / total_archivos)
        
        progreso.empty()
        estado_texto.empty()

        if lista_candidatos:
            lista_candidatos = sorted(lista_candidatos, key=lambda x: x["Puntuación (%)"], reverse=True)

            # TABLA COMPARATIVA
            st.markdown("---")
            st.subheader("📊 Tabla Comparativa Generada por IA")
            
            cols_eliminar = ["id", "Texto", "Bytes", "Desglose Experiencia"]
            df_exportar = pd.DataFrame(lista_candidatos).drop(columns=[c for c in cols_eliminar if c in pd.DataFrame(lista_candidatos).columns])
            df_editado = st.data_editor(df_exportar, width="stretch", num_rows="fixed")
            
            csv_data = df_editado.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button(
                label="📥 Descargar Reporte Completo (CSV)",
                data=csv_data,
                file_name="analisis_cv_ia.csv",
                mime="text/csv"
            )

            # DESGLOSE INDIVIDUAL
            st.markdown("---")
            st.subheader("🏆 Evaluación Detallada")
            
            for i, cand in enumerate(lista_candidatos, start=1):
                score = cand["Puntuación (%)"]
                badge = "🟢 TOP MATCH" if score >= 80 else ("🟡 POTENCIAL" if score >= 50 else "🔴 NO ENCAJA")

                with st.expander(f"#{i} {badge} | {score}% — {cand['Candidato']} ({cand['Nombre Archivo']})"):
                    st.progress(score / 100)
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col1.metric("Email", cand["Email"])
                    col2.metric("Teléfono", cand["Teléfono"])
                    col3.metric("Ubicación", cand["Ubicación"])
                    col4.metric("Experiencia IA", f"{cand['Años Exp.']} años")
                    col5.metric("Máster", cand["Máster"])
                    
                    st.write("**🤖 Resumen Ejecutivo de la IA:**")
                    st.info(cand["Resumen IA"])
                    
                    st.write("**💼 Historial de Puestos / Experiencia Desglosada:**")
                    desglose = cand.get("Desglose Experiencia", [])
                    if desglose:
                        for exp in desglose:
                            puesto_emp = exp.get("puesto_empresa", "Puesto no especificado")
                            duracion = exp.
