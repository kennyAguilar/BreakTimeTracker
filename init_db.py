import sqlite3

# Conectar o crear la base de datos
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Crear tabla de usuarios
cursor.execute('''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    tarjeta TEXT NOT NULL UNIQUE,
    turno TEXT NOT NULL,
    codigo TEXT NOT NULL UNIQUE
)
''')

# Crear tabla de descansos activos (en curso)
cursor.execute('''
CREATE TABLE IF NOT EXISTS descansos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    inicio TEXT NOT NULL,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
)
''')

# Crear tabla de tiempos de descanso finalizados
cursor.execute('''
CREATE TABLE IF NOT EXISTS tiempos_descanso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    fecha TEXT NOT NULL,
    inicio TEXT NOT NULL,
    fin TEXT,
    duracion_minutos INTEGER,
    FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
)
''')

conn.commit()
conn.close()

print("✔ Base de datos creada correctamente con las tablas: usuarios, descansos y tiempos_descanso.")
