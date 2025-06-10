# IMPORTACIONES - Como traer herramientas que necesitamos
from flask import Flask, render_template, request, redirect, url_for, session, make_response
# Flask es como el motor de nuestro sitio web
# render_template = mostrar páginas web
# request = recibir información del usuario
# redirect = enviar al usuario a otra página
# session = recordar quien está conectado
# make_response = para crear respuestas personalizadas (como CSV)

from datetime import datetime, timedelta, time, date  # Para trabajar con fechas y horas
import pytz  # Para manejo de zonas horarias
import psycopg2  # Para conectarse a la base de datos PostgreSQL
import psycopg2.extras  # Herramientas extra para la base de datos
import os  # Para acceder a configuraciones del sistema
from dotenv import load_dotenv  # Para leer configuraciones secretas
import logging  # Para guardar registros de lo que pasa en la app
import csv  # Para crear archivos CSV
from io import StringIO  # Para manejar texto en memoria
from functools import lru_cache  # Para caching de funciones

# CONFIGURACIÓN INICIAL - Como preparar todo antes de empezar
logging.basicConfig(level=logging.INFO)  # Activar el sistema de registros
logger = logging.getLogger(__name__)  # Crear nuestro registrador personal

load_dotenv()  # Cargar configuraciones secretas desde un archivo .env

app = Flask(__name__)  # Crear nuestra aplicación web
# Una clave secreta para proteger la información de usuarios conectados
app.secret_key = os.getenv('SECRET_KEY', 'clave-temporal-cambiar-en-produccion')

# CONFIGURACIÓN DE ZONA HORARIA PARA PUNTA ARENAS
PUNTA_ARENAS_TZ = pytz.timezone('America/Punta_Arenas')

def obtener_hora_local():
    """Obtiene la hora actual de Punta Arenas independientemente del servidor"""
    utc_now = datetime.now(pytz.UTC)
    punta_arenas_time = utc_now.astimezone(PUNTA_ARENAS_TZ)
    
    # DEBUG - remover después
    print(f"🌍 UTC: {utc_now}")
    print(f"🏔️ Punta Arenas: {punta_arenas_time}")
    
    return punta_arenas_time

def fecha_hora_local():
    """Obtiene fecha y hora local para usar en place de datetime.now()"""
    local_time = obtener_hora_local()
    return local_time.replace(tzinfo=None)  # Sin timezone para compatibilidad con DB

# FUNCIÓN PARA CONECTARSE A LA BASE DE DATOS
def get_db():
    """
    Piensa en esto como abrir la puerta de un almacén donde guardamos toda la información.
    Como abrir una caja fuerte con una combinación específica.
    """
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),        # ¿Dónde está la base de datos? (como la dirección de casa)
            port=os.getenv("DB_PORT", "5432"),             # ¿Qué puerta usar? (como el número de apartamento)
            database=os.getenv("DB_NAME", "breaktimedb"),  # ¿Qué almacén específico? (nombre de la base de datos)
            user=os.getenv("DB_USER", "postgres"),         # ¿Quién soy? (usuario)
            password=os.getenv("DB_PASSWORD", "password123"), # ¿Cuál es mi contraseña?
            client_encoding='utf8'  # ¿En qué idioma hablamos? (codificación de caracteres)
        )
        return conn  # Devolver la conexión exitosa
    except Exception as e:
        # Si algo sale mal, anotar el error y avisar
        logger.error(f"Error conectando a la base de datos: {e}")
        raise  # Lanzar el error para que otros lo sepan

# OPTIMIZACIÓN: Cache para consultas frecuentes de usuarios
@lru_cache(maxsize=100)
def obtener_usuario_por_codigo(codigo):
    """Cache de usuarios por código para evitar consultas repetidas"""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT * FROM usuarios WHERE UPPER(codigo) = %s', (codigo.upper(),))
    usuario = cur.fetchone()
    conn.close()
    return dict(usuario) if usuario else None

# FUNCIÓN MEJORADA PARA VALIDAR TARJETAS CON MÁS ROBUSTEZ
def validar_tarjeta(tarjeta_raw):
    """
    Validador robusto de tarjetas RFID con múltiples verificaciones
    Detecta automáticamente formato y limpia caracteres especiales
    """
    if not tarjeta_raw:
        return None
    
    # Limpiar caracteres especiales comunes
    tarjeta = tarjeta_raw.strip()
    caracteres_especiales = [';', '?', '\n', '\r', '\t']
    for char in caracteres_especiales:
        tarjeta = tarjeta.replace(char, '')
    
    # Validar longitud mínima
    if len(tarjeta) < 3:
        return None
    
    # Validar que contenga al menos algunos números o letras
    if not any(c.isalnum() for c in tarjeta):
        return None
    
    return tarjeta.upper()  # Normalizar a mayúsculas

def limpiar_tarjeta(tarjeta_raw):
    """
    Limpia caracteres especiales de tarjetas SOLO AL GUARDAR
    Remueve ; al inicio y ? al final automáticamente
    """
    if not tarjeta_raw:
        return ""
    
    tarjeta = tarjeta_raw.strip()
    
    # Remover ; al inicio si existe
    if tarjeta.startswith(';'):
        tarjeta = tarjeta[1:]
    
    # Remover ? al final si existe  
    if tarjeta.endswith('?'):
        tarjeta = tarjeta[:-1]
    
    return tarjeta.strip()

# FILTRO PERSONALIZADO PARA CONVERTIR A ENTEROS
@app.template_filter('entero')
def entero_filter(value):
    """
    Como un traductor que convierte cualquier número decimal a número entero.
    Ejemplo: 15.7 se convierte en 15
    """
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0

# ========== SISTEMA DE JORNADAS NOCTURNAS CONTINUAS (09:00 - 06:00) ==========

def obtener_horarios_jornada(fecha=None):
    """
    Calcula los horarios de una jornada nocturna continua de 21 horas.
    Jornada estándar: 09:00 - 06:00 del día siguiente
    
    Retorna:
        dict: {
            'inicio': time(9, 0),     # Siempre 09:00
            'fin': time(6, 0),        # Siempre 06:00  
            'es_nocturna': True,      # Siempre True para este sistema
            'duracion_horas': 21      # Siempre 21 horas
        }
    """
    # Para simplicidad, siempre retornamos la jornada estándar
    # En el futuro se puede expandir para horarios especiales
    
    return {
        'inicio': time(9, 0),      # 09:00 AM
        'fin': time(6, 0),         # 06:00 AM del día siguiente  
        'es_nocturna': True,
        'duracion_horas': 21
    }

def obtener_fecha_jornada_unificada(momento=None):
    """
    Determina la fecha de jornada unificada para empleados que trabajan 
    en horarios nocturnos que cruzan medianoche.
    
    LÓGICA:
    - Jornada 09:00 - 06:00 del día siguiente
    - Si es antes de las 06:00 AM → pertenece a la jornada del día ANTERIOR
    - Si es 06:00 AM o después → pertenece a la jornada del día ACTUAL
    
    Ejemplos:
    - 2025-01-15 05:30 → fecha_jornada = 2025-01-14 (jornada anterior)
    - 2025-01-15 09:15 → fecha_jornada = 2025-01-15 (jornada actual)
    - 2025-01-15 23:45 → fecha_jornada = 2025-01-15 (jornada actual)
    """
    if momento is None:
        momento = fecha_hora_local()
    
    fecha_actual = momento.date()
    hora_actual = momento.time()
    
    # Límite: 06:00 AM
    limite_fin_jornada = time(6, 0)
    
    if hora_actual < limite_fin_jornada:
        # Es madrugada, pertenece a la jornada del día anterior
        fecha_jornada = fecha_actual - timedelta(days=1)
    else:
        # Es después de las 06:00, pertenece a la jornada del día actual
        fecha_jornada = fecha_actual
    
    return fecha_jornada

def obtener_reglas_descanso_por_rol(turno):
    """
    Define las reglas de descanso según el tipo de empleado.
    
    🎰 TODOS LOS EMPLEADOS TIENEN LOS MISMOS LÍMITES DE DESCANSO:
    - Comida: 40 minutos (para todos)
    - Descanso: 20 minutos (para todos)
    
    Lo que varía son las horas de trabajo:
    - Full Time: 9 horas de trabajo
    - Part-time: 5 horas de trabajo  
    - Llamado: 6 horas de trabajo
    
    Args:
        turno (str): 'Full', 'Part-time', 'Llamado'
    
    Returns:
        dict: {
            'limite_comida': int,      # Minutos máximos para comida (40 para todos)
            'limite_descanso': int,    # Minutos máximos para descanso (20 para todos)
            'horas_trabajo': int,      # Horas de trabajo según el tipo
            'descripcion': str         # Descripción legible
        }
    """
    reglas = {
        'Full': {
            'limite_comida': 40,
            'limite_descanso': 20,
            'horas_trabajo': 9,
            'descripcion': 'Full Time (9h trabajo, 40/20 min)'
        },
        'Part-time': {
            'limite_comida': 40,
            'limite_descanso': 20,
            'horas_trabajo': 5,
            'descripcion': 'Part-time (5h trabajo, 40/20 min)'
        },
        'Llamado': {
            'limite_comida': 40,
            'limite_descanso': 20,
            'horas_trabajo': 6,
            'descripcion': 'Llamado (6h trabajo, 40/20 min)'
        }
    }
    
    return reglas.get(turno, reglas['Full'])  # Default a Full Time si no se encuentra

def puede_tomar_descanso(usuario_id, tipo_descanso, conn):
    """
    Valida si un empleado puede tomar un descanso según las reglas de jornada nocturna.
    
    🎰 CASINO - OPERACIÓN 24/7 SIN PARAR
    RESTRICCIONES SIMPLIFICADAS:
    1. Horario permitido: 09:00 - 06:00 del día siguiente (jornada nocturna de 21 horas)
    2. Máximo 1 comida por jornada unificada
    
    Args:
        usuario_id (int): ID del usuario
        tipo_descanso (str): 'Comida' o 'Descanso'  
        conn: Conexión a la base de datos
    
    Returns:
        dict: {
            'permitido': bool,     # True si puede tomar descanso
            'razon': str          # Explicación del resultado
        }
    """
    momento_actual = fecha_hora_local()
    fecha_jornada = obtener_fecha_jornada_unificada(momento_actual)
    hora_actual = momento_actual.time()
    horarios = obtener_horarios_jornada()
    
    # 1. VERIFICAR HORARIO DE JORNADA NOCTURNA (09:00 - 06:00)
    inicio_jornada = horarios['inicio']  # 09:00
    fin_jornada = horarios['fin']        # 06:00
    
    # Lógica para horario que cruza medianoche
    if hora_actual >= inicio_jornada or hora_actual < fin_jornada:
        # Está dentro del horario permitido (09:00-23:59 o 00:00-05:59)
        pass
    else:
        # Fuera del horario de jornada (06:00 - 08:59) 
        return {
            'permitido': False,
            'razon': f'🎰 Fuera de horario de jornada. Casino opera: {inicio_jornada.strftime("%H:%M")} - {fin_jornada.strftime("%H:%M")} del día siguiente.'
        }
    
    # 2. VERIFICAR LÍMITE DE COMIDAS POR JORNADA (único límite real)
    if tipo_descanso == 'Comida':
        cur = conn.cursor()
        cur.execute('''
            SELECT COUNT(*) 
            FROM tiempos_descanso 
            WHERE usuario_id = %s 
            AND fecha = %s 
            AND tipo = 'Comida'
        ''', (usuario_id, fecha_jornada))
        
        comidas_hoy = cur.fetchone()[0]
        
        if comidas_hoy >= 1:
            return {
                'permitido': False,
                'razon': '🍽️ Ya tomó su comida para esta jornada. Solo 1 comida por jornada de 21 horas.'
            }
    
    # 3. ✅ TODO ESTÁ BIEN - CASINO NUNCA PARA, DESCANSO PERMITIDO
    return {
        'permitido': True,
        'razon': f'🎰 Descanso permitido. Casino operando 24/7 - Jornada nocturna activa.'
    }

# PÁGINA PRINCIPAL - Sin mensajes ni notificaciones
@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Esta es como la recepción de un edificio de oficinas.
    - GET: Cuando alguien solo quiere ver quién está en descanso
    - POST: Cuando alguien pasa su tarjeta para entrar/salir de descanso
    """
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        if request.method == 'POST':
            entrada_raw = request.form.get('entrada', '').strip()
            
            if not entrada_raw:
                return redirect(url_for('index'))
            
            usuario = None
            
            # INTENTAR COMO TARJETA PRIMERO
            if len(entrada_raw) >= 10:  # Si es largo, probablemente es tarjeta
                tarjeta = validar_tarjeta(entrada_raw)
                if tarjeta:
                    cur.execute('SELECT * FROM usuarios WHERE tarjeta = %s', (tarjeta,))
                    usuario = cur.fetchone()

            # SI NO ENCONTRÓ POR TARJETA, INTENTAR COMO CÓDIGO
            if not usuario:
                codigo = entrada_raw.upper().strip()
                if len(codigo) >= 2:
                    cur.execute('SELECT * FROM usuarios WHERE UPPER(codigo) = %s', (codigo,))
                    usuario = cur.fetchone()

            # Si no se encontró usuario con ninguno de los métodos
            if not usuario:
                return redirect(url_for('index'))            # PROCESAMIENTO DE ENTRADA/SALIDA DE DESCANSO
            usuario_id = usuario['id']
            nombre_usuario = usuario['nombre']

            cur.execute('SELECT * FROM descansos WHERE usuario_id = %s', (usuario_id,))
            descanso_activo = cur.fetchone()
            
            ahora = fecha_hora_local()
            
            # ===== USAR FECHA JORNADA UNIFICADA PARA CRUCES DE MEDIANOCHE =====
            fecha_jornada = obtener_fecha_jornada_unificada(ahora)
            hora_actual = ahora.time()
            
            # ===== OBTENER REGLAS DINÁMICAS POR ROL =====
            reglas = obtener_reglas_descanso_por_rol(usuario['turno'])

            if descanso_activo:
                # ===== SALIR DE DESCANSO CON REGLAS POR ROL =====
                inicio = descanso_activo['inicio']
                duracion = int((ahora - inicio).total_seconds() / 60)

                # Verificar si ya tuvo comida en esta JORNADA UNIFICADA
                cur.execute('''SELECT 1 FROM tiempos_descanso 
                              WHERE usuario_id = %s AND fecha = %s AND tipo = 'Comida' ''', 
                            (usuario_id, fecha_jornada))
                ya_tuvo_comida = cur.fetchone()
                
                # LÓGICA INTELIGENTE: determinar tipo según duración y reglas del rol
                tipo_descanso = 'Descanso'
                  # Si duración >= 30 min Y no ha tenido comida → considerar como Comida
                if duracion >= 30 and not ya_tuvo_comida:
                    tipo_descanso = 'Comida'

                cur.execute('''
                    INSERT INTO tiempos_descanso (usuario_id, tipo, fecha, inicio, fin, duracion_minutos)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (usuario_id, tipo_descanso, fecha_jornada, inicio.time(), hora_actual, duracion))
                
                cur.execute('DELETE FROM descansos WHERE id = %s', (descanso_activo['id'],))
                
            else:
                # ===== ENTRAR A DESCANSO CON VALIDACIONES =====
                # Verificar si puede tomar descanso según reglas de casino 24/7
                validacion = puede_tomar_descanso(usuario_id, 'Pendiente', conn)
                
                if validacion['permitido']:
                    cur.execute('''
                        INSERT INTO descansos (usuario_id, tipo, inicio)
                        VALUES (%s, %s, %s)
                    ''', (usuario_id, 'Pendiente', ahora))
                else:
                    # Si no puede tomar descanso, solo redirigir sin insertar
                    # En el futuro se podría mostrar el mensaje de validacion['razon']
                    pass

            conn.commit()
            return redirect(url_for('index'))        # ===== MOSTRAR QUIÉN ESTÁ EN DESCANSO CON REGLAS DINÁMICAS POR ROL =====
        cur.execute('''
        SELECT 
            u.nombre,
            u.codigo,
            u.turno,
            d.tipo,
            d.inicio
        FROM descansos d
        JOIN usuarios u ON u.id = d.usuario_id
        ORDER BY d.inicio DESC
        ''')

        activos_raw = cur.fetchall()
        activos = []
        
        # ===== CALCULAR TIEMPO RESTANTE CON REGLAS DINÁMICAS =====
        ahora = fecha_hora_local()
        for descanso in activos_raw:
            # Obtener reglas específicas por rol del empleado
            reglas = obtener_reglas_descanso_por_rol(descanso['turno'])
            
            transcurrido_segundos = (ahora - descanso['inicio']).total_seconds()
            transcurrido_minutos = int(transcurrido_segundos / 60)
              # Usar límites dinámicos según el rol y tipo de descanso
            if descanso['tipo'] == 'Comida':
                limite = reglas['limite_comida']  # 40 min para todos
            else:
                limite = reglas['limite_descanso']  # 20 min para todos
            
            tiempo_restante = max(limite - transcurrido_minutos, 0)
            
            # Crear diccionario con información completa
            descanso_completo = {
                'nombre': descanso['nombre'],
                'codigo': descanso['codigo'],
                'turno': descanso['turno'],
                'tipo': descanso['tipo'],
                'inicio': descanso['inicio'],
                'tiempo_restante': tiempo_restante,
                'limite_maximo': limite,  # Para debugging/info adicional
                'descripcion_regla': reglas['descripcion']  # Ej: "Full Time (40/20 min)"
            }
            activos.append(descanso_completo)
        
        return render_template('index.html', descansos=activos)  # Solo enviar descansos
        
    except Exception as e:
        logger.error(f"Error en index: {e}")
        return render_template('index.html', descansos=[])
    finally:
        if conn:
            conn.close()

# PÁGINA DE LOGIN - Sin flash()
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Como una puerta con código secreto para administradores.
    Busca usuarios y contraseñas en la base de datos.
    """
    next_page = request.args.get('next')
    
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        clave = request.form.get('clave', '').strip()
        
        if not usuario or not clave:
            return render_template('login.html', error="Usuario y contraseña requeridos")
            
        # BUSCAR EN LA BASE DE DATOS
        conn = None
        try:
            conn = get_db()
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            # Buscar administrador activo con usuario y clave
            cur.execute('''
                SELECT id, usuario, nombre 
                FROM administradores 
                WHERE usuario = %s AND clave = %s AND activo = TRUE
            ''', (usuario, clave))
            
            admin = cur.fetchone()
            
            if admin:
                # Login exitoso
                session['usuario'] = admin['usuario']
                session['admin_id'] = admin['id']
                session['admin_nombre'] = admin['nombre']
                session.permanent = True
                
                logger.info(f"Login exitoso para {admin['nombre']} ({admin['usuario']})")
                return redirect(url_for(next_page)) if next_page else redirect(url_for('base_datos'))
            else:
                # Login fallido
                logger.warning(f"Intento de login fallido para usuario: {usuario}")
                return render_template('login.html', error="Usuario o contraseña incorrectos")
                
        except Exception as e:
            logger.error(f"Error en login: {e}")
            return render_template('login.html', error="Error del sistema")
        finally:
            if conn:
                conn.close()
            
    return render_template('login.html')

# PÁGINA DE BASE DE DATOS - Sin flash()
@app.route('/base_datos', methods=['GET', 'POST'])
def base_datos():
    """
    Como un archivo de empleados donde puedes ver y agregar personas.
    Solo administradores pueden entrar aquí.
    """
    if 'usuario' not in session:
        # Sin flash - solo redireccionar
        return redirect(url_for('login', next='base_datos'))

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        if request.method == 'POST':
            nombre = request.form.get('nombre', '').strip()
            tarjeta_raw = request.form.get('tarjeta', '').strip()
            turno = request.form.get('turno', '').strip()
            codigo = request.form.get('codigo', '').strip()
            
            # LIMPIAR TARJETA AUTOMÁTICAMENTE AL GUARDAR
            tarjeta = limpiar_tarjeta(tarjeta_raw)
            
            if not all([nombre, tarjeta, turno, codigo]):
                # Sin flash - continuar sin mensaje
                pass
            elif len(tarjeta) < 3:
                # Sin flash - continuar sin mensaje
                pass
            elif len(codigo) < 2:
                # Sin flash - continuar sin mensaje
                pass
            else:
                try:
                    cur.execute('''INSERT INTO usuarios (nombre, tarjeta, turno, codigo) 
                                  VALUES (%s, %s, %s, %s)''',
                                (nombre, tarjeta, turno, codigo))
                    conn.commit()
                    # Sin flash - solo continuar
                except psycopg2.IntegrityError:
                    conn.rollback()
                    # Sin flash - solo continuar

        cur.execute('SELECT * FROM usuarios ORDER BY nombre')
        usuarios = cur.fetchall()
        return render_template('base_datos.html', usuarios=usuarios)
        
    except Exception as e:
        logger.error(f"Error en base_datos: {e}")
        # Sin flash - solo retornar página vacía
        return render_template('base_datos.html', usuarios=[])
    finally:
        if conn:
            conn.close()

# EDITAR USUARIO
@app.route('/editar_usuario/<int:usuario_id>', methods=['GET', 'POST'])
def editar_usuario(usuario_id):
    """
    Editar un usuario existente
    Como actualizar información en un archivo de empleados
    """
    if 'usuario' not in session:
        return redirect(url_for('login', next='base_datos'))

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        if request.method == 'POST':
            nombre = request.form.get('nombre', '').strip()
            tarjeta_raw = request.form.get('tarjeta', '').strip()
            turno = request.form.get('turno', '').strip()
            codigo = request.form.get('codigo', '').strip()
            
            # LIMPIAR TARJETA AUTOMÁTICAMENTE AL GUARDAR
            tarjeta = limpiar_tarjeta(tarjeta_raw)
            
            if all([nombre, tarjeta, turno, codigo]) and len(tarjeta) >= 3 and len(codigo) >= 2:
                try:
                    cur.execute('''
                        UPDATE usuarios 
                        SET nombre = %s, tarjeta = %s, turno = %s, codigo = %s 
                        WHERE id = %s
                    ''', (nombre, tarjeta, turno, codigo, usuario_id))
                    conn.commit()
                    return redirect(url_for('base_datos'))
                except psycopg2.IntegrityError:
                    conn.rollback()
                    # Tarjeta o código ya existe - continuar sin mensaje
                    pass
        
        # OBTENER DATOS DEL USUARIO PARA MOSTRAR EN EL FORMULARIO
        cur.execute('SELECT * FROM usuarios WHERE id = %s', (usuario_id,))
        usuario_data = cur.fetchone()
        
        if not usuario_data:
            # Si no existe el usuario, regresar a base de datos
            return redirect(url_for('base_datos'))
            
        return render_template('editar_usuario.html', usuario=usuario_data)
        
    except Exception as e:
        logger.error(f"Error editando usuario: {e}")
        return redirect(url_for('base_datos'))
    finally:
        if conn:
            conn.close()

# ELIMINAR USUARIO  
@app.route('/eliminar_usuario/<int:usuario_id>', methods=['POST'])
def eliminar_usuario(usuario_id):
    """
    Eliminar un usuario del sistema
    Como remover a alguien del archivo de empleados
    """
    if 'usuario' not in session:
        return redirect(url_for('login', next='base_datos'))

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # VERIFICAR SI EL USUARIO TIENE REGISTROS DE DESCANSOS
        cur.execute('SELECT COUNT(*) as total FROM tiempos_descanso WHERE usuario_id = %s', (usuario_id,))
        result = cur.fetchone()
        tiene_registros = result['total'] > 0 if result else False
        
        if tiene_registros:
            # SI TIENE REGISTROS, NO ELIMINAR (preservar integridad de datos)
            # En una versión futura podríamos marcar como "inactivo"
            pass
        else:
            # SI NO TIENE REGISTROS, ELIMINAR COMPLETAMENTE
            cur.execute('DELETE FROM usuarios WHERE id = %s', (usuario_id,))
            conn.commit()
        
        return redirect(url_for('base_datos'))
        
    except Exception as e:
        logger.error(f"Error eliminando usuario: {e}")
        return redirect(url_for('base_datos'))
    finally:
        if conn:
            conn.close()

# PÁGINA DE REGISTROS MEJORADA - Con filtros y exportación
@app.route('/registros')
def registros():
    """
    Como revisar un libro de historial donde se ve todo lo que ha pasado.
    Quién tomó descansos, cuándo y por cuánto tiempo.
    Ahora con filtros por fecha, usuario y tipo.
    """
    if 'usuario' not in session:
        return redirect(url_for('login', next='registros'))

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
          # OBTENER PARÁMETROS DE FILTRO MEJORADOS PARA JORNADAS
        jornada_inicio = request.args.get('jornada_inicio', '')
        jornada_fin = request.args.get('jornada_fin', '')
        usuario_filtro = request.args.get('usuario', '')
        tipo_filtro = request.args.get('tipo', '')
        
        # FILTROS RÁPIDOS POR JORNADA (nuevos)
        filtro_rapido = request.args.get('filtro_rapido', '')
        
        # CALCULAR FECHAS DE JORNADA SEGÚN FILTRO RÁPIDO
        fecha_jornada_actual = obtener_fecha_jornada_unificada()
        
        if filtro_rapido == 'hoy':
            jornada_inicio = fecha_jornada_actual.strftime('%Y-%m-%d')
            jornada_fin = fecha_jornada_actual.strftime('%Y-%m-%d')
        elif filtro_rapido == 'ayer':
            ayer = fecha_jornada_actual - timedelta(days=1)
            jornada_inicio = ayer.strftime('%Y-%m-%d')
            jornada_fin = ayer.strftime('%Y-%m-%d')
        elif filtro_rapido == 'semana':
            inicio_semana = fecha_jornada_actual - timedelta(days=fecha_jornada_actual.weekday())
            jornada_inicio = inicio_semana.strftime('%Y-%m-%d')
            jornada_fin = fecha_jornada_actual.strftime('%Y-%m-%d')
        elif filtro_rapido == 'mes':
            primer_dia_mes = fecha_jornada_actual.replace(day=1)
            jornada_inicio = primer_dia_mes.strftime('%Y-%m-%d')
            jornada_fin = fecha_jornada_actual.strftime('%Y-%m-%d')
        
        # CONSTRUIR CONSULTA BÁSICA Y FILTRAR POR JORNADA EN PYTHON
        consulta_base = '''
            SELECT u.nombre, u.codigo, t.tipo, t.fecha, t.inicio, t.fin, t.duracion_minutos
            FROM tiempos_descanso t
            JOIN usuarios u ON u.id = t.usuario_id
        '''
        
        condiciones = []
        parametros = []        # FILTROS BÁSICOS (sin jornada unificada en SQL)
        if usuario_filtro:
            condiciones.append("LOWER(u.nombre) LIKE LOWER(%s)")
            parametros.append(f'%{usuario_filtro}%')
            
        if tipo_filtro:
            condiciones.append("t.tipo = %s")
            parametros.append(tipo_filtro)
        
        # AGREGAR CONDICIONES A LA CONSULTA
        if condiciones:
            consulta_base += " WHERE " + " AND ".join(condiciones)
            
        consulta_base += " ORDER BY t.fecha DESC, t.inicio DESC LIMIT 500"
        
        cur.execute(consulta_base, parametros)
        todos_registros = cur.fetchall()
          # FILTRAR POR JORNADA UNIFICADA EN PYTHON
        historial = []
        for registro in todos_registros:
            # Calcular fecha de jornada unificada para este registro
            momento_registro = datetime.combine(registro['fecha'], registro['inicio'])
            fecha_jornada_registro = obtener_fecha_jornada_unificada(momento_registro)
            
            # Aplicar filtros de fecha de jornada si existen
            incluir = True
            if jornada_inicio:
                jornada_inicio_obj = datetime.strptime(jornada_inicio, '%Y-%m-%d').date()
                if fecha_jornada_registro < jornada_inicio_obj:
                    incluir = False
                    
            if jornada_fin and incluir:
                jornada_fin_obj = datetime.strptime(jornada_fin, '%Y-%m-%d').date()
                if fecha_jornada_registro > jornada_fin_obj:
                    incluir = False
            
            if incluir:
                # Agregar la fecha de jornada calculada al registro
                registro_completo = dict(registro)
                registro_completo['fecha_jornada'] = fecha_jornada_registro
                historial.append(registro_completo)
        
        # OBTENER LISTA DE USUARIOS PARA EL FILTRO
        cur.execute('SELECT DISTINCT nombre FROM usuarios ORDER BY nombre')
        usuarios_disponibles = cur.fetchall()
        
        # CALCULAR ESTADÍSTICAS
        if historial:
            total_registros = len(historial)
            total_minutos = sum(r['duracion_minutos'] for r in historial)
            total_horas = round(total_minutos / 60, 2)
            promedio_minutos = round(total_minutos / total_registros, 1)
        else:
            total_registros = total_minutos = total_horas = promedio_minutos = 0
        
        estadisticas = {
            'total_registros': total_registros,
            'total_minutos': total_minutos,
            'total_horas': total_horas,
            'promedio_minutos': promedio_minutos
        }
        
        return render_template('registros.html', 
                             historial=historial,
                             usuarios_disponibles=usuarios_disponibles,
                             estadisticas=estadisticas,                             filtros={
                                 'jornada_inicio': jornada_inicio,
                                 'jornada_fin': jornada_fin,
                                 'usuario': usuario_filtro,
                                 'tipo': tipo_filtro,
                                 'filtro_rapido': filtro_rapido
                             })
        
    except Exception as e:
        logger.error(f"Error en registros: {e}")
        return render_template('registros.html', historial=[], usuarios_disponibles=[], 
                             estadisticas={}, filtros={})
    finally:
        if conn:
            conn.close()

# NUEVA RUTA PARA EXPORTAR CSV
@app.route('/exportar_csv')
def exportar_csv():
    """
    Exportar registros filtrados a archivo CSV
    Como imprimir un reporte en Excel
    """
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
          # OBTENER LOS MISMOS FILTROS QUE EN REGISTROS (MEJORADOS PARA JORNADAS)
        jornada_inicio = request.args.get('jornada_inicio', '')
        jornada_fin = request.args.get('jornada_fin', '')
        usuario_filtro = request.args.get('usuario', '')
        tipo_filtro = request.args.get('tipo', '')
        filtro_rapido = request.args.get('filtro_rapido', '')
        
        # APLICAR FILTROS RÁPIDOS SI EXISTEN
        fecha_jornada_actual = obtener_fecha_jornada_unificada()
        
        if filtro_rapido == 'hoy':
            jornada_inicio = fecha_jornada_actual.strftime('%Y-%m-%d')
            jornada_fin = fecha_jornada_actual.strftime('%Y-%m-%d')
        elif filtro_rapido == 'ayer':
            ayer = fecha_jornada_actual - timedelta(days=1)
            jornada_inicio = ayer.strftime('%Y-%m-%d')
            jornada_fin = ayer.strftime('%Y-%m-%d')
        elif filtro_rapido == 'semana':
            inicio_semana = fecha_jornada_actual - timedelta(days=fecha_jornada_actual.weekday())
            jornada_inicio = inicio_semana.strftime('%Y-%m-%d')
            jornada_fin = fecha_jornada_actual.strftime('%Y-%m-%d')
        elif filtro_rapido == 'mes':
            primer_dia_mes = fecha_jornada_actual.replace(day=1)
            jornada_inicio = primer_dia_mes.strftime('%Y-%m-%d')
            jornada_fin = fecha_jornada_actual.strftime('%Y-%m-%d')# USAR LA MISMA LÓGICA DE FILTROS (básicos primero)
        consulta_base = '''
            SELECT u.nombre, u.codigo, t.tipo, t.fecha, t.inicio, t.fin, t.duracion_minutos
            FROM tiempos_descanso t
            JOIN usuarios u ON u.id = t.usuario_id
        '''
        
        condiciones = []
        parametros = []
            
        if usuario_filtro:
            condiciones.append("LOWER(u.nombre) LIKE LOWER(%s)")
            parametros.append(f'%{usuario_filtro}%')
            
        if tipo_filtro:
            condiciones.append("t.tipo = %s")
            parametros.append(tipo_filtro)
        
        if condiciones:
            consulta_base += " WHERE " + " AND ".join(condiciones)
            
        consulta_base += " ORDER BY t.fecha DESC, t.inicio DESC"
        
        cur.execute(consulta_base, parametros)
        todos_registros = cur.fetchall()
        
        # FILTRAR POR JORNADA UNIFICADA EN PYTHON
        datos = []
        for registro in todos_registros:
            # Calcular fecha de jornada unificada
            momento_registro = datetime.combine(registro['fecha'], registro['inicio'])
            fecha_jornada_registro = obtener_fecha_jornada_unificada(momento_registro)
              # Aplicar filtros de fecha de jornada si existen
            incluir = True
            if jornada_inicio:
                jornada_inicio_obj = datetime.strptime(jornada_inicio, '%Y-%m-%d').date()
                if fecha_jornada_registro < jornada_inicio_obj:
                    incluir = False
                    
            if jornada_fin and incluir:
                jornada_fin_obj = datetime.strptime(jornada_fin, '%Y-%m-%d').date()
                if fecha_jornada_registro > jornada_fin_obj:
                    incluir = False
            
            if incluir:
                # Agregar la fecha de jornada calculada
                registro_completo = dict(registro)
                registro_completo['fecha_jornada'] = fecha_jornada_registro
                datos.append(registro_completo)
        
        # CREAR ARCHIVO CSV EN MEMORIA
        output = StringIO()
        writer = csv.writer(output)
          # ESCRIBIR ENCABEZADOS
        writer.writerow([
            'Nombre',
            'Código',
            'Tipo Descanso',
            'Fecha Calendario',
            'Fecha Jornada',
            'Hora Inicio',
            'Hora Fin',
            'Duración (minutos)',
            'Duración (horas)'
        ])
        
        # ESCRIBIR DATOS
        for registro in datos:
            duracion_horas = round(registro['duracion_minutos'] / 60, 2)
            writer.writerow([
                registro['nombre'],
                registro['codigo'],
                registro['tipo'],
                registro['fecha'].strftime('%Y-%m-%d'),
                registro['fecha_jornada'].strftime('%Y-%m-%d'),
                registro['inicio'].strftime('%H:%M'),
                registro['fin'].strftime('%H:%M'),
                registro['duracion_minutos'],
                duracion_horas
            ])
        
        # CREAR RESPUESTA HTTP CON EL CSV
        output.seek(0)
        fecha_actual = fecha_hora_local().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f'registros_descansos_{fecha_actual}.csv'
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename={nombre_archivo}'
        
        return response
        
    except Exception as e:
        logger.error(f"Error exportando CSV: {e}")
        return redirect(url_for('registros'))
    finally:
        if conn:
            conn.close()

# NUEVA RUTA PARA REPORTES/DASHBOARD
@app.route('/reportes')
def reportes():
    """
    Página de reportes y estadísticas SEPARADOS por tipo
    Dashboard con métricas de Comida vs Descanso por separado
    """
    if 'usuario' not in session:
        return redirect(url_for('login', next='reportes'))

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # ===== OBTENER FECHA DE JORNADA UNIFICADA ACTUAL =====
        fecha_jornada_actual = obtener_fecha_jornada_unificada()
        inicio_semana = fecha_jornada_actual - timedelta(days=fecha_jornada_actual.weekday())
        
        # ======= ESTADÍSTICAS DE LA JORNADA ACTUAL - CALCULADAS EN PYTHON =======
        cur.execute('''
            SELECT tipo, duracion_minutos, fecha, inicio
            FROM tiempos_descanso 
            ORDER BY fecha DESC, inicio DESC
        ''')
        
        todos_los_registros = cur.fetchall()
        
        # Filtrar registros de la jornada actual
        registros_jornada_actual = []
        for registro in todos_los_registros:
            momento_registro = datetime.combine(registro['fecha'], registro['inicio'])
            fecha_jornada_registro = obtener_fecha_jornada_unificada(momento_registro)
            
            if fecha_jornada_registro == fecha_jornada_actual:
                registros_jornada_actual.append(registro)
        
        # Calcular estadísticas
        if registros_jornada_actual:
            total_descansos = len(registros_jornada_actual)
            total_minutos = sum(r['duracion_minutos'] for r in registros_jornada_actual)
            promedio_minutos = total_minutos / total_descansos if total_descansos > 0 else 0
            
            # Separar por tipo
            comidas = [r for r in registros_jornada_actual if r['tipo'] == 'Comida']
            descansos = [r for r in registros_jornada_actual if r['tipo'] == 'Descanso']
            
            total_comidas = len(comidas)
            minutos_comida = sum(r['duracion_minutos'] for r in comidas)
            promedio_comida = minutos_comida / total_comidas if total_comidas > 0 else 0
            
            total_descansos_cortos = len(descansos)
            minutos_descanso = sum(r['duracion_minutos'] for r in descansos)
            promedio_descanso = minutos_descanso / total_descansos_cortos if total_descansos_cortos > 0 else 0
        else:
            total_descansos = total_minutos = promedio_minutos = 0
            total_comidas = minutos_comida = promedio_comida = 0
            total_descansos_cortos = minutos_descanso = promedio_descanso = 0
        
        # Crear objeto de estadísticas como DictCursor
        stats_hoy = {
            'total_descansos': total_descansos,
            'total_minutos': total_minutos,
            'promedio_minutos': promedio_minutos,
            'total_comidas': total_comidas,
            'minutos_comida': minutos_comida,
            'promedio_comida': promedio_comida,
            'total_descansos_cortos': total_descansos_cortos,
            'minutos_descanso': minutos_descanso,
            'promedio_descanso': promedio_descanso
        }
          # ======= TOP USUARIOS QUE MÁS SE EXCEDEN EN TIEMPO =======
        # Consulta simple para obtener todos los registros de la semana
        cur.execute('''
            SELECT 
                u.nombre,
                u.codigo,
                u.turno,
                t.tipo,
                t.duracion_minutos,
                t.fecha,
                t.inicio
            FROM tiempos_descanso t
            JOIN usuarios u ON u.id = t.usuario_id
            WHERE t.fecha >= %s
            ORDER BY u.nombre, t.fecha DESC, t.inicio DESC
        ''', (inicio_semana,))
        
        todos_registros_usuarios = cur.fetchall()
        
        # Procesar en Python para calcular jornadas y excesos
        usuario_stats = {}
        for registro in todos_registros_usuarios:
            momento_registro = datetime.combine(registro['fecha'], registro['inicio'])
            fecha_jornada_registro = obtener_fecha_jornada_unificada(momento_registro)
            
            # Solo procesar registros de esta semana de jornadas
            if fecha_jornada_registro >= inicio_semana:
                codigo = registro['codigo']
                if codigo not in usuario_stats:
                    usuario_stats[codigo] = {
                        'nombre': registro['nombre'],
                        'codigo': codigo,
                        'turno': registro['turno'],
                        'total_descansos': 0,
                        'total_minutos': 0,
                        'exceso_comidas': 0,
                        'exceso_descansos': 0,
                        'total_exceso': 0,
                        'comidas_con_exceso': 0,
                        'descansos_con_exceso': 0,
                        'total_comidas': 0,
                        'total_descansos_cortos': 0,
                        'minutos_comida': 0,
                        'minutos_descanso': 0
                    }
                
                stats = usuario_stats[codigo]
                stats['total_descansos'] += 1
                stats['total_minutos'] += registro['duracion_minutos']
                
                if registro['tipo'] == 'Comida':
                    stats['total_comidas'] += 1
                    stats['minutos_comida'] += registro['duracion_minutos']
                    if registro['duracion_minutos'] > 40:
                        exceso = registro['duracion_minutos'] - 40
                        stats['exceso_comidas'] += exceso
                        stats['total_exceso'] += exceso
                        stats['comidas_con_exceso'] += 1
                elif registro['tipo'] == 'Descanso':
                    stats['total_descansos_cortos'] += 1
                    stats['minutos_descanso'] += registro['duracion_minutos']
                    if registro['duracion_minutos'] > 20:
                        exceso = registro['duracion_minutos'] - 20
                        stats['exceso_descansos'] += exceso
                        stats['total_exceso'] += exceso
                        stats['descansos_con_exceso'] += 1
        
        # Convertir a lista y ordenar por total_exceso
        top_usuarios = sorted(usuario_stats.values(), 
                            key=lambda x: (x['total_exceso'], x['total_descansos']), 
                            reverse=True)[:15]        # ======= DESCANSOS POR JORNADA CON SEPARACIÓN =======
        # Consulta simple para obtener registros de la última semana
        cur.execute('''
            SELECT 
                tipo,
                duracion_minutos,
                fecha,
                inicio
            FROM tiempos_descanso 
            WHERE fecha >= %s
            ORDER BY fecha DESC, inicio DESC
        ''', (fecha_jornada_actual - timedelta(days=6),))
        
        registros_semana = cur.fetchall()
        
        # Procesar en Python para agrupar por fecha de jornada
        jornadas_stats = {}
        for registro in registros_semana:
            momento_registro = datetime.combine(registro['fecha'], registro['inicio'])
            fecha_jornada_registro = obtener_fecha_jornada_unificada(momento_registro)
            
            if fecha_jornada_registro not in jornadas_stats:
                jornadas_stats[fecha_jornada_registro] = {
                    'fecha_jornada': fecha_jornada_registro,
                    'cantidad_total': 0,
                    'minutos_total': 0,
                    'cantidad_comidas': 0,
                    'minutos_comidas': 0,
                    'cantidad_descansos': 0,
                    'minutos_descansos': 0
                }
            
            stats = jornadas_stats[fecha_jornada_registro]
            stats['cantidad_total'] += 1
            stats['minutos_total'] += registro['duracion_minutos']
            
            if registro['tipo'] == 'Comida':
                stats['cantidad_comidas'] += 1
                stats['minutos_comidas'] += registro['duracion_minutos']
            elif registro['tipo'] == 'Descanso':
                stats['cantidad_descansos'] += 1
                stats['minutos_descansos'] += registro['duracion_minutos']
        
        # Convertir a lista y ordenar por fecha descendente
        descansos_por_dia = sorted(jornadas_stats.values(), 
                                 key=lambda x: x['fecha_jornada'], 
                                 reverse=True)        
        return render_template('reportes.html',
                             stats_hoy=stats_hoy,
                             top_usuarios=top_usuarios,
                             descansos_por_dia=descansos_por_dia,
                             fecha_hoy=fecha_jornada_actual.strftime('%Y-%m-%d'))
        
    except Exception as e:
        logger.error(f"Error en reportes: {e}")
        return render_template('reportes.html', 
                             stats_hoy=None, 
                             top_usuarios=[], 
                             descansos_por_dia=[])
    finally:
        if conn:
            conn.close()

# CERRAR SESIÓN - Sin flash()
@app.route('/logout')
def logout():
    """
    Cerrar sesión segura y limpiar completamente la sesión.
    Redirigir siempre a la página principal.
    """
    # Log de cierre de sesión para auditoría
    if 'admin_nombre' in session:
        logger.info(f"Logout: {session['admin_nombre']} cerró sesión")
    
    # Limpiar TODA la sesión
    session.clear()
    
    # Forzar expiración de cookies
    response = make_response(redirect(url_for('index')))
    response.set_cookie('session', '', expires=0)
    
    return response

# MANEJO DE ERRORES - Como tener un plan cuando algo sale mal

@app.errorhandler(404)  # Cuando buscan una página que no existe
def not_found(error):
    """Como decir 'Esta página no existe' cuando alguien se pierde"""
    return render_template('error.html', error="Página no encontrada"), 404

@app.errorhandler(500)  # Cuando hay un error interno del servidor
def internal_error(error):
    """Como decir 'Algo salió mal en nuestro sistema' cuando hay problemas técnicos"""
    return render_template('error.html', error="Error interno del servidor"), 500

# INICIAR LA APLICACIÓN - Como encender el sistema
if __name__ == '__main__':
    # Solo para desarrollo local
    app.run(debug=True, host='0.0.0.0', port=5000)
