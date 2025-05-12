from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave-super-secreta'

# Conexión a la base de datos

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Inicio con lector de tarjetas
@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db()
    if request.method == 'POST':
        tarjeta_raw = request.form.get('tarjeta')
        tarjeta = tarjeta_raw.strip().replace(';', '').replace('?', '')
        usuario = conn.execute('SELECT * FROM usuarios WHERE tarjeta = ?', (tarjeta,)).fetchone()

        if usuario:
            usuario_id = usuario['id']

            descanso_activo = conn.execute('''
                SELECT * FROM descansos WHERE usuario_id = ?
            ''', (usuario_id,)).fetchone()

            ahora = datetime.now()
            fecha_actual = ahora.strftime('%Y-%m-%d')
            hora_actual = ahora.strftime('%H:%M:%S')

            if descanso_activo:
                # Terminar descanso y pasarlo a tiempos_descanso
                inicio = datetime.strptime(descanso_activo['inicio'], '%Y-%m-%d %H:%M:%S')
                duracion = int((ahora - inicio).total_seconds() / 60)

                # Verificar si ya tuvo un descanso de 40 este día
                tipo_descanso = 'Descanso'
                ya_tuvo_40 = conn.execute('''
                    SELECT 1 FROM tiempos_descanso
                    WHERE usuario_id = ? AND fecha = ? AND tipo = 'Comida'
                ''', (usuario_id, fecha_actual)).fetchone()

                if duracion >= 30 and not ya_tuvo_40:
                    tipo_descanso = 'Comida'

                conn.execute('''
                    INSERT INTO tiempos_descanso (usuario_id, tipo, fecha, inicio, fin, duracion_minutos)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (usuario_id, tipo_descanso, fecha_actual, inicio.strftime('%H:%M:%S'), hora_actual, duracion))

                conn.execute('DELETE FROM descansos WHERE id = ?', (descanso_activo['id'],))
            else:
                # Iniciar descanso (el tipo se decide al finalizar)
                conn.execute('''
                    INSERT INTO descansos (usuario_id, tipo, inicio)
                    VALUES (?, ?, ?)
                ''', (usuario_id, 'Pendiente', ahora.strftime('%Y-%m-%d %H:%M:%S')))

            conn.commit()
        return redirect(url_for('index'))

    activos = conn.execute('''
        SELECT u.nombre, u.codigo, d.tipo, d.inicio
        FROM descansos d
        JOIN usuarios u ON u.id = d.usuario_id
        ORDER BY d.inicio DESC
    ''').fetchall()
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
    if request.method == 'POST':
        nombre = request.form['nombre']
        tarjeta = request.form['tarjeta']
        turno = request.form['turno']
        codigo = request.form['codigo']
        conn.execute('INSERT INTO usuarios (nombre, tarjeta, turno, codigo) VALUES (?, ?, ?, ?)',
                     (nombre, tarjeta, turno, codigo))
        conn.commit()

    usuarios = conn.execute('SELECT * FROM usuarios').fetchall()
    conn.close()
    return render_template('base_datos.html', usuarios=usuarios)

# Historial de descansos
@app.route('/registros')
def registros():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder a esta sección.')
        return redirect(url_for('login', next='registros'))

    conn = get_db()
    registros = conn.execute('''
        SELECT u.nombre, u.codigo, t.tipo, t.fecha, t.inicio, t.fin, t.duracion_minutos
        FROM tiempos_descanso t
        JOIN usuarios u ON u.id = t.usuario_id
        ORDER BY t.fecha DESC, t.inicio DESC
    ''').fetchall()
    conn.close()
    return render_template('registros.html', historial=registros)

# Cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
