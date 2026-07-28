import os
import io
import platform

# Detectar el sistema operativo
ES_WINDOWS = platform.system() == "Windows"

# Si estás localmente en tu ordenador Windows, utiliza tus rutas locales:
if ES_WINDOWS:
    # Ajustar directorio temporal local
    TEMP_DIR = r"C:\temp"
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    os.environ["TMP"] = TEMP_DIR
    os.environ["TEMP"] = TEMP_DIR

    import pytesseract
    # Rutas locales de tu ordenador
    pytesseract.pytesseract.tesseract_cmd = r'C:\Tesseract-OCR\tesseract.exe'
    POPPLER_PATH = r'C:\Users\MAÑANA\Desktop\Release-26.02.0-0\poppler-26.02.0\Library\bin'
else:
    # En Linux (Streamlit Cloud), Tesseract y Poppler ya están en el sistema global
    import pytesseract
    POPPLER_PATH = None

import pdfplumber
from pdf2image import convert_from_bytes

def extraer_texto_pdf(archivo_input):
    texto = ""

    # Obtener bytes del archivo subido
    if isinstance(archivo_input, str):
        with open(archivo_input, "rb") as f:
            bytes_data = f.read()
    else:
        archivo_input.seek(0)
        bytes_data = archivo_input.read()

    # 1. Extracción directa (PDFs digitales)
    try:
        with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
    except Exception as e:
        print(f"Error en extracción directa: {e}")

    # 2. OCR (PDFs de tipo imagen)
    if not texto.strip():
        try:
            print("PDF de tipo imagen detectado. Aplicando OCR...")
            
            # Si estamos en Linux (cloud), poppler_path es None y funciona automáticamente
            if POPPLER_PATH:
                paginas_img = convert_from_bytes(bytes_data, poppler_path=POPPLER_PATH)
            else:
                paginas_img = convert_from_bytes(bytes_data)

            for img in paginas_img:
                try:
                    texto += pytesseract.image_to_string(img, lang='spa') + "\n"
                except Exception:
                    texto += pytesseract.image_to_string(img) + "\n"

        except Exception as e:
            print(f"Error en OCR: {e}")

    return texto.strip()
