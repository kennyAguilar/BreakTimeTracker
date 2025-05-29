import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def agregar_administrador():
    """Script para agregar nuevos administradores"""
    
    # Solicitar datos del nuevo administrador
    print("=== AGREGAR NUEVO ADMINISTRADOR ===")
    usuario = input("Usuario de login: ").strip()
    clave = input("Contraseña: ").strip()
    nombre = input("Nombre completo: ").strip()
    
    if not all([usuario, clave, nombre]):
        print("❌ Todos los campos son requeridos")
        return
    
    if len(usuario) < 3:
        print("❌ El usuario debe tener al menos 3 caracteres")
        return
        
    if len(clave) < 4:
        print("❌ La contraseña debe tener al menos 4 caracteres")
        return
    
    # Conectar a la base de datos
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "breaktimedb"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "password123")
        )
        
        cur = conn.cursor()
        
        # Verificar si el usuario ya existe
        cur.execute('SELECT usuario FROM administradores WHERE usuario = %s', (usuario,))
        if cur.fetchone():
            print(f"❌ El usuario '{usuario}' ya existe")
            return
        
        # Insertar nuevo administrador
        cur.execute('''
            INSERT INTO administradores (usuario, clave, nombre) 
            VALUES (%s, %s, %s)
        ''', (usuario, clave, nombre))
        
        conn.commit()
        print(f"✅ Administrador '{nombre}' agregado exitosamente")
        print(f"   Usuario: {usuario}")
        print(f"   Contraseña: {clave}")
        
    except psycopg2.IntegrityError:
        print(f"❌ El usuario '{usuario}' ya existe")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            conn.close()

def listar_administradores():
    """Mostrar todos los administradores"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "breaktimedb"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "password123")
        )
        
        cur = conn.cursor()
        cur.execute('SELECT id, usuario, nombre, activo, fecha_creacion FROM administradores ORDER BY id')
        admins = cur.fetchall()
        
        print("\n=== ADMINISTRADORES REGISTRADOS ===")
        for admin in admins:
            estado = "✅ Activo" if admin[3] else "❌ Inactivo"
            print(f"ID: {admin[0]} | Usuario: {admin[1]} | Nombre: {admin[2]} | {estado}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    while True:
        print("\n=== GESTIÓN DE ADMINISTRADORES ===")
        print("1. Agregar administrador")
        print("2. Listar administradores")
        print("3. Salir")
        
        opcion = input("Selecciona una opción: ").strip()
        
        if opcion == "1":
            agregar_administrador()
        elif opcion == "2":
            listar_administradores()
        elif opcion == "3":
            break
        else:
            print("❌ Opción inválida")