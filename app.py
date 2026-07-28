import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="Filtro Inteligente de CVs", page_icon="⚡", layout="wide")

st.title("⚡ Filtro Inteligente y Analizador de CVs")
st.write("Sube varios CVs en PDF y aplica filtros de experiencia, titulación y múltiples palabras clave.")

# --- BARRA LATERAL: CONTROLES DE FILTRADO ---
st.sidebar.header("🎯 Requisitos Mínimos")

exp_minima = st.sidebar.slider("Años de experiencia mínimos:", 0, 10, 0)
requiere_titulo = st.sidebar.checkbox("Exigir Titulación Universitaria / Superior")

# Entrada para MÚLTIPLES palabras separadas por comas
palabras_input = st.sidebar.text_input("🔍 Palabras clave (separadas por comas):", placeholder="Ej: Python, SQL, Inglés")

# Procesamos la lista de palabras ingresadas
palabras_clave = [p.strip().lower() for p in palabras_input.split(",") if p.strip()]

# --- CARGADOR DE ARCHIVOS ---
archivos_pdf = st.file_uploader("Sube los CVs en formato PDF", type=["pdf"], accept_multiple_files=True)

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

# --- PROCESAMIENTO Y FILTRADO ---
if archivos_pdf:
    st.success(f"Cargados {len(archivos_pdf)} currículums. Aplicando filtros...")
    st.markdown("---")
    
    candidatos_aptos = 0
    
    for i, archivo in enumerate(archivos_pdf, start=1):
        texto_completo = ""
        
        with pdfplumber.open(archivo) as pdf:
            for pagina in pdf.pages:
                t = pagina.extract_text()
                if t:
                    texto_completo += t + "\n"
        
        texto_lower = texto_completo.lower()
        
        # Análisis de experiencia y título
        exp_detectada = extraer_experiencia(texto_completo)
        tiene_titulo, titulos_detectados = detectar_titulo(texto_completo)
        
        # Conteo individual para CADA palabra clave solicitada
        conteo_palabras = {}
        palabras_faltantes = []
        
        for palabra in palabras_clave:
            menciones = texto_lower.count(palabra)
            conteo_palabras[palabra] = menciones
            if menciones == 0:
                palabras_faltantes.append(palabra)
        
        # Cumple si la experiencia alcanza, si tiene título (si se exige) y si tiene TODAS las palabras clave
        cumple_exp = exp_detectada >= exp_minima
        cumple_titulo = True if not requiere_titulo else tiene_titulo
        cumple_kw = len(palabras_faltantes) == 0
        
        es_apto = cumple_exp and cumple_titulo and cumple_kw
        
        if es_apto:
            candidatos_aptos += 1
            
        estado_badge = "✅ APTO" if es_apto else "❌ NO CUMPLE REQUISITOS"
        
        with st.expander(f"{estado_badge} — {archivo.name} | Exp: ~{exp_detectada} años | Título: {'Sí' if tiene_titulo else 'No'}"):
            col1, col2 = st.columns(2)
            col1.metric("Años Exp. Estimados", f"{exp_detectada} años")
            col2.metric("¿Titulación Detectada?", "Sí" if tiene_titulo else "No")
            
            # Muestreo de palabras clave encontradas
            if palabras_clave:
                st.subheader("🎯 Desglose de Palabras Clave:")
                cols = st.columns(len(palabras_clave))
                for idx, (kw, cant) in enumerate(conteo_palabras.items()):
                    cols[idx % len(cols)].metric(f"'{kw}'", f"{cant} menciones")
                
                if palabras_faltantes:
                    st.error(f"⚠️ Faltan en este CV: {', '.join(palabras_faltantes)}")
                else:
                    st.success("✨ ¡Contiene todas las palabras clave buscadas!")
                    
            if tiene_titulo:
                st.info(f"🎓 **Educación detectada:** {', '.join(titulos_detectados)}")
                
            st.subheader("Texto completo del CV:")
            st.text_area("Contenido", texto_completo, height=150, key=f"cv_{i}")

    st.sidebar.markdown("---")
    st.sidebar.metric("Candidatos Aptos", f"{candidatos_aptos} de {len(archivos_pdf)}")
