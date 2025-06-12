# Guía de Uso - Categorizador de Errores en Modelos Médicos Multimodales

## 📋 Propósito de la Herramienta

Esta aplicación permite categorizar y analizar los errores que cometen los modelos de IA médicos multimodales al responder preguntas sobre imágenes anatómicas. Su objetivo es identificar los tipos de errores más comunes para mejorar el entrenamiento y evaluación de estos modelos.

## 🚀 Inicio Rápido

### 1. Cargar los Datos
1. **Ubicar el archivo de datos**: Busca tu archivo `.jsonl` o `.json` con las respuestas del modelo
2. **Subir archivo**: Usa el botón "Carga un archivo JSONL o JSON" en la barra lateral
3. **Verificar carga**: Confirma que aparezca el mensaje "Archivo cargado exitosamente"

### 2. Configurar Directorio de Imágenes
1. **Introducir ruta**: En la barra lateral, ingresa la ruta completa a la carpeta de imágenes
2. **Ejemplo**: `/ruta/a/imagenes/` o `C:\imagenes\`
3. **Confirmar**: Haz clic en "Configurar directorio"

### 3. Aplicar Filtros (Opcional)
- **Solo respuestas incorrectas**: Activado por defecto (recomendado)
- **Filtrar por modelo**: Si tienes múltiples modelos en el dataset
- **Filtrar por categorías**: Para enfocarte en temas específicos (ej. "Abdomen", "Tórax")

## 🔍 Categorías de Error

### E_Vis - Error de Percepción Visual 🔴
**¿Cuándo usar?** El modelo "no ve bien" la imagen
- ❌ Identifica incorrectamente la estructura señalada
- ❌ Se equivoca en la localización espacial
- ❌ Describe características visuales irrelevantes
- ❌ Omite características visuales cruciales

**Ejemplo del dataset:**
> **Pregunta**: ¿Qué tipo de válvula posee el elemento marcado con 5?
> **Respuesta correcta**: A (Válvula espiral)
> **Respuesta del modelo**: C (No tiene válvula)
> **Justificación**: "El número 5 corresponde a la vesícula biliar (cuerpo-fondo); esta estructura no presenta ningún sistema valvular propio..."
> 
> **Categorización**: E_Vis - El modelo identifica incorrectamente el elemento 5 como vesícula biliar cuando debería ser otra estructura con válvula espiral.

### E_Con - Error Conceptual o de Conocimiento Médico 🔵
**¿Cuándo usar?** El conocimiento médico es incorrecto
- ❌ Afirma hechos anatómicos/fisiológicos incorrectos
- ❌ Realiza inferencias lógicas erróneas
- ❌ Confunde conceptos médicos

**Ejemplo del dataset:**
> **Pregunta**: De dónde se origina la arteria indicada con 3?
> **Respuesta correcta**: B (Arteria ilíaca externa)
> **Respuesta del modelo**: D (Arteria femoral profunda)
> **Justificación**: "El vaso señalado corresponde a una rama circunfleja de la arteria femoral profunda..."
> 
> **Categorización**: E_Con - Error en el conocimiento anatómico del origen vascular.

### E_Int - Error de Integración Imagen-Texto 🟡
**¿Cuándo usar?** Falla la conexión entre imagen, pregunta y conocimiento
- ❌ Describe algo correctamente pero lo asocia erróneamente
- ❌ Se enfoca en aspectos irrelevantes para la pregunta
- ❌ No conecta adecuadamente lo visual con lo conceptual

**Ejemplo del dataset:**
> **Pregunta**: Indique el elemento que entrega irrigación funcional al hígado
> **Respuesta correcta**: D (No está rotulado)
> **Respuesta del modelo**: C
> **Justificación**: "La irrigación funcional del hígado proviene de la vena porta hepática, que en la imagen está señalada con el número 9."
> 
> **Categorización**: E_Int - El modelo conoce que la vena porta da irrigación funcional, pero selecciona mal el número en la imagen.

### E_Form - Error de Formulación de la Justificación 🟢
**¿Cuándo usar?** La justificación está mal expresada
- ❌ Justificación vaga o ambigua
- ❌ Contradictoria o incompleta
- ❌ Irrelevante para la pregunta específica

### E_Mult - Error Múltiple o Indeterminado 🟣
**¿Cuándo usar?** Combinación de errores o casos confusos
- ❌ Hay errores de múltiples categorías simultáneamente
- ❌ La justificación es tan confusa que no se puede categorizar claramente

## 📝 Proceso de Categorización

### Paso a Paso:
1. **Examinar la imagen**: Verifica qué estructura está realmente señalada
2. **Leer la pregunta**: Entiende exactamente qué se está pidiendo
3. **Analizar la respuesta**: Compara la respuesta del modelo vs. la correcta
4. **Evaluar la justificación**: Lee cuidadosamente el razonamiento del modelo
5. **Identificar el error principal**: ¿Cuál es la falla más importante?
6. **Seleccionar categoría**: Elige la que mejor describe el error principal
7. **Agregar notas**: Opcionalmente, describe el error específico

### Pregunta Clave para Cada Categoría:
- **E_Vis**: "¿El modelo ve/identifica correctamente la estructura?"
- **E_Con**: "¿El conocimiento médico utilizado es correcto?"
- **E_Int**: "¿Conecta bien lo que ve con lo que pregunta?"
- **E_Form**: "¿La justificación está bien formulada?"
- **E_Mult**: "¿Hay múltiples tipos de error?"

## 🎯 Consejos para una Categorización Efectiva

### ✅ Mejores Prácticas:
- **Enfócate en el error principal**: Si hay múltiples errores, identifica el más determinante
- **Usa las notas**: Detalla errores específicos o casos particulares
- **Sé consistente**: Mantén criterios similares a lo largo de la sesión
- **Revisa la imagen**: Siempre verifica qué está realmente señalado

### ⚠️ Casos Complicados:
- **Múltiples errores**: Si hay 2+ errores claros de diferentes tipos → E_Mult
- **Error sutil**: Si es difícil de categorizar → usar notas para explicar
- **Respuesta parcialmente correcta**: Categorizar por el aspecto que falla

## 🔧 Funciones de la Interfaz

### Navegación:
- **Botones ⬅️ ➡️**: Navegar secuencialmente
- **Selector numérico**: Ir directamente a una pregunta específica
- **Filtros**: Reducir el conjunto de datos a revisar

### Guardado:
- **Categorización automática**: Se guarda al seleccionar una categoría
- **Exportar**: Botón "Guardar Categorizaciones" genera archivo CSV
- **Estadísticas**: Panel lateral muestra conteo por categoría

### Metadatos Útiles:
- **ID**: Identificador único de la pregunta
- **Modelo**: Qué modelo generó la respuesta
- **Categorías 1 y 2**: Clasificación temática de la pregunta
- **Imagen**: Nombre del archivo de imagen

## 📊 Interpretación de Resultados

### Patrones a Identificar:
- **E_Vis frecuente**: El modelo tiene problemas de percepción visual
- **E_Con frecuente**: Necesita mejor entrenamiento en conocimiento médico
- **E_Int frecuente**: Falla en la integración multimodal
- **Variación por categoría**: Algunos temas son más difíciles que otros

### Uso de Estadísticas:
- **Total categorizado**: Progreso en la tarea
- **Distribución por tipo**: Qué errores son más comunes
- **Filtros por tema**: Identificar áreas problemáticas específicas

## 🔄 Flujo de Trabajo Recomendado

1. **Sesión de calibración**: Los dos médicos categorizan las mismas 20-30 preguntas y comparan resultados
2. **División del trabajo**: Cada médico toma un subconjunto o revisan de forma independiente
3. **Revisión cruzada**: Intercambiar casos difíciles o dudosos
4. **Consenso final**: Resolver discrepancias mediante discusión

## ❓ Resolución de Problemas Comunes

**Imagen no se carga**: Verificar ruta del directorio de imágenes
**Archivo no se carga**: Confirmar formato JSONL/JSON y estructura de datos
**Navegación lenta**: Usar filtros para reducir el dataset
**Categorización perdida**: Las selecciones se guardan automáticamente

---

Esta herramienta es fundamental para entender y mejorar el rendimiento de los modelos de IA médicos. Una categorización cuidadosa y consistente proporcionará insights valiosos para el desarrollo futuro.