import os
import io

# Configuración de directorio temporal limpio
TEMP_DIR = r"C:\temp"
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

os.environ["TMP"] = TEMP_DIR
os.environ["TEMP"] = TEMP_DIR

import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract

# 1. RUTA NUEVA Y LIMPIA DE TESSERACT
pytesseract.pytesseract.tesseract_cmd = r'C:\Tesseract-OCR\tesseract.exe'

# 2. RUTA DE POPPLER
POPPLER_PATH = r'C:\Users\MAÑANA\Desktop\Release-26.02.0-0\poppler-26.02.0\Library\bin'

def extraer_texto_pdf(archivo_input):
    texto = ""

    # Obtener bytes del archivo subido
    if isinstance(archivo_input, str):
        with open(archivo_input, "rb") as f:
            bytes_data = f.read()
    else:
        archivo_input.seek(0)
        bytes_data = archivo_input.read()

    # Intento 1: Texto nativo/digital
    try:
        with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
    except Exception as e:
        print(f"Error en extracción directa: {e}")

    # Intento 2: OCR si es un PDF escaneado o de tipo imagen
    if not texto.strip():
        try:
            print("PDF de tipo imagen detectado. Aplicando OCR...")
            paginas_img = convert_from_bytes(bytes_data, poppler_path=POPPLER_PATH)

            for img in paginas_img:
                try:
                    texto += pytesseract.image_to_string(img, lang='spa') + "\n"
                except Exception:
                    texto += pytesseract.image_to_string(img) + "\n"

        except Exception as e:
            print(f"Error en OCR: {e}")

    return texto.strip()