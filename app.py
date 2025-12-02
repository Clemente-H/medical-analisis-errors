import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import time
from utils import (
    init_gsheets_connection, 
    save_annotation, 
    get_user_annotations,
    update_user_progress,
    get_all_annotations_summary
)

# Configuración de la página
st.set_page_config(
    page_title="Categorizador de Errores - Modelos Médicos",
    page_icon="🏥",
    layout="wide"
)

# CSS simplificado
st.markdown("""
<style>
    .main {
        padding: 1rem;
    }
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 2rem;
        border-radius: 10px;
        background-color: #1e1e1e;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .category-button {
        width: 100%;
        margin: 5px 0;
        padding: 12px;
        text-align: left;
    }
    .justification-box {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 3px solid #4a4a4a;
        color: white;
    }
    .progress-header {
        background-color: #2d2d2d;
        padding: 10px 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        font-size: 1.1rem;
    }
    .saved-indicator {
        color: #4CAF50;
        font-size: 0.9rem;
        margin-left: 10px;
    }
    div[data-testid="stSidebar"] {
        background-color: #1a1a1a;
    }
</style>
""", unsafe_allow_html=True)

# Categorías de error
ERROR_CATEGORIES = {
    "E_Vis": "Error de Percepción Visual",
    "E_Con": "Error Conceptual o de Conocimiento Médico",
    "E_Int": "Error de Integración Imagen-Texto",
    "E_Form": "Error de Formulación de la Justificación",
    "E_Mult": "Error Múltiple o Indeterminado"
}

ERROR_DESCRIPTIONS = {
    "E_Vis": "El modelo no interpreta correctamente lo que ve en la imagen",
    "E_Con": "Error en el conocimiento médico o razonamiento",
    "E_Int": "Falla al conectar la imagen con la pregunta o conocimiento",
    "E_Form": "La justificación está mal expresada o es ambigua",
    "E_Mult": "Múltiples errores o no se puede determinar"
}

ERROR_ICONS = {
    "E_Vis": "👁️",
    "E_Con": "🧠",
    "E_Int": "🔗",
    "E_Form": "📝",
    "E_Mult": "❓"
}

# Inicialización
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'temp_category' not in st.session_state:
    st.session_state.temp_category = None
if 'temp_explanation' not in st.session_state:
    st.session_state.temp_explanation = ""

def show_login():
    """Pantalla de login con contraseña"""
    st.markdown("<h1 style='text-align: center;'>🏥 Sistema de Anotación Médica</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center;'>Iniciar Sesión</h3>", unsafe_allow_html=True)
        
        allowed_users = st.secrets["users"]["allowed"]
        username = st.selectbox(
            "Selecciona tu usuario:",
            options=[""] + allowed_users,
            format_func=lambda x: "-- Seleccionar --" if x == "" else x
        )
        
        # Campo de contraseña
        password = st.text_input(
            "Contraseña:",
            type="password",
            placeholder="Ingresa la contraseña compartida"
        )
        
        if st.button("Entrar", type="primary", use_container_width=True):
            # Verificar contraseña desde secrets
            correct_password = st.secrets["users"]["shared_password"]
            
            if username and username in allowed_users:
                if password == correct_password:
                    st.session_state.username = username
                    st.success(f"¡Bienvenido {username}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta")
            else:
                st.error("❌ Selecciona un usuario válido")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Nota informativa
        st.info("💡 Solicita la contraseña al administrador del sistema")

def extract_model_answer(json_str):
    """Extrae la respuesta del modelo"""
    try:
        if json_str.startswith("```") and json_str.endswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json\n"):
                json_str = json_str[5:]
        
        data = json.loads(json_str)
        if 'Respuesta' in data:
            return data['Respuesta'].strip().upper()
    except:
        import re
        match = re.search(r'"Respuesta"\s*:\s*"([a-dA-D])"', json_str)
        if match:
            return match.group(1).upper()
    return None

def load_data():
    """Cargar datos desde archivo local"""
    try:
        data = []
        data_path = "data/preguntas.jsonl"
        
        if not os.path.exists(data_path):
            st.error(f"No se encuentra el archivo de datos en {data_path}")
            return None
        
        with open(data_path, 'r', encoding='utf-8') as file:
            for line in file:
                if line.strip():
                    item = json.loads(line)
                    item['respuesta_extraida'] = extract_model_answer(item['respuesta_modelo'])
                    data.append(item)
        
        df = pd.DataFrame(data)
        df['es_correcta'] = df['respuesta_extraida'] == df['respuesta_correcta']
        
        if 'modelo' not in df.columns:
            df['modelo'] = "GPT-4V"
        
        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return None

def filter_data():
    """Filtrar datos según criterios"""
    if st.session_state.data is not None:
        filtered = st.session_state.data.copy()
        
        if st.session_state.get('display_only_incorrect', True):
            filtered = filtered[~filtered['es_correcta']]
        
        if st.session_state.get('filter_by_model', "Todos") != "Todos":
            filtered = filtered[filtered['modelo'] == st.session_state.filter_by_model]
        
        if st.session_state.get('filter_by_category_1', "Todas") != "Todas":
            filtered = filtered[filtered['categoria_1'] == st.session_state.filter_by_category_1]
        
        st.session_state.filtered_data = filtered
        
        if len(filtered) > 0 and st.session_state.current_index >= len(filtered):
            st.session_state.current_index = 0

def format_justification(justification):
    """Formatear justificación"""
    if justification.startswith("```") and justification.endswith("```"):
        parts = justification.split("```")
        if len(parts) >= 3:
            return parts[1].replace("json\n", "")
    return justification

def save_and_navigate(next_index):
    """Guardar anotación actual y navegar"""
    # Solo guardar si hay una categoría seleccionada temporalmente
    if st.session_state.temp_category and not st.session_state.filtered_data.iloc[st.session_state.current_index]['es_correcta']:
        row = st.session_state.filtered_data.iloc[st.session_state.current_index]
        current_key = f"{row['id']}-{row['modelo']}"
        
        # Guardar en Google Sheets
        result = save_annotation(
            st.session_state.gsheets,
            st.session_state.username,
            row['id'],
            row['modelo'],
            st.session_state.temp_category,
            st.session_state.temp_explanation,
            row['es_correcta'],
            row['categoria_1'],
            row['categoria_2']
        )
        
        if result != "error":
            # Actualizar cache local
            st.session_state.user_annotations[current_key] = {
                'categoria': st.session_state.temp_category,
                'explicacion': st.session_state.temp_explanation,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Actualizar progreso
            update_user_progress(
                st.session_state.gsheets,
                st.session_state.username,
                row['id'],
                len(st.session_state.user_annotations)
            )
    
    # Limpiar temporales
    st.session_state.temp_category = None
    st.session_state.temp_explanation = ""
    
    # Navegar
    if 0 <= next_index < len(st.session_state.filtered_data):
        st.session_state.current_index = next_index
        
        # Recargar anotaciones del usuario para obtener datos actualizados
        st.session_state.user_annotations = get_user_annotations(
            st.session_state.gsheets, 
            st.session_state.username
        )
        
        st.rerun()

# VERIFICAR LOGIN
if 'username' not in st.session_state:
    show_login()
    st.stop()

# INICIALIZAR CONEXIONES Y DATOS
if 'gsheets' not in st.session_state:
    with st.spinner("Conectando..."):
        st.session_state.gsheets = init_gsheets_connection()

if 'user_annotations' not in st.session_state:
    st.session_state.user_annotations = get_user_annotations(
        st.session_state.gsheets, 
        st.session_state.username
    )

if 'data' not in st.session_state:
    data = load_data()
    if data is not None:
        st.session_state.data = data
        st.session_state.models_list = ["Todos"] + sorted(data['modelo'].unique().tolist())
        st.session_state.categories_1 = ["Todas"] + sorted(data['categoria_1'].unique().tolist())
        st.session_state.categories_2 = ["Todas"] + sorted(data['categoria_2'].unique().tolist())
        filter_data()

# SIDEBAR
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.divider()
    
    # Progreso
    total_anotadas = len(st.session_state.user_annotations)
    st.metric("Tus anotaciones", total_anotadas)
    
    st.divider()
    
    # Filtros básicos
    st.markdown("### Filtros")
    
    only_incorrect = st.checkbox(
        "Solo incorrectas", 
        value=st.session_state.get('display_only_incorrect', True),
        key='filter_incorrect'
    )
    if only_incorrect != st.session_state.get('display_only_incorrect', True):
        st.session_state.display_only_incorrect = only_incorrect
        filter_data()
    
    if 'models_list' in st.session_state:
        model = st.selectbox(
            "Modelo",
            st.session_state.models_list,
            key='filter_model_select'
        )
        if model != st.session_state.get('filter_by_model', "Todos"):
            st.session_state.filter_by_model = model
            filter_data()
    
    if 'categories_1' in st.session_state:
        cat1 = st.selectbox(
            "Categoría",
            st.session_state.categories_1,
            key='filter_cat1_select'
        )
        if cat1 != st.session_state.get('filter_by_category_1', "Todas"):
            st.session_state.filter_by_category_1 = cat1
            filter_data()

# CONTENIDO PRINCIPAL
st.title("🏥 Categorizador de Errores en Modelos Médicos Multimodales")

if st.session_state.get('filtered_data') is not None and len(st.session_state.filtered_data) > 0:
    row = st.session_state.filtered_data.iloc[st.session_state.current_index]
    current_key = f"{row['id']}-{row['modelo']}"
    existing_annotation = st.session_state.user_annotations.get(current_key)
    
    # Si hay anotación existente y no hay temporal, cargar en temporal
    if existing_annotation and st.session_state.temp_category is None:
        st.session_state.temp_category = existing_annotation.get('categoria')
        st.session_state.temp_explanation = existing_annotation.get('explicacion', '')
    
    # Header con progreso
    st.markdown(f"""
    <div class='progress-header'>
    Pregunta {st.session_state.current_index + 1} de {len(st.session_state.filtered_data)} | 
    ID: {row['id']} | Modelo: {row['modelo']} | 
    Anotadas por ti: {len(st.session_state.user_annotations)}
    </div>
    """, unsafe_allow_html=True)
    
    # Metadata
    cols = st.columns([1, 1, 1])
    with cols[0]:
        st.caption(f"**Categoría 1:** {row['categoria_1']}")
    with cols[1]:
        st.caption(f"**Categoría 2:** {row['categoria_2']}")
    with cols[2]:
        st.caption(f"**Imagen:** {row.get('nombre_imagen', 'N/A')}")
    
    st.divider()
    
    # LAYOUT DE 2 COLUMNAS
    col_left, col_right = st.columns([3, 2])
    
    # COLUMNA IZQUIERDA - Contenido (reordenado)
    with col_left:
        # 1. Pregunta (primero)
        st.subheader("Pregunta")
        st.write(row['pregunta'])
        
        # Respuestas (justo después de la pregunta)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Respuesta Correcta", row['respuesta_correcta'])
        with col2:
            st.metric("Respuesta del Modelo", row['respuesta_extraida'])
        
        if row['es_correcta']:
            st.success("✅ **Correcta**")
        else:
            st.error("❌ **Incorrecta**")
        
        # 2. Justificación del Modelo (segundo)
        st.subheader("Justificación del Modelo")
        formatted_just = format_justification(row['respuesta_modelo'])
        try:
            json_data = json.loads(formatted_just)
            if 'Justificacion' in json_data:
                st.markdown(f"<div class='justification-box'>{json_data['Justificacion']}</div>", 
                          unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='justification-box'>{formatted_just}</div>", 
                          unsafe_allow_html=True)
        except:
            st.markdown(f"<div class='justification-box'>{formatted_just}</div>", 
                       unsafe_allow_html=True)
        
        # 3. Imagen (último)
        if 'ruta' in row and row['ruta']:
            image_path = os.path.join("data/imagenes", row['ruta'])
            if os.path.exists(image_path):
                st.image(image_path, caption=row['nombre_imagen'], use_column_width=True)
            else:
                st.warning(f"Imagen no encontrada")
    
    # COLUMNA DERECHA - Controles
    with col_right:
        if row['es_correcta']:
            st.success("✅ El modelo respondió correctamente")
            st.info("No es necesario categorizar errores en respuestas correctas")
        else:
            st.markdown("### 🏷️ Categorización del Error")
            
            # Si existe anotación previa
            if existing_annotation:
                st.info(f"Ya categorizado: {existing_annotation['categoria']}")
            
            st.caption("Selecciona la categoría de error que mejor describe el problema principal:")
            
            # Botones de categorías (verticales) - NO GUARDAN, solo actualizan temporal
            for cat_code, cat_name in ERROR_CATEGORIES.items():
                icon = ERROR_ICONS[cat_code]
                is_selected = st.session_state.temp_category == cat_code
                
                if st.button(
                    f"{icon} {cat_code}: {cat_name}",
                    key=f"cat_{cat_code}",
                    help=ERROR_DESCRIPTIONS[cat_code],
                    type="primary" if is_selected else "secondary",
                    use_container_width=True
                ):
                    st.session_state.temp_category = cat_code
                    st.rerun()
            
            # Campo de explicación - se actualiza en session_state automáticamente
            st.markdown("### 📝 Contexto Adicional")
            
            st.session_state.temp_explanation = st.text_area(
                "Explica tu decisión (opcional pero recomendado):",
                value=st.session_state.temp_explanation,
                height=120,
                placeholder="¿Por qué elegiste esta categoría? ¿Qué error específico cometió el modelo?",
                key='explanation_field'
            )
            
            # Indicador de cambios sin guardar
            if st.session_state.temp_category:
                if not existing_annotation or (
                    st.session_state.temp_category != existing_annotation.get('categoria') or
                    st.session_state.temp_explanation != existing_annotation.get('explicacion', '')
                ):
                    st.warning("⚠️ Cambios sin guardar - Se guardarán al navegar")
        
        # Navegación - AQUÍ SE GUARDA TODO
        st.divider()
        st.markdown("### Navegación")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "⬅️ Anterior",
                disabled=st.session_state.current_index <= 0,
                use_container_width=True
            ):
                save_and_navigate(st.session_state.current_index - 1)
        
        with col2:
            if st.button(
                "Siguiente ➡️",
                disabled=st.session_state.current_index >= len(st.session_state.filtered_data) - 1,
                use_container_width=True,
                type="primary"
            ):
                save_and_navigate(st.session_state.current_index + 1)

else:
    st.info("No hay datos que mostrar. Verifica los filtros en la barra lateral.")

# Footer simple
st.divider()
st.caption(f"Sesión: {st.session_state.username} | {datetime.now().strftime('%Y-%m-%d %H:%M')}")