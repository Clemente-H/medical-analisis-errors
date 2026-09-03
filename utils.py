import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd
from datetime import datetime
import re
import time

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# --- Cache de posiciones de fila -------------------------------------------
# Cada navegación hacía 3 lecturas completas de la hoja (una por
# save_annotation, otra por update_user_progress y otra por
# get_user_annotations) más 2 escrituras. La API de Sheets permite ~60
# lecturas y ~60 escrituras por minuto POR PROYECTO, y todos los médicos
# comparten la misma service account: con dos o tres anotando en paralelo se
# llegaba al 429 RESOURCE_EXHAUSTED y la anotación se perdía. Además cada
# lectura traía la hoja entera, así que la app se ponía más lenta a medida que
# avanzaba la sesión.
#
# Guardamos en qué fila vive cada anotación para poder escribir directo. Las
# filas propias no se mueven: append siempre agrega al final y nadie borra
# filas, así que el cache sigue siendo válido durante toda la sesión.


def _annotation_key(username, pregunta_id, modelo):
    return f"{username}|{pregunta_id}|{modelo}"


def _build_row_index(all_values, username):
    """Mapa clave -> número de fila para las anotaciones del usuario."""
    row_index = {}

    for idx, row in enumerate(all_values[1:], start=2):  # Skip header
        if len(row) >= 4 and row[1] == username:
            row_index[_annotation_key(username, row[2], row[3])] = idx

    return row_index


def _row_from_append(response):
    """Fila en la que quedó un append_row, leída del updatedRange que
    devuelve la API (p.ej. "anotaciones!A57:I57")."""
    try:
        rango = response['updates']['updatedRange'].split('!')[-1]
        return int(re.search(r'[A-Z]+(\d+)', rango).group(1))
    except Exception:
        return None

def init_gsheets_connection():
    """Inicializar conexión con Google Sheets usando las credenciales en secrets"""
    try:
        # Crear credenciales desde secrets
        creds_dict = st.secrets["gsheets"]
        creds = Credentials.from_service_account_info(
            {
                "type": creds_dict["type"],
                "project_id": creds_dict["project_id"],
                "private_key_id": creds_dict["private_key_id"],
                "private_key": creds_dict["private_key"],
                "client_email": creds_dict["client_email"],
                "client_id": creds_dict["client_id"],
                "auth_uri": creds_dict["auth_uri"],
                "token_uri": creds_dict["token_uri"],
                "auth_provider_x509_cert_url": creds_dict["auth_provider_x509_cert_url"],
                "client_x509_cert_url": creds_dict["client_x509_cert_url"]
            },
            scopes=SCOPES
        )
        
        # Autorizar cliente
        client = gspread.authorize(creds)
        
        # Abrir spreadsheet
        spreadsheet = client.open_by_key(st.secrets["gsheets"]["spreadsheet_id"])
        
        # Obtener o crear hojas con headers
        try:
            annotations_sheet = spreadsheet.worksheet("anotaciones")
            # Verificar si tiene headers
            if not annotations_sheet.get_all_values():
                annotations_sheet.append_row([
                    "timestamp", "usuario", "pregunta_id", "modelo", 
                    "categoria_error", "explicacion", "es_correcta", 
                    "categoria_1", "categoria_2"
                ])
        except:
            # Crear hoja si no existe
            annotations_sheet = spreadsheet.add_worksheet(
                title="anotaciones", 
                rows=1000, 
                cols=10
            )
            annotations_sheet.append_row([
                "timestamp", "usuario", "pregunta_id", "modelo", 
                "categoria_error", "explicacion", "es_correcta", 
                "categoria_1", "categoria_2"
            ])
        
        try:
            progress_sheet = spreadsheet.worksheet("progreso_usuarios")
            # Verificar si tiene headers
            if not progress_sheet.get_all_values():
                progress_sheet.append_row([
                    "usuario", "ultima_pregunta_id", "total_anotadas",
                    "ultima_actualizacion", "ultimo_modelo"
                ])
        except:
            progress_sheet = spreadsheet.add_worksheet(
                title="progreso_usuarios",
                rows=100,
                cols=5
            )
            progress_sheet.append_row([
                "usuario", "ultima_pregunta_id", "total_anotadas",
                "ultima_actualizacion", "ultimo_modelo"
            ])
        
        return {
            'client': client,
            'spreadsheet': spreadsheet,
            'annotations': annotations_sheet,
            'progress': progress_sheet
        }
    
    except Exception as e:
        st.error(f"Error conectando con Google Sheets: {str(e)}")
        st.stop()

def save_annotation(gsheets, username, pregunta_id, modelo, categoria, explicacion, es_correcta, cat1, cat2):
    """Guardar o actualizar anotación en Google Sheets"""
    try:
        sheet = gsheets['annotations']

        # Ubicar la fila sin releer la hoja completa. El índice se llena al
        # cargar las anotaciones del usuario; si falta, se reconstruye una vez.
        row_index = gsheets.get('row_index')
        if row_index is None:
            row_index = _build_row_index(sheet.get_all_values(), username)
            gsheets['row_index'] = row_index

        key = _annotation_key(username, pregunta_id, modelo)
        existing_row = row_index.get(key)

        # Preparar datos
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = [
            timestamp, username, str(pregunta_id), modelo,
            categoria, explicacion, str(es_correcta),
            cat1, cat2
        ]

        if existing_row:
            # Actualizar fila existente
            sheet.update([row_data], f'A{existing_row}:I{existing_row}')
            return "actualizada"
        else:
            # Añadir nueva fila y recordar dónde quedó
            response = sheet.append_row(row_data)
            fila = _row_from_append(response)
            if fila:
                row_index[key] = fila
            return "guardada"

    except Exception as e:
        # El cache pudo quedar desalineado: forzar su reconstrucción
        gsheets['row_index'] = None
        st.error(f"Error guardando anotación: {str(e)}")
        return "error"

def get_user_annotations(gsheets, username):
    """Obtener todas las anotaciones previas del usuario.

    Es la única lectura completa de la hoja: aprovecha el recorrido para dejar
    armado el índice de filas que usa save_annotation.
    """
    try:
        sheet = gsheets['annotations']
        all_values = sheet.get_all_values()

        gsheets['row_index'] = _build_row_index(all_values, username)

        user_annotations = {}

        # Si solo hay headers o está vacío, retornar dict vacío
        if len(all_values) <= 1:
            return user_annotations
        
        # Procesar filas (skip header)
        for row in all_values[1:]:
            if len(row) >= 6 and row[1] == username:
                key = f"{row[2]}-{row[3]}"  # pregunta_id-modelo
                user_annotations[key] = {
                    'categoria': row[4] if len(row) > 4 else "",
                    'explicacion': row[5] if len(row) > 5 else "",
                    'timestamp': row[0] if len(row) > 0 else ""
                }
        
        return user_annotations
    
    except Exception as e:
        st.error(f"Error recuperando anotaciones: {str(e)}")
        return {}

def update_user_progress(gsheets, username, pregunta_id, total_anotadas, modelo=""):
    """Actualizar progreso del usuario"""
    try:
        sheet = gsheets['progress']

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # La fila del usuario en la hoja de progreso no cambia durante la
        # sesión, así que se busca una sola vez.
        user_row = gsheets.get('progress_row')
        if user_row is None:
            all_values = sheet.get_all_values()
            for idx, row in enumerate(all_values[1:], start=2):  # Skip header
                if len(row) > 0 and row[0] == username:
                    user_row = idx
                    gsheets['progress_row'] = idx
                    break

        row_data = [
            username,
            str(pregunta_id),
            str(total_anotadas),
            timestamp,
            str(modelo)
        ]

        if user_row:
            sheet.update([row_data], f'A{user_row}:E{user_row}')
        else:
            response = sheet.append_row(row_data)
            gsheets['progress_row'] = _row_from_append(response)

    except Exception as e:
        # No mostrar error para no interrumpir flujo
        gsheets['progress_row'] = None
        pass

def get_user_progress(gsheets, username):
    """Última pregunta registrada para el usuario.

    Devuelve (pregunta_id, modelo) para poder retomar la sesión donde quedó.
    Las filas escritas antes de que existiera la columna del modelo devuelven
    el modelo vacío; quien llama debe tolerarlo.
    """
    try:
        sheet = gsheets['progress']
        all_values = sheet.get_all_values()

        for idx, row in enumerate(all_values[1:], start=2):  # Skip header
            if len(row) > 1 and row[0] == username:
                gsheets['progress_row'] = idx
                return row[1], (row[4] if len(row) > 4 else "")

    except Exception as e:
        pass

    return None, ""

def get_all_annotations_summary(gsheets):
    """Obtener resumen de todas las anotaciones para estadísticas"""
    try:
        sheet = gsheets['annotations']
        all_values = sheet.get_all_values()
        
        summary = {
            'total': max(0, len(all_values) - 1),  # Restar header
            'por_usuario': {},
            'por_categoria': {}
        }
        
        if len(all_values) > 1:
            for row in all_values[1:]:  # Skip header
                if len(row) >= 5:
                    usuario = row[1]
                    categoria = row[4]
                    
                    if usuario:
                        summary['por_usuario'][usuario] = summary['por_usuario'].get(usuario, 0) + 1
                    
                    if categoria:
                        summary['por_categoria'][categoria] = summary['por_categoria'].get(categoria, 0) + 1
        
        return summary
    
    except Exception as e:
        return {'total': 0, 'por_usuario': {}, 'por_categoria': {}}