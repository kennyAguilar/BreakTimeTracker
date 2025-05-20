import psycopg2

# Conexión a PostgreSQL usando psycopg2 dentro de un bloque try/except
try:
    conn = psycopg2.connect(        # Intenta establecer conexión con la base de datos
        host="localhost",           # Dirección del servidor (localhost si está en tu propio equipo)
        port=5432,                  # Puerto por defecto de PostgreSQL
        database="breaktimedb",        # Nombre de la base de datos (cámbialo si estás usando otro)
        user="postgres",            # Usuario con acceso a la base de datos
        password="9635979"          # Contraseña del usuario (modifícala si es distinta)
    )
    cursor = conn.cursor()

    # Crear tabla de usuarios
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        nombre TEXT NOT NULL,
        tarjeta TEXT NOT NULL UNIQUE,
        turno TEXT NOT NULL,
        codigo TEXT NOT NULL UNIQUE
    )
    ''')

    # Crear tabla de descansos activos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS descansos (
        id SERIAL PRIMARY KEY,
        usuario_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,
        inicio TIMESTAMP NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )
    ''')

    # Crear tabla de tiempos de descanso finalizados
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tiempos_descanso (
        id SERIAL PRIMARY KEY,
        usuario_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,
        fecha DATE NOT NULL,
        inicio TIME NOT NULL,
        fin TIME,
        duracion_minutos INTEGER,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
    )
    ''')

    conn.commit()
    print("✔ Tablas creadas correctamente en PostgreSQL.")

except Exception as e:
    print(f"Error: {e}")

finally:
    if 'conn' in locals() and conn:
        conn.close()
