import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd
from datetime import datetime
import time

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

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
                    "ultima_actualizacion"
                ])
        except:
            progress_sheet = spreadsheet.add_worksheet(
                title="progreso_usuarios", 
                rows=100, 
                cols=5
            )
            progress_sheet.append_row([
                "usuario", "ultima_pregunta_id", "total_anotadas", 
                "ultima_actualizacion"
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
        
        # Obtener todos los valores (más eficiente que get_all_records)
        all_values = sheet.get_all_values()
        
        # Si solo hay headers o está vacío, añadir directamente
        if len(all_values) <= 1:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            row_data = [
                timestamp, username, str(pregunta_id), modelo, 
                categoria, explicacion, str(es_correcta), 
                cat1, cat2
            ]
            sheet.append_row(row_data)
            return "guardada"
        
        # Buscar si existe anotación previa
        existing_row = None
        for idx, row in enumerate(all_values[1:], start=2):  # Skip header
            if len(row) >= 4 and row[1] == username and str(row[2]) == str(pregunta_id) and row[3] == modelo:
                existing_row = idx
                break
        
        # Preparar datos
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = [
            timestamp, username, str(pregunta_id), modelo, 
            categoria, explicacion, str(es_correcta), 
            cat1, cat2
        ]
        
        if existing_row:
            # Actualizar fila existente
            sheet.update(f'A{existing_row}:I{existing_row}', [row_data])
            return "actualizada"
        else:
            # Añadir nueva fila
            sheet.append_row(row_data)
            return "guardada"
    
    except Exception as e:
        st.error(f"Error guardando anotación: {str(e)}")
        return "error"

def get_user_annotations(gsheets, username):
    """Obtener todas las anotaciones previas del usuario"""
    try:
        sheet = gsheets['annotations']
        all_values = sheet.get_all_values()
        
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

def update_user_progress(gsheets, username, pregunta_id, total_anotadas):
    """Actualizar progreso del usuario"""
    try:
        sheet = gsheets['progress']
        all_values = sheet.get_all_values()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_row = None
        
        # Buscar usuario existente (skip header)
        if len(all_values) > 1:
            for idx, row in enumerate(all_values[1:], start=2):
                if len(row) > 0 and row[0] == username:
                    user_row = idx
                    break
        
        row_data = [
            username, 
            str(pregunta_id), 
            str(total_anotadas), 
            timestamp
        ]
        
        if user_row:
            sheet.update(f'A{user_row}:D{user_row}', [row_data])
        else:
            sheet.append_row(row_data)
    
    except Exception as e:
        # No mostrar error para no interrumpir flujo
        pass

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