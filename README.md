# ObraDu - Backend API

Repositorio del backend de **ObraDu**, un sistema integral para la gestión de obras.
Esta API RESTful proporciona todos los servicios necesarios para administrar obras, empleados, inventario de materiales, flota de vehículos y control de asistencias/tareas.

## Tecnologías Utilizadas

Este proyecto ha sido desarrollado siguiendo las mejores prácticas de la industria, utilizando un stack moderno y eficiente:

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python)
* **Base de Datos:** MySQL / MariaDB
* **ORM:** SQLAlchemy
* **Validación de Datos:** Pydantic
* **Autenticación y Seguridad:** JSON Web Tokens (JWT) y Passlib (Bcrypt)

## Características Principales

* **Autenticación Segura:** Sistema de login con encriptación de contraseñas y generación de tokens JWT.
* **Control de Roles (RBAC):** Permisos específicos dependiendo de si el usuario es `JEFE` o `EMPLEADO`.
* **Gestión de Obras:** Creación, edición y cálculo de progreso automático de los proyectos.
* **Control de Personal y Tareas:** Fichaje de horas (asistencias) y marcado de tareas completadas.
* **Inventario y Logística:** Administración del stock de materiales y asignación a obras específicas.
* **Gestión de Flota:** Control de estado de vehículos (Disponible, En Uso, Taller).

## Instalación y Configuración Local

Sigue estos pasos para levantar el entorno de desarrollo en tu máquina local:

### 1. Clonar el repositorio
```bash
git clone [https://github.com/TuUsuario/ObraDu_Proyecto_Intermodular.git](https://github.com/TuUsuario/ObraDu_Proyecto_Intermodular.git)
cd ObraDu_Proyecto_Intermodular/backend
```
### 2. Crear y activar el entorno virtual

```bash
# En Windows
python -m venv venv
venv\Scripts\activate

# En macOS/Linux
python3 -m venv venv
source venv/bin/activate
```
### 3. Instalar las dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar las variables de entorno

Para que el proyecto funcione en tu equipo, debes crear tu propio archivo llamado .env en la raíz de la carpeta backend con la siguiente estructura, utilizando los datos de tu propia base de datos local:

```bash
DATABASE_URL="mysql+pymysql://tu_usuario:tu_contraseña@localhost:3306/obradu"
SECRET_KEY=""
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 5. Iniciar el servidor
Arranca la aplicación mediante Uvicorn:
```bash
uvicorn main:app --reload
```
El servidor estará disponible y escuchando en http://localhost:8000.



#
#
#
#
*Desarrollado por Ángel Morales Sánchez como Proyecto Intermodular.*