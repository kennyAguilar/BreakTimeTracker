# 🎰 BreakTimeTracker - Sistema de Jornadas Nocturnas Continuas

Sistema avanzado de control de descansos para empleados de casino con jornadas nocturnas de 21 horas continuas.

## ✨ Características Principales

### 🌙 Jornadas Nocturnas Continuas (21 horas)
- **Horario**: 09:00 AM - 06:00 AM del día siguiente
- **Operación 24/7**: Sin interrupciones, como un casino real
- **Manejo de medianoche**: Fecha de jornada unificada para empleados nocturnos

### 👥 Tipos de Empleados
- **Full Time**: 9 horas de trabajo, 40 min comida, 20 min descanso
- **Part-time**: 5 horas de trabajo, 40 min comida, 20 min descanso  
- **Llamado**: 6 horas de trabajo, 40 min comida, 20 min descanso

### 🎯 Reglas Simplificadas
- **Máximo 1 comida** por jornada unificada de 21 horas
- **Sin límites** en cantidad de descansos cortos
- **Sin restricciones** de tiempo entre descansos (casino nunca para)

## 🚀 Funcionalidades Implementadas

### 📊 Sistema Principal
- ✅ Entrada/salida con código de empleado
- ✅ Tracking en tiempo real de descansos activos
- ✅ Cálculo automático de duración y tipo de descanso
- ✅ Validaciones inteligentes por horario y rol

### 📈 Reportes y Estadísticas
- ✅ Estadísticas de jornada actual
- ✅ Top usuarios que se exceden en tiempo
- ✅ Histórico de descansos por jornada unificada
- ✅ Exportación a CSV con fechas calendar y jornada

### 🔍 Filtros Avanzados
- ✅ Filtrado por fecha de jornada (no fecha calendario)
- ✅ Separación entre comidas y descansos
- ✅ Búsqueda por empleado, tipo, fecha

## 🛠️ Tecnologías

- **Backend**: Python Flask
- **Base de datos**: PostgreSQL
- **Frontend**: HTML5 + TailwindCSS + JavaScript
- **Timezone**: Manejo automático de zona horaria local

## 📋 Instalación

### Requisitos
```bash
pip install flask psycopg2-binary python-dotenv pytz
```

### Configuración
1. Configurar base de datos PostgreSQL
2. Ejecutar `python init_db.py` para crear tablas
3. Agregar usuarios con `python agregar_usuario.py`
4. Iniciar con `python app.py`

## 🏗️ Arquitectura del Sistema

### Funciones Principales

#### `obtener_fecha_jornada_unificada(momento=None)`
Calcula la fecha de jornada unificada para manejo de cruces de medianoche:
- Si hora < 06:00 AM → fecha jornada = día anterior  
- Si hora >= 06:00 AM → fecha jornada = día actual

#### `obtener_horarios_jornada(fecha=None)`
Retorna horarios fijos de jornada nocturna:
- Inicio: 09:00 AM
- Fin: 06:00 AM del día siguiente
- Duración: 21 horas continuas

#### `obtener_reglas_descanso_por_rol(turno)`
Define límites unificados por tipo de empleado:
- Todos: 40 min comida, 20 min descanso
- Solo varía las horas de trabajo según el tipo

#### `puede_tomar_descanso(usuario_id, tipo_descanso, conn)`
Validaciones simplificadas para operación casino 24/7:
- Horario permitido: 09:00-06:00
- Máximo 1 comida por jornada unificada

## 📁 Estructura de Archivos

```
BreakTimeTracker/
├── app.py                 # Aplicación principal (1129+ líneas)
├── init_db.py            # Inicialización de base de datos
├── agregar_usuario.py    # Gestión de usuarios
├── requirements.txt      # Dependencias
├── templates/            # Templates HTML
│   ├── index.html       # Página principal
│   ├── registros.html   # Histórico de registros
│   ├── reportes.html    # Dashboard de estadísticas
│   └── ...
├── static/
│   └── style.css        # Estilos personalizados
└── README.md            # Este archivo
```

## 🔧 Configuración de Jornadas

### Lógica de Fecha Unificada
```python
# Ejemplo: Empleado entra 10 PM del día 1, sale 6 AM del día 2
# Toda la jornada se agrupa bajo fecha_jornada = día 1

if hora_actual < 06:00:
    fecha_jornada = fecha_calendario - 1_día
else:
    fecha_jornada = fecha_calendario
```

### Validaciones de Horario
```python
# Horario permitido: 09:00-06:00 (cruzando medianoche)
if (hora >= 09:00) OR (hora < 06:00):
    return "Horario válido"
else:
    return "Fuera de jornada"
```

## 📊 Casos de Uso

### Escenario 1: Empleado Nocturno
- Entra: 10 PM del 9 junio
- Sale: 6 AM del 10 junio  
- **Fecha jornada**: 9 junio (toda la jornada)

### Escenario 2: Empleado Diurno
- Entra: 9 AM del 10 junio
- Sale: 6 PM del 10 junio
- **Fecha jornada**: 10 junio

### Escenario 3: Cruce de Medianoche
- 11:30 PM → fecha jornada = día actual
- 02:00 AM → fecha jornada = día anterior
- 07:00 AM → fecha jornada = día actual

## 🎯 Optimizaciones Implementadas

### Performance
- ✅ Consultas SQL simples sin cálculos de fecha complejos
- ✅ Procesamiento de jornadas en Python (más flexible)
- ✅ Filtrado post-consulta para agrupación por jornada

### Usabilidad  
- ✅ Interfaz responsive (mobile-first)
- ✅ Actualizaciones en tiempo real de contadores
- ✅ Validaciones instantáneas de entrada

### Mantenibilidad
- ✅ Funciones modulares y reutilizables
- ✅ Configuración centralizada de reglas
- ✅ Logs detallados para debugging

## 🚦 Estado del Proyecto

### ✅ Completado (100%)
- [x] Sistema de jornadas nocturnas continuas
- [x] Manejo de cruces de medianoche
- [x] Reglas unificadas por tipo de empleado
- [x] Filtros por fecha de jornada unificada
- [x] Reportes simplificados
- [x] Validaciones optimizadas
- [x] Templates responsivos

### 🔄 Próximas Mejoras (Opcionales)
- [ ] Dashboard en tiempo real con WebSockets
- [ ] Notificaciones push para excesos de tiempo
- [ ] Integración con sistemas de nómina
- [ ] API REST para aplicaciones móviles

## 📞 Soporte

Sistema desarrollado para operación casino 24/7 con jornadas nocturnas continuas.

**Desarrollado con ❤️ para empleados nocturnos que mantienen el casino funcionando sin parar** 🎰
