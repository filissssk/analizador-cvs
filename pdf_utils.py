import os
import io
import platform
import streamlit as st  # <-- 1. AÑADIDO IMPORT STREAMLIT

import pdfplumber
from pdf2image import convert_from_bytes

# Detectar el sistema operativo
ES_WINDOWS = platform.system() == "Windows"

# Configuración por SO
if ES_WINDOWS:
    TEMP_DIR = r"C:\temp"
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    os.environ["TMP"] = TEMP_DIR
    os.environ["TEMP"] = TEMP_DIR

    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Tesseract-OCR\tesseract.exe'
    POPPLER_PATH = r'C:\Users\MAÑANA\Desktop\Release-26.02.0-0\poppler-26.02.0\Library\bin'
else:
    import pytesseract
    POPPLER_PATH = None


# <-- 2. AÑADIDO EL DECORADOR DE CACHÉ AQUÍ
@st.cache_data(show_spinner=False)
def extraer_texto_pdf(archivo_input):
    texto = ""

    # 1. Lectura de los bytes del PDF
    if isinstance(archivo_input, str):
        with open(archivo_input, "rb") as f:
            bytes_data = f.read()
    elif isinstance(archivo_input, bytes):
        bytes_data = archivo_input
    else:
        archivo_input.seek(0)
        bytes_data = archivo_input.read()

    # 2. Intentar extracción de texto directo (PDFs digitales)
    try:
        with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
    except Exception as e:
        print(f"Error en extracción directa: {e}")

    # 3. Intentar OCR (PDFs escaneados o imagenes)
    if not texto.strip():
        try:
            print("PDF de tipo imagen detectado. Aplicando OCR...")

            if POPPLER_PATH:
                paginas_img = convert_from_bytes(bytes_data, poppler_path=POPPLER_PATH)
            else:
                paginas_img = convert_from_bytes(bytes_data)

            for img in paginas_img:
                try:
                    texto_pag = pytesseract.image_to_string(img, lang='spa')
                except Exception as e_lang:
                    print(f"Fallo idioma español en OCR ({e_lang}), reintentando por defecto...")
                    texto_pag = pytesseract.image_to_string(img)
                
                if texto_pag:
                    texto += texto_pag + "\n"

        except Exception as e:
            print(f"Error general en OCR: {e}")

    return texto.strip()
