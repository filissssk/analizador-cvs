import streamlit as st
import pdfplumber

st.set_page_config(page_title="Analizador de CVs Múltiples", page_icon="📄")

st.title("📄 Analizador Múltiple de CVs en PDF")
st.write("Sube uno o varios archivos PDF para extraer y analizar su contenido.")

# Permitir subir múltiples archivos activando accept_multiple_files=True
archivos_pdf = st.file_uploader("Elige tus archivos PDF", type=["pdf"], accept_multiple_files=True)

if archivos_pdf:
    st.success(f"¡Se han subido {len(archivos_pdf)} archivo(s) correctamente!")
    
    # Recorremos cada uno de los archivos subidos
    for i, archivo in enumerate(archivos_pdf, start=1):
        # Crear un recuadro o pestaña expandible para cada PDF
        with st.expander(f"📄 Archivo {i}: {archivo.name}", expanded=False):
            texto_completo = ""
            
            with pdfplumber.open(archivo) as pdf:
                for pagina in pdf.pages:
                    texto_pagina = pagina.extract_text()
                    if texto_pagina:
                        texto_completo += texto_pagina + "\n"
            
            # Estadísticas rápidas por archivo
            palabras = texto_completo.split()
            
            col1, col2 = st.columns(2)
            col1.metric("Páginas", len(pdf.pages) if 'pdf' in locals() else 0)
            col2.metric("Total de palabras", len(palabras))
            
            # Mostrar el contenido extraído
            st.subheader("Texto extraído:")
            st.text_area(f"Contenido de {archivo.name}", texto_completo, height=200, key=f"text_{i}")
