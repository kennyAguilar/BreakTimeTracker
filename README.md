# 🕐 BreakTimeTracker v2.0

**Sistema profesional de control de tiempos de descanso para empresas**

![BreakTimeTracker](https://img.shields.io/badge/BreakTimeTracker-v2.0-blue?style=for-the-badge)
![Flask](https://img.shields.io/badge/Flask-2.3.3-green?style=flat-square)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11-yellow?style=flat-square)

## 📋 Descripción

BreakTimeTracker es un sistema web completo para el control automatizado de tiempos de descanso en empresas. Permite a los empleados registrar entrada y salida de descansos usando tarjetas RFID o códigos, mientras que los administradores pueden gestionar usuarios y generar reportes detallados.

## ✨ Características Principales

### 🏠 **Lector Universal**
- ✅ Soporte para tarjetas RFID largas
- ✅ Códigos cortos (KA22, CB29, HP30, VS26, etc.)
- ✅ Validación automática de entrada
- ✅ Interface simple tipo "lector industrial"

### ⏰ **Control Inteligente de Tiempos**
- ✅ Descansos cortos: 20 minutos máximo
- ✅ Tiempo de comida: 40 minutos máximo
- ✅ Detección automática según duración
- ✅ Contador en tiempo real
- ✅ Zona horaria Punta Arenas (Chile)

### 👥 **Gestión de Usuarios**
- ✅ CRUD completo (Crear, Leer, Actualizar, Eliminar)
- ✅ Gestión de tarjetas y códigos
- ✅ Turnos de trabajo configurables
- ✅ Validación de datos únicos

### 📊 **Reportes y Estadísticas**
- ✅ Dashboard en tiempo real
- ✅ Historial completo filtrable
- ✅ Exportación a CSV
- ✅ Estadísticas por día/semana
- ✅ Top usuarios más activos

### 🔒 **Seguridad Avanzada**
- ✅ Sistema multi-administrador
- ✅ Autenticación desde base de datos
- ✅ Auto-logout por inactividad (30 min)
- ✅ Navegación segura área administrativa
- ✅ Logs de auditoría completos

## 🛠️ Tecnologías Utilizadas

| Componente | Tecnología | Versión |
|------------|------------|---------|
| **Backend** | Python Flask | 2.3.3 |
| **Base de Datos** | PostgreSQL | 15+ |
| **Frontend** | HTML5 + TailwindCSS | 2.2.19 |
| **Zona Horaria** | pytz | 2023.3 |
| **Deploy** | Render.com | - |
| **DB Hosting** | Neon.tech | - |

## 🚀 Instalación y Configuración

### **Prerrequisitos**
- Python 3.11+
- PostgreSQL 15+
- Git

### **1. Clonar repositorio**
```bash
git clone https://github.com/tu-usuario/BreakTimeTracker.git
cd BreakTimeTracker
```

### **2. Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows
```

### **3. Instalar dependencias**
```bash
pip install -r requirements.txt
```

### **4. Configurar variables de entorno**
Crear archivo `.env`:
```env
DB_HOST=tu-host-neon.com
DB_PORT=5432
DB_NAME=breaktimedb
DB_USER=tu-usuario
DB_PASSWORD=tu-password
SECRET_KEY=tu-clave-secreta-super-segura
TZ=America/Punta_Arenas
```

### **5. Crear base de datos**
```sql
-- Crear tablas necesarias
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    tarjeta VARCHAR(50) UNIQUE NOT NULL,
    turno VARCHAR(20) NOT NULL,
    codigo VARCHAR(10) UNIQUE NOT NULL
);

CREATE TABLE administradores (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(50) UNIQUE NOT NULL,
    clave VARCHAR(100) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

CREATE TABLE descansos (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    tipo VARCHAR(20) DEFAULT 'Pendiente',
    inicio TIMESTAMP NOT NULL
);

CREATE TABLE tiempos_descanso (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    tipo VARCHAR(20) NOT NULL,
    fecha DATE NOT NULL,
    inicio TIME NOT NULL,
    fin TIME NOT NULL,
    duracion_minutos INTEGER NOT NULL
);
```

### **6. Datos de ejemplo**
```sql
-- Usuarios de ejemplo
INSERT INTO usuarios (nombre, tarjeta, turno, codigo) VALUES
('Kenny Aguilar', '1234567890123', 'Mañana', 'KA22'),
('Carlos Bedon', '9876543210987', 'Tarde', 'CB29'),
('Hector Poblete', '5555666677778', 'Noche', 'HP30');

-- Administrador de ejemplo
INSERT INTO administradores (usuario, clave, nombre, activo) VALUES
('admin', 'password123', 'Administrador Principal', TRUE);
```

### **7. Ejecutar aplicación**
```bash
python app.py
```

Acceder a: `http://127.0.0.1:5000`

## 🌐 Deploy en Producción

### **Render.com**
1. Conectar repositorio GitHub
2. Configurar variables de entorno
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn --bind 0.0.0.0:$PORT app:app`

### **Variables de entorno requeridas:**
```
TZ=America/Punta_Arenas
DB_HOST=tu-host-neon
DB_PORT=5432
DB_NAME=tu-database
DB_USER=tu-usuario
DB_PASSWORD=tu-password
SECRET_KEY=clave-super-secreta
```

## 📱 Uso del Sistema

### **👷 Para Empleados**
1. **Entrar a descanso**: Deslizar tarjeta o escribir código (ej: KA22)
2. **Ver tiempo restante**: Pantalla principal muestra tiempo en tiempo real
3. **Salir de descanso**: Volver a deslizar tarjeta o escribir código

### **👨‍💼 Para Administradores**
1. **Login**: `/login` con credenciales de base de datos
2. **Gestión usuarios**: Agregar, editar, eliminar empleados
3. **Ver registros**: Historial completo con filtros
4. **Generar reportes**: Dashboard con estadísticas
5. **Exportar datos**: Descargar CSV con registros
6. **Logout**: Obligatorio para volver al lector

## 📊 Estructura del Proyecto

```
BreakTimeTracker/
├── 📄 app.py                 # Aplicación principal Flask
├── 📄 requirements.txt       # Dependencias Python
├── 📄 .env.example          # Ejemplo variables entorno
├── 📄 README.md             # Este archivo
├── 📁 templates/            # Plantillas HTML
│   ├── 📄 index.html        # Lector principal
│   ├── 📄 login.html        # Login administrativo
│   ├── 📄 base_datos.html   # Gestión usuarios
│   ├── 📄 registros.html    # Historial
│   ├── 📄 reportes.html     # Dashboard
│   ├── 📄 editar_usuario.html
│   └── 📄 error.html        # Página de errores
├── 📁 static/               # Archivos estáticos
│   └── 📄 style.css         # Estilos personalizados
└── 📁 venv/                 # Entorno virtual (no incluir en Git)
```

## 🔧 API Endpoints

| Ruta | Método | Descripción | Autenticación |
|------|--------|-------------|---------------|
| `/` | GET/POST | Lector principal | No |
| `/login` | GET/POST | Login administrativo | No |
| `/base_datos` | GET/POST | Gestión usuarios | Sí |
| `/registros` | GET | Historial registros | Sí |
| `/reportes` | GET | Dashboard estadísticas | Sí |
| `/exportar_csv` | GET | Exportar CSV | Sí |
| `/logout` | GET | Cerrar sesión | Sí |

## 🛡️ Características de Seguridad

- ✅ **Autenticación multi-admin** desde base de datos
- ✅ **Auto-logout** por inactividad (30 minutos)
- ✅ **Navegación controlada** área administrativa
- ✅ **Validación de datos** en formularios
- ✅ **Logs de auditoría** para acciones críticas
- ✅ **Manejo seguro** de sesiones y cookies
- ✅ **Protección SQL injection** con prepared statements

## 🔄 Flujo de Trabajo

```mermaid
graph TD
    A[Empleado llega] --> B[Desliza tarjeta/escribe código]
    B --> C{¿Usuario válido?}
    C -->|No| D[Pantalla principal sin cambios]
    C -->|Sí| E{¿Ya está en descanso?}
    E -->|No| F[Registrar ENTRADA a descanso]
    E -->|Sí| G[Calcular duración]
    G --> H{¿Duración >= 30 min?}
    H -->|Sí| I[Registrar como COMIDA]
    H -->|No| J[Registrar como DESCANSO]
    F --> K[Mostrar en pantalla principal]
    I --> K
    J --> K
    K --> L[Actualizar tiempo restante cada minuto]
```

## 📈 Roadmap Futuro

- [ ] **App móvil** para empleados
- [ ] **Notificaciones push** cuando se acaba el tiempo
- [ ] **Integración** con sistemas de nómina
- [ ] **API REST** para integraciones externas
- [ ] **Dashboard gerencial** con métricas avanzadas
- [ ] **Soporte multi-empresa** en una instancia
- [ ] **Backup automático** de base de datos

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Para contribuir:

1. Fork el proyecto
2. Crear rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 👨‍💻 Autor

**Tu Nombre**
- GitHub: [@tu-usuario](https://github.com/tu-usuario)
- Email: tu-email@ejemplo.com

## 🏢 Casos de Uso

✅ **Empresas manufactureras** con turnos rotativos  
✅ **Call centers** con control estricto de tiempo  
✅ **Oficinas corporativas** con políticas de descanso  
✅ **Retail** con múltiples empleados por turno  
✅ **Hospitales/clínicas** con personal 24/7  

## 📞 Soporte

Si encuentras algún problema o tienes sugerencias:

1. 📧 Crear **Issue** en GitHub
2. 📱 Contactar por email
3. 📋 Incluir logs y pasos para reproducir

---

⭐ **¡Si te gusta el proyecto, dale una estrella en GitHub!** ⭐

*Desarrollado con ❤️ en Punta Arenas, Chile* 🇨🇱
