import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Categorizador de Errores en Modelos Médicos Multimodales",
    page_icon="🏥",
    layout="wide"
)

# Estilo CSS personalizado
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .error-box {
        background-color: #0c0d0d;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 5px solid #cccccc;
    }
    .error-box.E_Vis {
        border-left: 5px solid #ff6b6b;
    }
    .error-box.E_Con {
        border-left: 5px solid #339af0;
    }
    .error-box.E_Int {
        border-left: 5px solid #ffd43b;
    }
    .error-box.E_Form {
        border-left: 5px solid #20c997;
    }
    .error-box.E_Mult {
        border-left: 5px solid #845ef7;
    }
    .correct {
        color: #2ecc71;
        font-weight: bold;
    }
    .incorrect {
        color: #e74c3c;
        font-weight: bold;
    }
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .progress-indicator {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .justification {
        background-color: #0c0d0d;
        border-left: 4px solid #6c757d;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .tooltip {
        position: relative;
        display: inline-block;
        border-bottom: 1px dotted black;
        cursor: help;
    }
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 300px;
        background-color: #555;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 10px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -150px;
        opacity: 0;
        transition: opacity 0.3s;
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
    .metadata-row {
        background-color: #343a40;
        padding: 10px;
        color: white;
        border-radius: 5px;
        margin-bottom: 20px;
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
    }
    .metadata-item {
        display: inline-block;
        margin-right: 20px;
    }
    .metadata-label {
        font-weight: bold;
        margin-right: 5px;
    }
    .image-container {
        margin-bottom: 20px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Definición de categorías de error
ERROR_CATEGORIES = {
    "E_Vis": "Error de Percepción Visual",
    "E_Con": "Error Conceptual o de Conocimiento Médico",
    "E_Int": "Error de Integración Imagen-Texto",
    "E_Form": "Error de Formulación de la Justificación",
    "E_Mult": "Error Múltiple o Indeterminado"
}

ERROR_DESCRIPTIONS = {
    "E_Vis": "El modelo se equivoca al 'ver' o interpretar la imagen. Identifica incorrectamente la estructura señalada, se equivoca en la localización espacial, describe características visuales irrelevantes u omite características visuales cruciales.",
    "E_Con": "La base de conocimiento médico que usa el modelo en la justificación es incorrecta, o el razonamiento sobre ese conocimiento es erróneo. Afirma hechos anatómicos/fisiológicos incorrectos, realiza inferencias lógicas erróneas o confunde conceptos médicos.",
    "E_Int": "El modelo falla en conectar adecuadamente lo que ve en la imagen con la pregunta, las opciones, o el conocimiento médico. Describe algo correctamente en la imagen pero lo asocia erróneamente con un término/opción o se enfoca en aspectos irrelevantes.",
    "E_Form": "La justificación es deficiente en cómo está expresada: vaga, ambigua, contradictoria, incompleta o irrelevante para la pregunta.",
    "E_Mult": "Hay una combinación clara de errores de distintas categorías, o la justificación es tan confusa que no se puede determinar la naturaleza del error."
}

# Inicialización de variables de estado
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'error_categorizations' not in st.session_state:
    st.session_state.error_categorizations = {}
if 'data' not in st.session_state:
    st.session_state.data = None
if 'filtered_data' not in st.session_state:
    st.session_state.filtered_data = None
if 'display_only_incorrect' not in st.session_state:
    st.session_state.display_only_incorrect = True
if 'filter_by_model' not in st.session_state:
    st.session_state.filter_by_model = "Todos"
if 'models_list' not in st.session_state:
    st.session_state.models_list = []
if 'categories_1' not in st.session_state:
    st.session_state.categories_1 = []
if 'filter_by_category_1' not in st.session_state:
    st.session_state.filter_by_category_1 = "Todas"
if 'categories_2' not in st.session_state:
    st.session_state.categories_2 = []
if 'filter_by_category_2' not in st.session_state:
    st.session_state.filter_by_category_2 = "Todas"
if 'image_dir' not in st.session_state:
    st.session_state.image_dir = None

def extract_model_answer(json_str):
    """Extrae la respuesta del modelo desde el formato JSON en la justificación."""
    try:
        # Primero limpiamos los bloques de código markdown
        if json_str.startswith("```") and json_str.endswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json\n"):
                json_str = json_str[5:]
        
        # Intentar parsearlo como JSON
        data = json.loads(json_str)
        if 'Respuesta' in data:
            return data['Respuesta'].strip().upper()
    except:
        # Si falla, intentar con regex para extraer la respuesta
        import re
        match = re.search(r'"Respuesta"\s*:\s*"([a-dA-D])"', json_str)
        if match:
            return match.group(1).upper()
    
    return None

def load_data(file):
    """Carga datos desde un archivo JSONL o JSON."""
    data = []
    try:
        # Determinar si es JSONL o JSON
        if file.name.endswith('.jsonl'):
            # Leer línea por línea para JSONL
            content = file.getvalue().decode('utf-8')
            for line in content.strip().split('\n'):
                if line.strip():  # Skip empty lines
                    item = json.loads(line)
                    item['respuesta_extraida'] = extract_model_answer(item['respuesta_modelo'])
                    data.append(item)
        else:  # Asumir JSON normal
            content = json.loads(file.getvalue())
            if isinstance(content, list):
                for item in content:
                    item['respuesta_extraida'] = extract_model_answer(item['respuesta_modelo'])
                    data.append(item)
            else:  # Si es un objeto JSON simple
                content['respuesta_extraida'] = extract_model_answer(content['respuesta_modelo'])
                data.append(content)
                
        # Convertir a DataFrame
        df = pd.DataFrame(data)
        
        # Verificar campos requeridos
        required_fields = ['id', 'pregunta', 'respuesta_correcta', 'respuesta_modelo', 'categoria_1', 'categoria_2']
        for field in required_fields:
            if field not in df.columns:
                st.error(f"El archivo no contiene el campo requerido: {field}")
                return None
                
        # Añadir campo de coincidencia
        df['es_correcta'] = df['respuesta_extraida'] == df['respuesta_correcta']
        
        # Opcional: extraer nombre del modelo si existe
        if 'modelo' not in df.columns:
            # Intentar extraer del nombre del archivo o asignar "Desconocido"
            modelo = file.name.split('.')[0] if '.' in file.name else "Desconocido"
            df['modelo'] = modelo
            
        return df
        
    except Exception as e:
        st.error(f"Error al cargar el archivo: {str(e)}")
        return None

def save_categorizations():
    """Guarda las categorizaciones en un archivo CSV."""
    if not st.session_state.error_categorizations:
        st.warning("No hay categorizaciones para guardar.")
        return
        
    # Convertir dict a DataFrame
    data = []
    for key, value in st.session_state.error_categorizations.items():
        question_id, model = key.split('-')
        data.append({
            'pregunta_id': question_id,
            'modelo': model,
            'categoria_error': value['categoria'],
            'notas': value.get('notas', '')
        })
        
    df = pd.DataFrame(data)
    
    # Generar nombre de archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"categorizacion_errores_{timestamp}.csv"
    
    # Guardar como CSV
    csv = df.to_csv(index=False).encode('utf-8')
    
    # Botón de descarga
    st.download_button(
        label="Descargar Categorizaciones como CSV",
        data=csv,
        file_name=filename,
        mime="text/csv"
    )
    
def navigate_to(index):
    """Navega a un índice específico en los datos filtrados."""
    if st.session_state.filtered_data is not None:
        if 0 <= index < len(st.session_state.filtered_data):
            st.session_state.current_index = index
            # Actualiza también el índice previamente seleccionado para evitar problemas de sincronización
            if 'previous_selected_index' in st.session_state:
                st.session_state.previous_selected_index = index + 1
            st.rerun()  # Forzar una actualización inmediata de la UI
        else:
            st.error("Índice fuera de rango.")

def filter_data():
    """Filtra los datos según los criterios seleccionados."""
    if st.session_state.data is not None:
        filtered = st.session_state.data.copy()
        
        # Filtrar por respuestas incorrectas
        if st.session_state.display_only_incorrect:
            filtered = filtered[~filtered['es_correcta']]
            
        # Filtrar por modelo
        if st.session_state.filter_by_model != "Todos":
            filtered = filtered[filtered['modelo'] == st.session_state.filter_by_model]
            
        # Filtrar por categoría 1
        if st.session_state.filter_by_category_1 != "Todas":
            filtered = filtered[filtered['categoria_1'] == st.session_state.filter_by_category_1]
            
        # Filtrar por categoría 2
        if st.session_state.filter_by_category_2 != "Todas":
            filtered = filtered[filtered['categoria_2'] == st.session_state.filter_by_category_2]
        
        st.session_state.filtered_data = filtered
        
        # Reset index if it's out of bounds
        if len(filtered) > 0 and st.session_state.current_index >= len(filtered):
            st.session_state.current_index = 0

def format_justification(justification):
    """Formatea la justificación para mostrarla sin los bloques de código markdown."""
    if justification.startswith("```") and justification.endswith("```"):
        parts = justification.split("```")
        if len(parts) >= 3:  # Hay al menos un bloque de código
            return parts[1].replace("json\n", "")
    return justification

# Interfaz de usuario
st.title("🏥 Categorizador de Errores en Modelos Médicos Multimodales")

# Barra lateral para carga de archivo y filtros
with st.sidebar:
    st.header("Configuración")
    
    # Cargar archivo
    uploaded_file = st.file_uploader("Carga un archivo JSONL o JSON", type=["jsonl", "json"])
    
    if uploaded_file is not None:
        # Cargar datos
        data = load_data(uploaded_file)
        if data is not None:
            st.success(f"Archivo cargado exitosamente. {len(data)} registros encontrados.")
            st.session_state.data = data
            
            # Extraer lista de modelos
            st.session_state.models_list = ["Todos"] + sorted(data['modelo'].unique().tolist())
            
            # Extraer categorías
            st.session_state.categories_1 = ["Todas"] + sorted(data['categoria_1'].unique().tolist())
            st.session_state.categories_2 = ["Todas"] + sorted(data['categoria_2'].unique().tolist())
            
            # Aplicar filtros iniciales
            filter_data()
    
    # Configurar directorio de imágenes
    if st.session_state.image_dir is None:
        st.subheader("Directorio de imágenes")
        image_dir = st.text_input("Carpeta raíz de imágenes:", value="")
        if st.button("Configurar directorio"):
            if os.path.exists(image_dir):
                st.session_state.image_dir = image_dir
                st.success(f"Directorio configurado: {image_dir}")
            else:
                st.error(f"El directorio no existe: {image_dir}")
    else:
        st.subheader("Directorio de imágenes")
        st.success(f"Directorio configurado: {st.session_state.image_dir}")
        if st.button("Cambiar directorio"):
            st.session_state.image_dir = None
    
    # Filtros
    st.subheader("Filtros")
    
    # Mostrar solo respuestas incorrectas
    display_only_incorrect = st.checkbox("Solo respuestas incorrectas", 
                                        value=st.session_state.display_only_incorrect)
    if display_only_incorrect != st.session_state.display_only_incorrect:
        st.session_state.display_only_incorrect = display_only_incorrect
        filter_data()
    
    # Filtrar por modelo
    if st.session_state.models_list:
        model_filter = st.selectbox("Modelo", st.session_state.models_list, 
                                   index=st.session_state.models_list.index(st.session_state.filter_by_model))
        if model_filter != st.session_state.filter_by_model:
            st.session_state.filter_by_model = model_filter
            filter_data()
    
    # Filtrar por categoría 1
    if st.session_state.categories_1:
        cat1_filter = st.selectbox("Categoría 1", st.session_state.categories_1, 
                                  index=st.session_state.categories_1.index(st.session_state.filter_by_category_1))
        if cat1_filter != st.session_state.filter_by_category_1:
            st.session_state.filter_by_category_1 = cat1_filter
            filter_data()
    
    # Filtrar por categoría 2
    if st.session_state.categories_2:
        cat2_filter = st.selectbox("Categoría 2", st.session_state.categories_2, 
                                  index=st.session_state.categories_2.index(st.session_state.filter_by_category_2))
        if cat2_filter != st.session_state.filter_by_category_2:
            st.session_state.filter_by_category_2 = cat2_filter
            filter_data()
    
    # Guardar categorizaciones
    if st.session_state.error_categorizations:
        st.subheader("Exportar")
        if st.button("Guardar Categorizaciones"):
            save_categorizations()
    
    # Estadísticas de categorización
    if st.session_state.error_categorizations:
        st.subheader("Estadísticas")
        
        # Contar categorías
        categories_count = {}
        for key, value in st.session_state.error_categorizations.items():
            cat = value['categoria']
            categories_count[cat] = categories_count.get(cat, 0) + 1
        
        # Mostrar conteo
        for cat, desc in ERROR_CATEGORIES.items():
            count = categories_count.get(cat, 0)
            st.text(f"{cat}: {count}")
        
        total = sum(categories_count.values())
        st.text(f"Total: {total}")

# Contenido principal
if st.session_state.filtered_data is not None and len(st.session_state.filtered_data) > 0:
    # Obtener registro actual
    row = st.session_state.filtered_data.iloc[st.session_state.current_index]
    
    # Crear un identificador único para esta pregunta+modelo
    current_key = f"{row['id']}-{row['modelo']}"
    
    # Mostrar encabezado con metadatos
    st.markdown(f"""
    <div class="progress-indicator">
        Pregunta {st.session_state.current_index + 1} de {len(st.session_state.filtered_data)} 
        (ID: {row['id']}, Modelo: {row['modelo']})
    </div>
    """, unsafe_allow_html=True)
    
    # Fila de metadatos
    st.markdown(f"""
    <div class="metadata-row">
        <div class="metadata-item"><span class="metadata-label">Categoría 1:</span> {row['categoria_1']}</div>
        <div class="metadata-item"><span class="metadata-label">Categoría 2:</span> {row['categoria_2']}</div>
        <div class="metadata-item"><span class="metadata-label">Imagen:</span> {row.get('nombre_imagen', 'N/A')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Mostrar imagen primero
    if 'ruta' in row and row['ruta'] and st.session_state.image_dir is not None:
        try:
            image_path = os.path.join(st.session_state.image_dir, row['ruta'])
            if os.path.exists(image_path):
                st.markdown(f"""<div class="image-container">""", unsafe_allow_html=True)
                st.image(image_path, caption=row['nombre_imagen'], width=500)
                st.markdown(f"""</div>""", unsafe_allow_html=True)
            else:
                st.warning(f"Imagen no encontrada en: {image_path}")
        except Exception as e:
            st.error(f"Error al cargar la imagen: {str(e)}")
    elif 'ruta' in row and row['ruta'] and st.session_state.image_dir is None:
        st.warning("Configura un directorio de imágenes en el panel lateral para ver las imágenes.")
    
    # Mostrar información de la pregunta
    st.subheader("Pregunta")
    st.write(row['pregunta'])
    
    # Tabla de respuestas
    result_df = pd.DataFrame({
        "Respuesta Correcta": [row['respuesta_correcta']],
        "Respuesta del Modelo": [row['respuesta_extraida']],
        "¿Correcta?": ["✅ Sí" if row['es_correcta'] else "❌ No"]
    })
    st.dataframe(result_df, hide_index=True)
    
    # Justificación del modelo
    st.subheader("Justificación del Modelo")
    formatted_justification = format_justification(row['respuesta_modelo'])
    try:
        # Intentar parsearlo como JSON para darle mejor formato
        json_data = json.loads(formatted_justification)
        if 'Justificacion' in json_data:
            st.markdown(f"""<div class="justification">{json_data['Justificacion']}</div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="justification">{formatted_justification}</div>""", unsafe_allow_html=True)
    except:
        st.markdown(f"""<div class="justification">{formatted_justification}</div>""", unsafe_allow_html=True)
    
    # Categorización de errores (solo para respuestas incorrectas)
    if not row['es_correcta']:
        st.subheader("Categorización del Error")
        
        # Obtener categorización anterior si existe
        current_category = ""
        current_notes = ""
        if current_key in st.session_state.error_categorizations:
            current_category = st.session_state.error_categorizations[current_key]['categoria']
            current_notes = st.session_state.error_categorizations[current_key].get('notas', "")
        
        # Mostrar descripciones de categorías
        st.write("Seleccione la categoría de error que mejor describe el problema principal:")
        
        # Crear columnas para las categorías
        cols = st.columns(len(ERROR_CATEGORIES))
        selected_category = ""
        
        for i, (cat_code, cat_name) in enumerate(ERROR_CATEGORIES.items()):
            with cols[i]:
                # Crear un botón para cada categoría
                is_selected = cat_code == current_category
                button_style = f"background-color: {'#e6f3ff' if is_selected else 'white'}; "
                button_style += "border: 1px solid #ccc; border-radius: 5px; padding: 10px; width: 100%; margin: 5px 0;"
                
                if st.button(f"{cat_code}", key=f"cat_{cat_code}", 
                            help=ERROR_DESCRIPTIONS[cat_code]):
                    selected_category = cat_code
                
                # Mostrar el nombre de la categoría debajo del botón
                st.write(cat_name)
        
        # Actualizar categorización si se seleccionó una nueva
        if selected_category and selected_category != current_category:
            st.session_state.error_categorizations[current_key] = {
                'categoria': selected_category,
                'notas': current_notes
            }
            # Recargar para mostrar la selección actualizada
            st.rerun()  # Cambiado de st.experimental_rerun() a st.rerun()
        
        # Mostrar descripción de la categoría seleccionada
        if current_category:
            st.markdown(f"""
            <div class="error-box {current_category}">
                <strong>{ERROR_CATEGORIES[current_category]}</strong><br>
                {ERROR_DESCRIPTIONS[current_category]}
            </div>
            """, unsafe_allow_html=True)
            
            # Campo para notas adicionales
            notes = st.text_area("Notas adicionales (opcional)", value=current_notes)
            if notes != current_notes:
                st.session_state.error_categorizations[current_key]['notas'] = notes
    
    # Navegación
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        if st.button("⬅️ Anterior", disabled=st.session_state.current_index <= 0):
            navigate_to(st.session_state.current_index - 1)
    
    with col2:
        # Selector numérico para navegar a un índice específico
        # Usar un key único para el number_input para mejorar la detección de cambios
        selected_index = st.number_input("Ir a pregunta #", 
                                         min_value=1, 
                                         max_value=len(st.session_state.filtered_data),
                                         value=st.session_state.current_index + 1,
                                         key="question_index_selector")
        
        # Añadir una clave al session_state para rastrear el índice seleccionado
        if 'previous_selected_index' not in st.session_state:
            st.session_state.previous_selected_index = st.session_state.current_index + 1
            
        # Verificar si ha cambiado desde la última renderización
        if selected_index != st.session_state.previous_selected_index:
            st.session_state.previous_selected_index = selected_index
            navigate_to(selected_index - 1)
    
    with col3:
        if st.button("Siguiente ➡️", disabled=st.session_state.current_index >= len(st.session_state.filtered_data) - 1):
            navigate_to(st.session_state.current_index + 1)

else:
    if uploaded_file is not None:
        st.info("No hay datos que mostrar con los filtros actuales. Intenta cambiar los filtros.")
    else:
        st.info("Carga un archivo JSONL o JSON para comenzar.")
        
        # Ejemplo de formato esperado
        st.subheader("Formato de Datos Esperado")
        st.code('''
{
  "id": 94,
  "pregunta": "Indique el nombre del elemento 6...",
  "respuesta_correcta": "D",
  "respuesta_modelo": "{\\"Respuesta\\": \\"c\\", \\"Justificacion\\": \\"El elemento número 6...\\"}",
  "nombre_imagen": "Fig6-14-pelv",
  "categoria_1": "AnatomiaTopografica",
  "categoria_2": "Pelvis",
  "ruta": "imagenes/AnatomiaTopografica/Pelvis/Fig6-14-pelv.jpg",
  "modelo": "GPT-4V"  // Opcional, se puede extraer del nombre del archivo
}
        ''', language="json")