# IMPORTACIONES - Como traer herramientas que necesitamos
from flask import Flask, render_template, request, redirect, url_for, session
# Flask es como el motor de nuestro sitio web
# render_template = mostrar páginas web
# request = recibir información del usuario
# redirect = enviar al usuario a otra página
# session = recordar quien está conectado
# flash = eliminado - ya no se usa

from datetime import datetime  # Para trabajar con fechas y horas
import psycopg2  # Para conectarse a la base de datos PostgreSQL
import psycopg2.extras  # Herramientas extra para la base de datos
import os  # Para acceder a configuraciones del sistema
from dotenv import load_dotenv  # Para leer configuraciones secretas
import logging  # Para guardar registros de lo que pasa en la app

# CONFIGURACIÓN INICIAL - Como preparar todo antes de empezar
logging.basicConfig(level=logging.INFO)  # Activar el sistema de registros
logger = logging.getLogger(__name__)  # Crear nuestro registrador personal

load_dotenv()  # Cargar configuraciones secretas desde un archivo .env

app = Flask(__name__)  # Crear nuestra aplicación web
# Una clave secreta para proteger la información de usuarios conectados
app.secret_key = os.getenv('SECRET_KEY', 'clave-temporal-cambiar-en-produccion')

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
            tarjeta_raw = request.form.get('tarjeta')
            tarjeta = validar_tarjeta(tarjeta_raw)
            
            if not tarjeta:
                # Sin mensajes - solo redireccionar
                return redirect(url_for('index'))

            cur.execute('SELECT * FROM usuarios WHERE tarjeta = %s', (tarjeta,))
            usuario = cur.fetchone()

            if usuario:
                usuario_id = usuario['id']
                nombre_usuario = usuario['nombre']

                cur.execute('SELECT * FROM descansos WHERE usuario_id = %s', (usuario_id,))
                descanso_activo = cur.fetchone()

                ahora = datetime.now()
                fecha_actual = ahora.date()
                hora_actual = ahora.time()

                if descanso_activo:
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
        ahora = datetime.now()
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
    Solo quien sepa el usuario y contraseña puede entrar.
    """
    next_page = request.args.get('next')
    
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        clave = request.form.get('clave', '').strip()
        
        if not usuario or not clave:
            # Sin flash - solo redireccionar
            return render_template('login.html')
            
        admin_user = os.getenv('ADMIN_USER', 'admin')
        admin_pass = os.getenv('ADMIN_PASS', '1234')
        
        if usuario == admin_user and clave == admin_pass:
            session['usuario'] = 'admin'
            session.permanent = True
            # Sin flash - solo redireccionar
            return redirect(url_for(next_page)) if next_page else redirect(url_for('base_datos'))
        else:
            # Sin flash - solo redireccionar
            return render_template('login.html')
            
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
            tarjeta = request.form.get('tarjeta', '').strip()
            turno = request.form.get('turno', '').strip()
            codigo = request.form.get('codigo', '').strip()
            
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

# PÁGINA DE REGISTROS - Sin flash()
@app.route('/registros')
def registros():
    """
    Como revisar un libro de historial donde se ve todo lo que ha pasado.
    Quién tomó descansos, cuándo y por cuánto tiempo.
    """
    if 'usuario' not in session:
        # Sin flash - solo redireccionar
        return redirect(url_for('login', next='registros'))

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        cur.execute('''
            SELECT u.nombre, u.codigo, t.tipo, t.fecha, t.inicio, t.fin, t.duracion_minutos
            FROM tiempos_descanso t
            JOIN usuarios u ON u.id = t.usuario_id
            ORDER BY t.fecha DESC, t.inicio DESC
            LIMIT 100
        ''')
        historial = cur.fetchall()
        return render_template('registros.html', historial=historial)
        
    except Exception as e:
        logger.error(f"Error en registros: {e}")
        # Sin flash - solo retornar página vacía
        return render_template('registros.html', historial=[])
    finally:
        if conn:
            conn.close()

# CERRAR SESIÓN - Sin flash()
@app.route('/logout')
def logout():
    """
    Como cerrar sesión en una computadora pública.
    Olvida que el administrador estaba conectado.
    """
    session.clear()
    # Sin flash - solo redireccionar
    return redirect(url_for('index'))

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
    """
    Esto es como presionar el botón de 'encender' de todo el sistema.
    debug=True significa que si algo sale mal, nos dirá exactamente qué fue.
    """
    app.run(debug=True, host='0.0.0.0', port=5000)
