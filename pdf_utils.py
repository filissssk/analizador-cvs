import os
import io
import platform
import streamlit as st

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


def extraer_texto_pdf(archivo_input):
    """
    Extrae texto de un PDF usando:
    1. pdfplumber (PDFs digitales)
    2. OCR con pytesseract (PDFs escaneados)
    SIN CACHE para evitar problemas con bytes.
    """
    print(f"    📖 Iniciando extracción de texto...")
    texto = ""

    try:
        # 1. Convertir input a bytes
        if isinstance(archivo_input, str):
            with open(archivo_input, "rb") as f:
                bytes_data = f.read()
        elif isinstance(archivo_input, bytes):
            bytes_data = archivo_input
        else:
            archivo_input.seek(0)
            bytes_data = archivo_input.read()

        print(f"    ✓ Bytes obtenidos ({len(bytes_data)} bytes)")

        # 2. Intentar extracción de texto directo (PDFs digitales)
        try:
            print(f"    📄 Intentando extracción con pdfplumber...")
            with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
                for i, page in enumerate(pdf.pages):
                    t = page.extract_text()
                    if t:
                        texto += t + "\n"
            
            if texto.strip():
                print(f"    ✓ pdfplumber extrajo {len(texto)} caracteres")
        except Exception as e:
            print(f"    ⚠️ pdfplumber falló: {e}")

        # 3. Intentar OCR (PDFs escaneados o imágenes)
        if not texto.strip():
            try:
                print(f"    🖼️ PDF de tipo imagen detectado. Aplicando OCR...")

                if POPPLER_PATH:
                    paginas_img = convert_from_bytes(bytes_data, poppler_path=POPPLER_PATH)
                else:
                    paginas_img = convert_from_bytes(bytes_data)

                print(f"    ✓ Convertidas {len(paginas_img)} páginas a imagen")

                for idx, img in enumerate(paginas_img):
                    try:
                        texto_pag = pytesseract.image_to_string(img, lang='spa')
                    except Exception as e_lang:
                        print(f"    ⚠️ OCR español falló, reintentando por defecto...")
                        texto_pag = pytesseract.image_to_string(img)
                    
                    if texto_pag:
                        texto += texto_pag + "\n"
                
                if texto.strip():
                    print(f"    ✓ OCR extrajo {len(texto)} caracteres")

            except Exception as e:
                print(f"    ❌ Error general en OCR: {e}")

        if not texto.strip():
            print(f"    ❌ NO se extrajo texto")
            return ""

        return texto.strip()

    except Exception as e:
        print(f"    ❌ EXCEPCIÓN en extraer_texto_pdf: {str(e)}")
        import traceback
        traceback.print_exc()
        return ""
