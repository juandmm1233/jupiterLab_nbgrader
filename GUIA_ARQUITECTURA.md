# Guía de arquitectura: JupyterHub + JupyterLab + nbgrader

Documento de referencia para desplegar un entorno educativo interactivo con:

1. **Registro de estudiantes** con usuario y contraseña (`jupyterhub-nativeauthenticator`).
2. **Aprobación manual** de cuentas por el profesor (admin) antes de permitir el acceso.
3. **Calificación automática** con nbgrader y la pestaña Formgrader.
4. **Aislamiento de roles y volúmenes**, incluido el directorio de intercambio (exchange) de nbgrader.

La implementación vive en este repositorio. Esta guía explica *por qué* y *cómo* está armada, con los comandos y permisos necesarios.

---

## 1. Arquitectura general

```
┌─────────────────────────────────────────────────────────────┐
│  Host (Docker)                                              │
│                                                             │
│  ┌──────────────────────┐     red: jupyterhub-network       │
│  │ JupyterHub           │◄────────────────────────────────┐ │
│  │ NativeAuthenticator  │                                 │ │
│  │ DockerSpawner        │── spawnea ──┐                   │ │
│  └──────────┬───────────┘             │                   │ │
│             │                         ▼                   │ │
│             │              ┌──────────────────┐           │ │
│             │              │ Contenedor       │           │ │
│             │              │ jupyter-<user>   │───────────┘ │
│             │              │ JupyterLab +     │             │
│             │              │ nbgrader         │             │
│             │              └────┬────────┬────┘             │
│             │                   │        │                  │
│  volumen    │    volumen        │        │  volumen         │
│  jupyterhub-data   privado      │        │  nbgrader-exchange
│  (DB Hub)   │  jupyterhub-user- │        │  (/srv/nbgrader/ │
│             │  {username}       │        │   exchange)      │
└─────────────┴───────────────────┴────────┴──────────────────┘
```

| Componente | Rol |
|---|---|
| **JupyterHub** | Autenticación, autorización, panel admin y lanzamiento de servidores |
| **NativeAuthenticator** | Signup + bloqueo hasta aprobación en `/hub/authorize` |
| **DockerSpawner** | Un contenedor aislado por usuario, JupyterLab por defecto (`/lab`) |
| **nbgrader** | Tareas, tests ocultos, Formgrader (profesor) y Assignment List (alumno) |
| **Idle culler** | Apaga servidores inactivos tras 1 hora |

---

## 2. Prerrequisitos e instalación (Ubuntu Server)

### 2.1 Instalar Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker
docker compose version   # debe ser Compose v2
```

### 2.2 Clonar y configurar

Desde la raíz del proyecto (`jupiterLab_nbgrader/`):

```bash
cp .env.example .env
nano .env
```

Variables relevantes en `.env`:

| Variable | Ejemplo | Significado |
|---|---|---|
| `HUB_PORT` | `8000` | Puerto publicado en el host |
| `JUPYTERHUB_ADMIN` | `admin` | Profesor(es); separados por coma |
| `NBGRADER_COURSE_ID` | `curso-2026` | ID del curso (slug, sin espacios) |
| `NBGRADER_TIMEZONE` | `America/Bogota` | Zona horaria de deadlines |
| `USER_MEM_LIMIT` | `2G` | Memoria por contenedor de usuario |
| `USER_CPU_LIMIT` | `1.0` | CPU por contenedor de usuario |

### 2.3 Construir y arrancar

```bash
docker compose build
docker compose up -d
docker compose logs -f jupyterhub
```

Abrir `http://<IP-o-localhost>:8000`.

### 2.4 Primer arranque: crear y activar el profesor

1. Ir a **Signup** (`/hub/signup`) y registrar el usuario definido en `JUPYTERHUB_ADMIN` (p. ej. `admin`) con su contraseña.
2. Iniciar sesión. Al ser admin, JupyterHub lo autoriza.
3. Sembrar scripts del curso en el volumen del profesor:

   ```bash
   ./scripts/seed-instructor.sh admin
   ```

4. En la terminal de JupyterLab del profesor:

   ```bash
   bash ~/work/init-course.sh
   ```

5. Cuando un estudiante se registre, el profesor lo aprueba en `/hub/authorize` antes de que pueda entrar.

Firewall opcional:

```bash
sudo ufw allow 8000/tcp
```

Para HTTPS en producción, poner Caddy/Nginx/Traefik delante (ver [README.md](README.md) sección 3).

---

## 3. Archivos de configuración

### 3.1 `docker-compose.yml`

Define:

- Red `jupyterhub-network` (Hub y contenedores de usuario).
- Volumen `jupyterhub-data` → DB y cookie secret del Hub.
- Volumen `nbgrader-exchange` → directorio de intercambio compartido.
- Servicio `jupyterhub` con el socket Docker montado (necesario para DockerSpawner).
- Servicio `singleuser-builder` que solo construye la imagen `jupyterlab-singleuser:latest`.

Los workspaces privados `jupyterhub-user-{username}` los crea DockerSpawner bajo demanda; no hace falta declararlos en compose.

### 3.2 `jupyterhub/Dockerfile`

Imagen base `jupyterhub/jupyterhub:5.2` e instalación de:

- `dockerspawner`
- `jupyterhub-nativeauthenticator`
- `jupyterhub-idle-culler`

Copia `jupyterhub_config.py` a `/srv/jupyterhub/`.

### 3.3 `jupyterhub/jupyterhub_config.py` (reglas de usuarios)

Fragmentos esenciales y su significado:

```python
# Autenticador nativo: registro en /hub/signup
c.JupyterHub.authenticator_class = "nativeauthenticator.NativeAuthenticator"

admin_users = os.environ.get("JUPYTERHUB_ADMIN", "admin").split(",")
c.Authenticator.admin_users = {u.strip() for u in admin_users if u.strip()}

# JupyterHub 5.x: allow_all deja pasar a la capa del autenticador.
# La aprobación real la hace NativeAuthenticator (flag is_authorized).
c.Authenticator.allow_all = True

# Registro abierto, pero SIN acceso inmediato (aprobación manual).
c.NativeAuthenticator.open_signup = False
c.NativeAuthenticator.check_common_password = True
c.NativeAuthenticator.minimum_password_length = 8
```

Spawner y volúmenes:

```python
c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"
c.DockerSpawner.default_url = "/lab"   # JupyterLab por defecto
c.DockerSpawner.notebook_dir = "/home/jovyan/work"
c.DockerSpawner.volumes = {
    "jupyterhub-user-{username}": "/home/jovyan/work",   # privado
    "nbgrader-exchange": "/srv/nbgrader/exchange",       # compartido
}
```

Roles RBAC (nbgrader consulta grupos del Hub):

```python
c.JupyterHub.load_roles = [
    {
        "name": "user",
        "scopes": ["self", "read:groups", "list:groups"],
    },
    # + rol idle-culler-role para el servicio de culling
]
```

Grupo de instructores (convención nbgrader):

```python
NBGRADER_COURSE_ID = os.environ.get("NBGRADER_COURSE_ID", "curso-2026")
c.JupyterHub.load_groups = {
    f"formgrade-{NBGRADER_COURSE_ID}": {
        "users": [u.strip() for u in admin_users if u.strip()],
    },
}
```

| Quién | Cómo se identifica | Qué ve en JupyterLab |
|---|---|---|
| Profesor / admin | En `admin_users` y en `formgrade-{course_id}` | Formgrader, Create Assignment, Course List |
| Estudiante | Usuario aprobado, fuera de `formgrade-*` | Assignment List (Fetch / Submit / Feedback) |
| Usuario recién registrado | En BD de NativeAuthenticator con `is_authorized=False` | No puede iniciar sesión hasta `/hub/authorize` |

### 3.4 `singleuser/Dockerfile`

Imagen `quay.io/jupyter/scipy-notebook` +:

- Paquetes: `nbgrader`, `nbgitpuller`, `jupyterlab-git`, cliente `jupyterhub`.
- Extensiones de nbgrader habilitadas a nivel sistema (Formgrader, Assignment List, etc.).
- Punto de montaje `/srv/nbgrader/exchange` preparado con permisos base.
- Config global en `/etc/jupyter/nbgrader_config.py`.

La UI de Formgrader/Create Assignment se oculta sola a no-instructores gracias a `JupyterHubAuthPlugin`.

### 3.5 `singleuser/nbgrader_config.py`

```python
c.Exchange.root = "/srv/nbgrader/exchange"
c.Exchange.timezone = os.environ.get("NBGRADER_TIMEZONE", "America/Bogota")
c.CourseDirectory.course_id = os.environ.get("NBGRADER_COURSE_ID", "curso-2026")
c.Authenticator.plugin_class = "nbgrader.auth.JupyterHubAuthPlugin"
```

El plugin usa `JUPYTERHUB_API_TOKEN` / URL inyectados por el Hub en cada servidor de usuario para preguntar: ¿pertenece a `formgrade-{course_id}`?

---

## 4. Autenticación y registro (requisitos 1 y 2)

### Flujo del estudiante

1. Abre `/hub/signup` y crea usuario + contraseña.
2. Intenta login → **rechazado** mientras no esté autorizado (`open_signup = False`).
3. El profesor entra a `/hub/authorize` y aprueba la cuenta.
4. El estudiante inicia sesión y DockerSpawner levanta su contenedor con JupyterLab.

### Flujo del profesor (admin)

1. Se registra una sola vez con el nombre de `JUPYTERHUB_ADMIN`.
2. Gestiona usuarios en el panel del Hub y en `/hub/authorize`.
3. Pertenece automáticamente a `formgrade-{NBGRADER_COURSE_ID}` → ve Formgrader.

### Seguridad básica ya configurada

- Contraseñas comunes bloqueadas (`check_common_password`).
- Longitud mínima 8.
- Bloqueo temporal tras 5 intentos fallidos (600 s).

---

## 5. Aislamiento de roles y exchange (requisito 4)

### 5.1 Capas de aislamiento

| Capa | Mecanismo | Qué protege |
|---|---|---|
| Contenedor por usuario | DockerSpawner | Procesos y filesystem de cada alumno |
| Volumen privado | `jupyterhub-user-{username}` → `~/work` | Notebooks, `source/`, `gradebook.db` del profesor; trabajo del alumno |
| Exchange compartido | Volumen `nbgrader-exchange` | Solo tareas liberadas, entregas y feedback |
| Permisos Unix en exchange | `0755` / `1733` | Lectura de outbound; escritura sin listar en inbound |
| Roles nbgrader | Grupo `formgrade-*` + AuthPlugin | Quién ve Formgrader vs Assignment List |

El profesor guarda soluciones en `~/work/<course_id>/source/`. Eso **no** se monta en los contenedores de los alumnos. Al hacer **Generate + Release**, nbgrader publica en `outbound/` una versión limpia (sin soluciones ni asserts ocultos visibles en el notebook del alumno).

### 5.2 Estructura del exchange

```
/srv/nbgrader/exchange/<course_id>/
├── outbound/    modo 0755   → profesor Release; alumnos Fetch
├── inbound/     modo 1733   → alumnos Submit; profesor Collect
└── feedback/    modo 0755   → profesor Release Feedback; alumnos Fetch Feedback
```

Significado de `chmod 1733` en `inbound/`:

- Bit sticky (`1xxx`): un usuario no borra archivos de otro (en hosts con UIDs distintos).
- Sin permiso de lectura en el directorio: **no se puede listar** el contenido.
- Con escritura y ejecución: se puede entrar y crear (Submit) archivos propios.

Con DockerSpawner todos los contenedores corren como UID `jovyan` (1000). Por eso el aislamiento entre entregas depende sobre todo de **impedir el listado** de `inbound/`, no de UIDs distintos en el host. Los nombres de entrega incluyen el username; sin listar el directorio, un alumno no puede enumerar las de otros.

### 5.3 Inicialización (Docker) — script oficial

Desde JupyterLab del profesor, tras `seed-instructor.sh`:

```bash
bash ~/work/init-course.sh
```

Ese script (`nbgrader/init-course.sh`):

1. Ejecuta `nbgrader quickstart` y mueve el curso a `~/work/<course_id>/`.
2. Crea `outbound/`, `inbound/`, `feedback/` bajo el exchange.
3. Aplica permisos:

   ```bash
   chmod 0755 "${EXCHANGE_ROOT}/${COURSE_ID}"
   chmod 0755 "${EXCHANGE_ROOT}/${COURSE_ID}/outbound"
   chmod 0755 "${EXCHANGE_ROOT}/${COURSE_ID}/feedback"
   chmod 1733 "${EXCHANGE_ROOT}/${COURSE_ID}/inbound"
   ```

### 5.4 Equivalente en Linux nativo (referencia)

Si se desplegara nbgrader fuera de Docker (instalación clásica en el host), el patrón de permisos sería:

```bash
sudo mkdir -p /srv/nbgrader/exchange
sudo chown root:root /srv/nbgrader/exchange
sudo chmod 755 /srv/nbgrader/exchange

# Tras crear el curso (como instructor o con un script de init):
COURSE_ID=curso-2026
sudo mkdir -p /srv/nbgrader/exchange/${COURSE_ID}/{outbound,inbound,feedback}
sudo chmod 0755 /srv/nbgrader/exchange/${COURSE_ID}
sudo chmod 0755 /srv/nbgrader/exchange/${COURSE_ID}/outbound
sudo chmod 0755 /srv/nbgrader/exchange/${COURSE_ID}/feedback
sudo chmod 1733 /srv/nbgrader/exchange/${COURSE_ID}/inbound
```

En este proyecto **no hace falta** ejecutar esos `sudo` en el host: el volumen Docker y `init-course.sh` ya los aplican dentro de los contenedores.

### 5.5 Qué ve cada rol en disco

| Ruta | Profesor | Estudiante |
|---|---|---|
| `~/work/<course>/source/` (soluciones) | Sí (volumen propio) | No montado |
| `~/work/<course>/submitted/`, `gradebook.db` | Sí | No montado |
| Exchange `outbound/` | Escribe (Release) | Lee (Fetch) |
| Exchange `inbound/` | Lee (Collect) | Escribe (Submit), sin listar |
| Exchange `feedback/` | Escribe | Lee tras Release Feedback |

---

## 6. Sistema de calificación automática (requisito 3)

### 6.1 Flujo del profesor (Formgrader)

1. Sidebar de JupyterLab → **Formgrader**.
2. **Add new assignment** → nombre y fecha límite.
3. Crear/editar notebook en `~/work/<course_id>/source/<tarea>/`.
4. Menú **Create Assignment** para tipar celdas:

   | Tipo de celda | Uso |
   |---|---|
   | Read-only | Enunciado |
   | Autograded answer | Código del alumno (`# YOUR CODE HERE`) |
   | Autograder tests | Asserts (pueden ocultarse al alumno) |
   | Manually graded answer / task | Preguntas abiertas |

5. **Generate** → versión limpia en `release/`.
6. **Release** → copia a `outbound/` del exchange.
7. Tras el deadline: **Collect** → entregas a `submitted/`.
8. **Autograde** → ejecuta tests (visibles + ocultos) y suma puntos.
9. **Generate Feedback** + **Release Feedback** → HTML en `feedback/`.

Hay una tarea de ejemplo en `nbgrader/example-assignment/tarea-01.ipynb` (factorial / es_primo).

### 6.2 Flujo del estudiante (Assignment List)

1. Sidebar → **Assignment List**.
2. **Released** → **Fetch**.
3. Resolver en `~/work/<course_id>/<tarea>/`.
4. **Validate** (tests visibles).
5. **Submit** → escribe en `inbound/`.
6. Tras calificación: **Fetch Feedback**.

### 6.3 Exportar notas

En la terminal del profesor:

```bash
cd ~/work/curso-2026
nbgrader export --to=notas.csv
```

---

## 7. Operaciones frecuentes

```bash
# Logs del Hub
docker compose logs -f jupyterhub

# Reiniciar conservando datos
docker compose restart jupyterhub

# Sembrar de nuevo scripts del profesor (p. ej. tras borrar volumen)
./scripts/seed-instructor.sh admin

# Backup BD del Hub
docker run --rm -v jupyterhub-data:/data -v "$(pwd)":/backup alpine \
  tar czf /backup/jupyterhub-data-backup.tar.gz -C /data .

# Backup workspace del profesor (incluye gradebook)
docker run --rm -v jupyterhub-user-admin:/data -v "$(pwd)":/backup alpine \
  tar czf /backup/admin-workspace.tar.gz -C /data .

# Apagar stack (los volúmenes persisten)
docker compose down
```

Añadir más profesores al mismo curso: en `.env`,

```
JUPYTERHUB_ADMIN=admin,profesor2
```

y recrear con `docker compose up -d`. Todos quedan en `formgrade-<course_id>`.

Paquetes Python extra para alumnos: editar `singleuser/requirements.txt` y

```bash
docker compose build singleuser-builder
```

Luego Stop/Start del servidor del usuario desde `/hub/admin`.

---

## 8. Checklist de cumplimiento

| Requisito | Estado | Dónde |
|---|---|---|
| Registro con usuario/contraseña | Cumple | NativeAuthenticator, `/hub/signup` |
| Sin acceso hasta aprobación manual | Cumple | `open_signup = False`, `/hub/authorize` |
| JupyterLab por defecto | Cumple | `DockerSpawner.default_url = "/lab"` |
| Formgrader + autograding | Cumple | Imagen singleuser + grupo `formgrade-*` |
| Exchange aislado | Cumple | Volumen compartido + `inbound` `1733` + workspaces privados |

Para el flujo operativo detallado día a día, ver también la [sección 6 del README](README.md#6-nbgrader-tareas-autocalificadas-entorno-universitario).
