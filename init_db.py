import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Conexión a PostgreSQL usando variables de entorno
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
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

# Crear tabla de administradores
cursor.execute('''
CREATE TABLE IF NOT EXISTS administradores (
    id SERIAL PRIMARY KEY,
    usuario TEXT NOT NULL UNIQUE,
    clave TEXT NOT NULL,
    nombre TEXT NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Insertar administrador por defecto
cursor.execute('''
INSERT INTO administradores (usuario, clave, nombre) 
VALUES ('admin', '1234', 'Administrador Principal')
ON CONFLICT (usuario) DO NOTHING
''')

conn.commit()
conn.close()

print("✅ Base de datos PostgreSQL inicializada correctamente.")
