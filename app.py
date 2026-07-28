import streamlit as st
import pdfplumber

st.set_page_config(page_title="Analizador de CVs Múltiples", page_icon="📄")

st.title("📄 Analizador Múltiple de CVs en PDF")
st.write("Sube varios archivos PDF y busca palabras clave para evaluar a los candidatos.")

# 1. Buscador global de palabras clave
palabra_clave = st.text_input("🔍 Escribe una palabra clave para buscar (ej. Python, Excel, Inglés):")

# 2. Cargador de múltiples archivos PDF
archivos_pdf = st.file_uploader("Elige tus archivos PDF", type=["pdf"], accept_multiple_files=True)

if archivos_pdf:
    st.success(f"¡Se han subido {len(archivos_pdf)} archivo(s) correctamente!")
    st.markdown("---")
    
    # Recorremos cada uno de los archivos subidos
    for i, archivo in enumerate(archivos_pdf, start=1):
        texto_completo = ""
        
        # Extraemos el texto del PDF
        with pdfplumber.open(archivo) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto_completo += texto_pagina + "\n"
        
        # Si el usuario escribió algo en el buscador, contamos las coincidencias
        coincidencias = 0
        if palabra_clave.strip():
            # Convertimos todo a minúsculas para que no importe si buscan "python" o "Python"
            coincidencias = texto_completo.lower().count(palabra_clave.strip().lower())
        
        # Título del recuadro expandible con el nombre del archivo
        titulo_expander = f"📄 {archivo.name}"
        if palabra_clave.strip():
            titulo_expander += f" — 🎯 Coincidencias de '{palabra_clave}': {coincidencias}"
            
        with st.expander(titulo_expander, expanded=False):
            # Estadísticas por archivo
            palabras = texto_completo.split()
            col1, col2, col3 = st.columns(3)
            col1.metric("Páginas", len(pdf.pages))
            col2.metric("Total palabras", len(palabras))
            col3.metric(f"Menciones de '{palabra_clave}'" if palabra_clave else "Búsqueda", coincidencias if palabra_clave else "N/A")
            
            # Contenido extraído
            st.subheader("Texto extraído:")
            st.text_area(f"Contenido de {archivo.name}", texto_completo, height=180, key=f"text_{i}")
