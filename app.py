from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave-super-secreta'

# Conexión a PostgreSQL
def get_db():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="breaktimedb",
        user="postgres",
        password="9635979"
    )
    return conn

# Inicio con lector de tarjetas
@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST':
        tarjeta_raw = request.form.get('tarjeta')
        tarjeta = tarjeta_raw.strip().replace(';', '').replace('?', '')
        cursor.execute('SELECT * FROM usuarios WHERE tarjeta = %s', (tarjeta,))
        usuario = cursor.fetchone()

        if usuario:
            usuario_id = usuario['id']
            cursor.execute('SELECT * FROM descansos WHERE usuario_id = %s', (usuario_id,))
            descanso_activo = cursor.fetchone()

            ahora = datetime.now()
            fecha_actual = ahora.strftime('%Y-%m-%d')
            hora_actual = ahora.strftime('%H:%M:%S')

            if descanso_activo:
                inicio = descanso_activo['inicio']
                duracion = int((ahora - inicio).total_seconds() / 60)

                tipo_descanso = 'Descanso'
                cursor.execute('''
                    SELECT 1 FROM tiempos_descanso
                    WHERE usuario_id = %s AND fecha = %s AND tipo = 'Comida'
                ''', (usuario_id, fecha_actual))
                ya_tuvo_40 = cursor.fetchone()

                if duracion >= 30 and not ya_tuvo_40:
                    tipo_descanso = 'Comida'

                cursor.execute('''
                    INSERT INTO tiempos_descanso (usuario_id, tipo, fecha, inicio, fin, duracion_minutos)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (usuario_id, tipo_descanso, fecha_actual, inicio.strftime('%H:%M:%S'), hora_actual, duracion))

                cursor.execute('DELETE FROM descansos WHERE id = %s', (descanso_activo['id'],))
            else:
                cursor.execute('''
                    INSERT INTO descansos (usuario_id, tipo, inicio)
                    VALUES (%s, %s, %s)
                ''', (usuario_id, 'Pendiente', ahora))

            conn.commit()
        return redirect(url_for('index'))

    cursor.execute('''
        SELECT u.nombre, u.codigo, d.tipo, d.inicio
        FROM descansos d
        JOIN usuarios u ON u.id = d.usuario_id
        ORDER BY d.inicio DESC
    ''')
    activos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', descansos=activos)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    next_page = request.args.get('next')
    if request.method == 'POST':
        if request.form['usuario'] == 'admin' and request.form['clave'] == '1234':
            session['usuario'] = 'admin'
            return redirect(url_for(next_page)) if next_page else redirect(url_for('base_datos'))
    return render_template('login.html')

# Base de datos de asistentes
@app.route('/base_datos', methods=['GET', 'POST'])
def base_datos():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder a esta sección.')
        return redirect(url_for('login', next='base_datos'))

    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    if request.method == 'POST':
        nombre = request.form['nombre']
        tarjeta = request.form['tarjeta']
        turno = request.form['turno']
        codigo = request.form['codigo']
        cursor.execute('''
            INSERT INTO usuarios (nombre, tarjeta, turno, codigo)
            VALUES (%s, %s, %s, %s)
        ''', (nombre, tarjeta, turno, codigo))
        conn.commit()

    cursor.execute('SELECT * FROM usuarios')
    usuarios = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('base_datos.html', usuarios=usuarios)

# Historial de descansos
@app.route('/registros')
def registros():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder a esta sección.')
        return redirect(url_for('login', next='registros'))

    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('''
        SELECT u.nombre, u.codigo, t.tipo, t.fecha, t.inicio, t.fin, t.duracion_minutos
        FROM tiempos_descanso t
        JOIN usuarios u ON u.id = t.usuario_id
        ORDER BY t.fecha DESC, t.inicio DESC
    ''')
    registros = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('registros.html', historial=registros)

# Cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
