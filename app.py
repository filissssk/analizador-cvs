import streamlit as st
import pdfplumber

# Título de la app
st.title("📄 Analizador de PDFs y CVs")
st.write("Sube un archivo PDF para extraer y analizar su contenido.")

# Subida de archivo
archivo_subido = st.file_uploader("Elige un archivo PDF", type="pdf")

if archivo_subido is not None:
    # Leer el PDF
    texto_completo = ""
    with pdfplumber.open(archivo_subido) as pdf:
        for pagina in pdf.pages:
            texto_completo += pagina.extract_text() + "\n"

    # Mostrar resultado
    st.subheader("Contenido extraído:")
    st.text_area("Texto del PDF", texto_completo, height=300)

    # Ejemplo de análisis básico
    st.subheader("📊 Análisis rápido")
    palabras = texto_completo.split()
    st.write(f"**Total de palabras:** {len(palabras)}")
    
    # Buscar palabras clave (útil para CVs)
    palabra_clave = st.text_input("Buscar palabra clave (ej. 'Python', 'Experiencia'):")
    if palabra_clave:
        coincidencias = texto_completo.lower().count(palabra_clave.lower())
        st.write(f"La palabra **'{palabra_clave}'** aparece **{coincidencias}** veces.")