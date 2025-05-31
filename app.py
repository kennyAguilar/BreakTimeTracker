# IMPORTACIONES - Como traer herramientas que necesitamos
from flask import Flask, render_template, request, redirect, url_for, session, make_response
# Flask es como el motor de nuestro sitio web
# render_template = mostrar páginas web
# request = recibir información del usuario
# redirect = enviar al usuario a otra página
# session = recordar quien está conectado
# make_response = para crear respuestas personalizadas (como CSV)

from datetime import datetime, timedelta  # Para trabajar con fechas y horas
import pytz  # Para manejo de zonas horarias
import psycopg2  # Para conectarse a la base de datos PostgreSQL
import psycopg2.extras  # Herramientas extra para la base de datos
import os  # Para acceder a configuraciones del sistema
from dotenv import load_dotenv  # Para leer configuraciones secretas
import logging  # Para guardar registros de lo que pasa en la app
import csv  # Para crear archivos CSV
from io import StringIO  # Para manejar texto en memoria

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

# FUNCIÓN PARA VALIDAR TARJETAS
def validar_tarjeta(tarjeta_raw):
    """
    Como un guardia de seguridad que revisa si una tarjeta es válida.
    Limpia la tarjeta de caracteres raros y verifica que sea lo suficientemente larga.
    """
    if not tarjeta_raw:  # Si no hay tarjeta, rechazar
        return None
    
    # Limpiar la tarjeta: quitar espacios y caracteres extraños como ; y ?
    tarjeta = tarjeta_raw.strip().replace(';', '').replace('?', '')
    
    if len(tarjeta) < 3:  # Si la tarjeta es muy corta (menos de 3 caracteres), rechazar
        return None
    
    return tarjeta  # Devolver la tarjeta limpia y válida

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
                return redirect(url_for('index'))

            # PROCESAMIENTO DE ENTRADA/SALIDA DE DESCANSO
            usuario_id = usuario['id']
            nombre_usuario = usuario['nombre']

            cur.execute('SELECT * FROM descansos WHERE usuario_id = %s', (usuario_id,))
            descanso_activo = cur.fetchone()

            ahora = fecha_hora_local()
            fecha_actual = ahora.date() 
            hora_actual = ahora.time()

            if descanso_activo:
                # SALIR DE DESCANSO
                inicio = descanso_activo['inicio']
                duracion = int((ahora - inicio).total_seconds() / 60)

                cur.execute('''SELECT 1 FROM tiempos_descanso 
                              WHERE usuario_id = %s AND fecha = %s AND tipo = 'Comida' ''', 
                            (usuario_id, fecha_actual))
                ya_tuvo_40 = cur.fetchone()
                
                tipo_descanso = 'Descanso'
                if duracion >= 30 and not ya_tuvo_40:
                    tipo_descanso = 'Comida'

                cur.execute('''
                    INSERT INTO tiempos_descanso (usuario_id, tipo, fecha, inicio, fin, duracion_minutos)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (usuario_id, tipo_descanso, fecha_actual, inicio.time(), hora_actual, duracion))
                
                cur.execute('DELETE FROM descansos WHERE id = %s', (descanso_activo['id'],))
                
            else:
                # ENTRAR A DESCANSO
                cur.execute('''
                    INSERT INTO descansos (usuario_id, tipo, inicio)
                    VALUES (%s, %s, %s)
                ''', (usuario_id, 'Pendiente', ahora))

            conn.commit()
            return redirect(url_for('index'))

        # MOSTRAR QUIÉN ESTÁ EN DESCANSO - Calcular en Python para garantizar enteros
        cur.execute('''
        SELECT 
            u.nombre,
            u.codigo,
            d.tipo,
            d.inicio
        FROM descansos d
        JOIN usuarios u ON u.id = d.usuario_id
        ORDER BY d.inicio DESC
        ''')

        activos_raw = cur.fetchall()
        activos = []
        
        # Calcular tiempo restante en Python para garantizar enteros
        ahora = fecha_hora_local()
        for descanso in activos_raw:
            transcurrido_segundos = (ahora - descanso['inicio']).total_seconds()
            transcurrido_minutos = int(transcurrido_segundos / 60)  # Convertir a entero
            limite = 40 if descanso['tipo'] == 'Comida' else 20
            tiempo_restante = max(limite - transcurrido_minutos, 0)  # No negativos
            
            # Crear nuevo diccionario con el tiempo calculado como entero
            descanso_completo = {
                'nombre': descanso['nombre'],
                'codigo': descanso['codigo'],
                'tipo': descanso['tipo'],
                'inicio': descanso['inicio'],
                'tiempo_restante': tiempo_restante  # Ya es entero
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
        
        # OBTENER PARÁMETROS DE FILTRO
        fecha_inicio = request.args.get('fecha_inicio', '')
        fecha_fin = request.args.get('fecha_fin', '')
        usuario_filtro = request.args.get('usuario', '')
        tipo_filtro = request.args.get('tipo', '')
        
        # CONSTRUIR CONSULTA DINÁMICA CON FILTROS
        consulta_base = '''
            SELECT u.nombre, u.codigo, t.tipo, t.fecha, t.inicio, t.fin, t.duracion_minutos
            FROM tiempos_descanso t
            JOIN usuarios u ON u.id = t.usuario_id
        '''
        
        condiciones = []
        parametros = []
        
        # FILTRO POR FECHA INICIO
        if fecha_inicio:
            condiciones.append("t.fecha >= %s")
            parametros.append(fecha_inicio)
        
        # FILTRO POR FECHA FIN
        if fecha_fin:
            condiciones.append("t.fecha <= %s")
            parametros.append(fecha_fin)
            
        # FILTRO POR USUARIO
        if usuario_filtro:
            condiciones.append("LOWER(u.nombre) LIKE LOWER(%s)")
            parametros.append(f'%{usuario_filtro}%')
            
        # FILTRO POR TIPO
        if tipo_filtro:
            condiciones.append("t.tipo = %s")
            parametros.append(tipo_filtro)
        
        # AGREGAR CONDICIONES A LA CONSULTA
        if condiciones:
            consulta_base += " WHERE " + " AND ".join(condiciones)
            
        consulta_base += " ORDER BY t.fecha DESC, t.inicio DESC LIMIT 500"
        
        cur.execute(consulta_base, parametros)
        historial = cur.fetchall()
        
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
                             estadisticas=estadisticas,
                             filtros={
                                 'fecha_inicio': fecha_inicio,
                                 'fecha_fin': fecha_fin,
                                 'usuario': usuario_filtro,
                                 'tipo': tipo_filtro
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
        
        # OBTENER LOS MISMOS FILTROS QUE EN REGISTROS
        fecha_inicio = request.args.get('fecha_inicio', '')
        fecha_fin = request.args.get('fecha_fin', '')
        usuario_filtro = request.args.get('usuario', '')
        tipo_filtro = request.args.get('tipo', '')
        
        # USAR LA MISMA LÓGICA DE FILTROS
        consulta_base = '''
            SELECT u.nombre, u.codigo, t.tipo, t.fecha, t.inicio, t.fin, t.duracion_minutos
            FROM tiempos_descanso t
            JOIN usuarios u ON u.id = t.usuario_id
        '''
        
        condiciones = []
        parametros = []
        
        if fecha_inicio:
            condiciones.append("t.fecha >= %s")
            parametros.append(fecha_inicio)
        
        if fecha_fin:
            condiciones.append("t.fecha <= %s")
            parametros.append(fecha_fin)
            
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
        datos = cur.fetchall()
        
        # CREAR ARCHIVO CSV EN MEMORIA
        output = StringIO()
        writer = csv.writer(output)
        
        # ESCRIBIR ENCABEZADOS
        writer.writerow([
            'Nombre',
            'Código',
            'Tipo Descanso',
            'Fecha',
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
    Página de reportes y estadísticas
    Como un dashboard con gráficos y números importantes
    """
    if 'usuario' not in session:
        return redirect(url_for('login', next='reportes'))

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # ESTADÍSTICAS DE HOY
        hoy = fecha_hora_local().date()
        cur.execute('''
            SELECT 
                COUNT(*) as total_descansos,
                COALESCE(SUM(duracion_minutos), 0) as total_minutos,
                COALESCE(AVG(duracion_minutos), 0) as promedio_minutos,
                COUNT(CASE WHEN tipo = 'Comida' THEN 1 END) as comidas,
                COUNT(CASE WHEN tipo = 'Descanso' THEN 1 END) as descansos_cortos
            FROM tiempos_descanso 
            WHERE fecha = %s
        ''', (hoy,))
        
        stats_hoy = cur.fetchone()
        
        # ESTADÍSTICAS DE LA SEMANA
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        cur.execute('''
            SELECT 
                COUNT(*) as total_descansos,
                COALESCE(SUM(duracion_minutos), 0) as total_minutos,
                COALESCE(AVG(duracion_minutos), 0) as promedio_minutos
            FROM tiempos_descanso 
            WHERE fecha >= %s
        ''', (inicio_semana,))
        
        stats_semana = cur.fetchone()
        
        # TOP USUARIOS (más descansos esta semana)
        cur.execute('''
            SELECT 
                u.nombre,
                u.codigo,
                COUNT(*) as total_descansos,
                COALESCE(SUM(t.duracion_minutos), 0) as total_minutos
            FROM tiempos_descanso t
            JOIN usuarios u ON u.id = t.usuario_id
            WHERE t.fecha >= %s
            GROUP BY u.id, u.nombre, u.codigo
            ORDER BY total_descansos DESC
            LIMIT 10
        ''', (inicio_semana,))
        
        top_usuarios = cur.fetchall()
        
        # DESCANSOS POR DÍA (últimos 7 días)
        cur.execute('''
            SELECT 
                fecha,
                COUNT(*) as cantidad,
                COALESCE(SUM(duracion_minutos), 0) as minutos_total
            FROM tiempos_descanso 
            WHERE fecha >= %s
            GROUP BY fecha
            ORDER BY fecha DESC
        ''', (hoy - timedelta(days=6),))
        
        descansos_por_dia = cur.fetchall()
        
        # QUIEN ESTÁ EN DESCANSO AHORA
        cur.execute('''
            SELECT 
                u.nombre,
                u.codigo,
                d.tipo,
                d.inicio,
                EXTRACT(EPOCH FROM (NOW() - d.inicio)) / 60 as minutos_transcurridos
            FROM descansos d
            JOIN usuarios u ON u.id = d.usuario_id
            ORDER BY d.inicio DESC
        ''')
        
        activos_ahora = cur.fetchall()
        
        return render_template('reportes.html',
                             stats_hoy=stats_hoy,
                             stats_semana=stats_semana,
                             top_usuarios=top_usuarios,
                             descansos_por_dia=descansos_por_dia,
                             activos_ahora=activos_ahora,
                             fecha_hoy=hoy.strftime('%Y-%m-%d'))
        
    except Exception as e:
        logger.error(f"Error en reportes: {e}")
        return render_template('reportes.html', 
                             stats_hoy=None, 
                             stats_semana=None,
                             top_usuarios=[], 
                             descansos_por_dia=[], 
                             activos_ahora=[])
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
