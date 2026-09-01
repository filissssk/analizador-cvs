def procesar_un_cv(archivo, idx, api_key):
    try:
        bytes_pdf = archivo.getvalue()
        texto_completo = extraer_texto_pdf(bytes_pdf)
        
        # SI EL PDF ESTÁ ESCANEADO O PDF_UTILS FALLA:
        if not texto_completo or not texto_completo.strip():
            st.error(f"❌ El archivo '{archivo.name}' no contiene texto extraíble (puede ser una imagen o PDF escaneado).")
            datos_ia = {}
        else:
            datos_ia = extraer_datos_cv_con_ia(texto_completo, api_key) or {}
        
        res = {
            "id": idx,
            "Nombre Archivo": archivo.name,
            "Candidato": datos_ia.get("candidato", "No identificado"),
            "Ubicación": datos_ia.get("ubicacion", "No especificada"),
            "Años Exp.": datos_ia.get("anos_exp", 0),
            "Desglose Experiencia": datos_ia.get("experiencias_desglosadas", []),
            "Máster": datos_ia.get("master", "No"),
            "Titulación": datos_ia.get("titulacion", "No"),
            "Email": datos_ia.get("email", "No encontrado"),
            "Teléfono": datos_ia.get("telefono", "No encontrado"),
            "Resumen IA": datos_ia.get("resumen", "Sin resumen disponible"),
            "Habilidades": str(datos_ia.get("habilidades", "")),
            "Texto": texto_completo if texto_completo else "SIN TEXTO EXTRAÍDO",
            "Bytes": bytes_pdf,
            "datos_raw_ia": datos_ia
        }
        return res

    except Exception as e:
        st.error(f"Error procesando {archivo.name}: {e}")
        return None
