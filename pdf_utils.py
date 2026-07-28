import os
import io
import platform
import streamlit as st

# Detectar el sistema operativo
ES_WINDOWS = platform.system() == "Windows"

if ES_WINDOWS:
    # Configuración Local para Windows
    TEMP_DIR = r"C:\temp"
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    os.environ["TMP"] = TEMP_DIR
    os.environ["TEMP"] = TEMP_DIR

    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Tesseract-OCR\tesseract.exe'
    POPPLER_PATH = r'C:\Users\MAÑANA\Desktop\Release-26.02.0-0\poppler-26.02.0\Library\bin'
else:
    # Configuración para Servidor Linux (Streamlit Cloud)
    import pytesseract
    POPPLER_PATH = None

import pdfplumber
from pdf2image import convert_from_bytes

# --- CACHÉ DE STREAMLIT ---
# Esta función guarda en memoria el resultado del OCR según los bytes del archivo.
# Si los bytes no cambian, ¡no vuelve a procesar el PDF!
@st.cache_data(show_spinner=False)
def extraer_texto_pdf(bytes_data):
    texto = ""

    # 1. Intentar extracción de texto directo (PDFs digitales)
    try:
        with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
    except Exception as e:
        print(f"Error en extracción directa: {e}")

    # 2. Intentar OCR (PDFs escaneados o imágenes)
    if not texto.strip():
        try:
            print("PDF de tipo imagen detectado. Aplicando OCR optimizado...")
            
            # Bajamos el dpi a 150 para duplicar la velocidad sin perder precisión
            if POPPLER_PATH:
                paginas_img = convert_from_bytes(bytes_data, dpi=150, poppler_path=POPPLER_PATH)
            else:
                paginas_img = convert_from_bytes(bytes_data, dpi=150)

            for img in paginas_img:
                try:
                    texto_pag = pytesseract.image_to_string(img, lang='spa')
                except Exception:
                    texto_pag = pytesseract.image_to_string(img)
                
                if texto_pag:
                    texto += texto_pag + "\n"

        except Exception as e:
            print(f"Error general en OCR: {e}")

    return texto.strip()
