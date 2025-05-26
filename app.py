from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'clave-super-secreta'

# Conexión a PostgreSQL

def get_db():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    return conn

# Inicio con lector de tarjetas
@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        tarjeta_raw = request.form.get('tarjeta')
        tarjeta = tarjeta_raw.strip().replace(';', '').replace('?', '')

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

                cur.execute('''SELECT 1 FROM tiempos_descanso WHERE usuario_id = %s AND fecha = %s AND tipo = 'Comida' ''', (usuario_id, fecha_actual))
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
        cur.close()
        conn.close()
        return redirect(url_for('index'))

    cur.execute('''
    SELECT 
        u.nombre, 
        d.tipo, 
        d.inicio, 
        CASE 
            WHEN d.tipo = 'Comida' THEN ROUND(GREATEST(40 - EXTRACT(EPOCH FROM (NOW() - d.inicio)) / 60, 0), 1)
            ELSE ROUND(GREATEST(20 - EXTRACT(EPOCH FROM (NOW() - d.inicio)) / 60, 0), 1)
        END AS tiempo_restante
    FROM descansos d
    JOIN usuarios u ON u.id = d.usuario_id
    ORDER BY d.inicio DESC
''')

    activos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', descansos=activos)

@app.route('/login', methods=['GET', 'POST'])
def login():
    next_page = request.args.get('next')
    if request.method == 'POST':
        if request.form['usuario'] == 'admin' and request.form['clave'] == '1234':
            session['usuario'] = 'admin'
            return redirect(url_for(next_page)) if next_page else redirect(url_for('base_datos'))
    return render_template('login.html')

@app.route('/base_datos', methods=['GET', 'POST'])
def base_datos():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder a esta sección.')
        return redirect(url_for('login', next='base_datos'))

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        nombre = request.form['nombre']
        tarjeta = request.form['tarjeta']
        turno = request.form['turno']
        codigo = request.form['codigo']
        cur.execute('''INSERT INTO usuarios (nombre, tarjeta, turno, codigo) VALUES (%s, %s, %s, %s)''',
                    (nombre, tarjeta, turno, codigo))
        conn.commit()

    cur.execute('SELECT * FROM usuarios')
    usuarios = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('base_datos.html', usuarios=usuarios)

@app.route('/registros')
def registros():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder a esta sección.')
        return redirect(url_for('login', next='registros'))

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('''
        SELECT u.nombre, u.codigo, t.tipo, t.fecha, t.inicio, t.fin, t.duracion_minutos
        FROM tiempos_descanso t
        JOIN usuarios u ON u.id = t.usuario_id
        ORDER BY t.fecha DESC, t.inicio DESC
    ''')
    historial = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('registros.html', historial=historial)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
