BreakTime Tracker - Versión Portable con Neon.tech

REQUISITOS:
- Conexión a Internet.
- Python 3.10+ instalado.
- psycopg2-binary y flask instalados.

PASOS:
1️⃣ Abre esta carpeta en tu terminal (PowerShell o CMD).
2️⃣ Si es la primera vez, instala las dependencias:
   pip install flask psycopg2-binary python-dotenv
3️⃣ Ejecuta la aplicación:
   python app.py
4️⃣ Abre tu navegador en: http://127.0.0.1:5000

USANDO NEON.TECH:
- La base de datos está en la nube. Se conecta automáticamente usando los datos del archivo .env.

INFORMACIÓN ADICIONAL:
- Si deseas reiniciar la base de datos, ejecuta init_db.py (esto es opcional y debe hacerse con cuidado).
- Si deseas agregar usuarios rápidamente, puedes usar agregar_usuario.py.