import streamlit as st
import re
import pandas as pd
from pdf_utils import extraer_texto_pdf

st.set_page_config(page_title="Analizador de CVs", page_icon="🚀", layout="wide")

st.title("Selección de Currículums")
st.write("Analiza, clasifica, extrae datos de contacto y exporta el ranking de los candidatos.")

# --- BARRA LATERAL ---
st.sidebar.header("Filtros de Selección")

# Desmarcado / Desactivado por defecto:
exp_minima = st.sidebar.slider("Años de experiencia deseados:", 0, 10, 0)
requiere_titulo = st.sidebar.checkbox("Valorar Titulación Universitaria / Estudios Superiores", value=False)
palabras_input = st.sidebar.text_input("🔍 Palabras clave (separadas por comas):", value="")

palabras_clave = [p.strip().lower() for p in palabras_input.split(",") if p.strip()]

# --- CARGADOR DE ARCHIVOS ---
archivos_pdf = st.file_uploader("Sube los CVs en formato PDF", type=["pdf"], accept_multiple_files=True)

# --- FUNCIONES DE EXTRACCIÓN INTELIGENTE ---
def extraer_datos_contacto(texto):
    # Regex para email
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', texto)
    email = email_match.group(0) if email_match else "No encontrado"
    
    # Regex para teléfono (formatos comunes)
    telefono_match = re.search(r'(\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}', texto)
    telefono = telefono_match.group(0) if telefono_match else "No encontrado"
    
    # Enlaces
    linkedin = "Sí" if "linkedin.com" in texto.lower() else "No"
    github = "Sí" if "github.com" in texto.lower() else "No"
    
    return email, telefono, linkedin, github

def extraer_experiencia(texto):
    patrones = [
        r'(\d+)\s*\+?\s*años?\s*de\s*exp',
        r'(\d+)\s*\+?\s*años?\s*en',
        r'exp[a-z]*\w*\s*:\s*(\d+)\s*años?',
        r'(\d+)\s*años?'
    ]
    anos_encontrados = []
    for patron in patrones:
        coincidencias = re.findall(patron, texto.lower())
        for c in coincidencias:
            if c.isdigit():
                anos_encontrados.append(int(c))
    return max(anos_encontrados) if anos_encontrados else 0

def detectar_titulo(texto):
    palabras_titulo = ["grado", "licenciatur", "ingenier", "máster", "master", "universidad", "técnico", "tecnico", "doctorado", "phd", "bachelor"]
    texto_lower = texto.lower()
    titulos_hallados = [p.capitalize() for p in palabras_titulo if p in texto_lower]
    return len(titulos_hallados) > 0, list(set(titulos_hallados))

# --- PROCESAMIENTO ---
if archivos_pdf:
    st.info(f"Procesando {len(archivos_pdf)} currículums...")
    
    lista_candidatos = []
    
    for archivo in archivos_pdf:
        # Llamada directa a nuestra función inteligente con OCR integrado
        texto_completo = extraer_texto_pdf(archivo)
        texto_lower = texto_completo.lower()
        
        # Extraer contacto y experiencia
        email, telefono, linkedin, github = extraer_datos_contacto(texto_completo)
        exp_detectada = extraer_experiencia(texto_completo)
        tiene_titulo, titulos_detectados = detectar_titulo(texto_completo)
        
        # CÁLCULO DE SCORE
        puntos_maximos = 0
        puntos_obtenidos = 0
        
        # 1. Experiencia (30%)
        puntos_maximos += 30
        if exp_minima > 0:
            puntos_obtenidos += 30 * min(1.0, exp_detectada / exp_minima)
        else:
            puntos_obtenidos += 30
            
        # 2. Titulación (20%)
        if requiere_titulo:
            puntos_maximos += 20
            if tiene_titulo:
                puntos_obtenidos += 20
                
        # 3. Palabras clave (50%)
        conteo_palabras = {}
        palabras_encontradas = 0
        if palabras_clave:
            puntos_maximos += 50
            for palabra in palabras_clave:
                if palabra in ["inglés", "ingles"]:
                    menciones = texto_lower.count("inglés") + texto_lower.count("ingles") + texto_lower.count("english")
                else:
                    menciones = texto_lower.count(palabra)
                
                conteo_palabras[palabra] = menciones
                if menciones > 0:
                    palabras_encontradas += 1
            
            puntos_obtenidos += 50 * (palabras_encontradas / len(palabras_clave))

        score_final = int((puntos_obtenidos / puntos_maximos) * 100) if puntos_maximos > 0 else 100
        
        # Guardar resultados
        lista_candidatos.append({
            "Nombre Archivo": archivo.name,
            "Puntuación (%)": score_final,
            "Años Exp.": exp_detectada,
            "Titulación": "Sí" if tiene_titulo else "No",
            "Email": email,
            "Teléfono": telefono,
            "LinkedIn": linkedin,
            "Conteo Palabras": conteo_palabras,
            "Texto": texto_completo
        })

    # --- ORDENAR POR RANKING (De mayor a menor score) ---
    lista_candidatos = sorted(lista_candidatos, key=lambda x: x["Puntuación (%)"], reverse=True)

    # --- SECCIÓN DE DESCARGA EXCEL/CSV ---
    st.markdown("---")
    st.subheader("📊 Tabla Comparativa y Exportación")
    
    # Crear DataFrame para la tabla
    df_exportar = pd.DataFrame(lista_candidatos).drop(columns=["Conteo Palabras", "Texto"])
    st.dataframe(df_exportar, width="stretch")
    
    # Botón para descargar CSV
    csv_data = df_exportar.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Reporte en CSV / Excel",
        data=csv_data,
        file_name="ranking_candidatos.csv",
        mime="text/csv"
    )

    # --- DESGLOSE INDIVIDUAL ---
    st.markdown("---")
    st.subheader("Ranking de Candidatos Detallado")
    
    for i, cand in enumerate(lista_candidatos, start=1):
        score = cand["Puntuación (%)"]
        
        if score >= 80:
            badge = "🟢 TOP CANDIDATO"
        elif score >= 50:
            badge = "🟡 POTENCIAL"
        else:
            badge = "🔴 BAJA POTENCIAL"

        with st.expander(f"#{i} {badge} | {score}% — {cand['Nombre Archivo']}"):
            st.progress(score / 100)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Email", cand["Email"])
            col2.metric("Teléfono", cand["Teléfono"])
            col3.metric("Exp. Estimada", f"{cand['Años Exp.']} años")
            col4.metric("Titulación", cand["Titulación"])
            
            if palabras_clave:
                st.write("**🎯 Desglose de Palabras Clave:**")
                cols = st.columns(len(palabras_clave))
                for idx, (kw, cant) in enumerate(cand["Conteo Palabras"].items()):
                    cols[idx % len(cols)].metric(f"'{kw}'", f"{cant} menciones")
            
            st.subheader("Texto completo del CV:")
            st.text_area("Contenido", cand["Texto"], height=120, key=f"cv_{i}")
