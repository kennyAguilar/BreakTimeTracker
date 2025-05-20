import psycopg2

# Conexión a la base de datos PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="postgres",
    user="postgres",
    password="9635979"
)

cursor = conn.cursor()

# Datos del usuario de prueba
nombre = "Usuario de Prueba"
tarjeta = "1234567890123456"     # Simula el número leído de tarjeta
turno = "Full"                   # Puede ser Full, Part-Time, Llamado
codigo = "UP22"                  # Código como KA22, UP22, etc.

# Insertar usuario
try:
    cursor.execute('''
        INSERT INTO usuarios (nombre, tarjeta, turno, codigo)
        VALUES (%s, %s, %s, %s)
    ''', (nombre, tarjeta, turno, codigo))
    conn.commit()
    print("✅ Usuario agregado correctamente.")
except Exception as e:
    print("❌ Error al insertar el usuario:", e)

conn.close()
