# JupyterLab Hub multiusuario (Docker)

JupyterHub multiusuario en contenedores con:

- **NativeAuthenticator**: los usuarios se registran y el admin los autoriza.
- **DockerSpawner**: cada usuario obtiene su propio contenedor de notebook aislado.
- **nbgrader**: el profesor crea tareas autocalificables, las distribuye, recoge entregas y autocalifica.
- **nbgitpuller**: para repartir notebooks desde un repo de GitHub.
- **Idle culler**: apaga notebooks inactivos tras 1 hora.
- **Portable Windows ↔ Ubuntu Server**: idéntico `docker compose up` en ambos.

> Esta solución reemplaza la instalación nativa de TLJH/JupyterHub en Ubuntu.
> Todo corre en contenedores, así no contaminas el SO host y migras con un
> `git pull` o `docker save`.

## Estructura

```
.
├── docker-compose.yml
├── .env.example
├── jupyterhub/
│   ├── Dockerfile              # Hub + NativeAuthenticator + DockerSpawner
│   └── jupyterhub_config.py    # Configuración del Hub (incluye grupo formgrade-<curso>)
├── singleuser/
│   ├── Dockerfile              # Imagen del notebook por usuario (con nbgrader)
│   ├── nbgrader_config.py      # Config global de nbgrader (exchange + auth plugin)
│   └── requirements.txt        # Paquetes Python para tus alumnos
├── nbgrader/
│   ├── init-course.sh          # Inicializa el curso (lo corre el profesor)
│   └── example-assignment/     # Tarea de ejemplo (factorial, es_primo)
└── scripts/
    ├── generate-nbgitpuller-link.py
    ├── seed-instructor.ps1     # (Windows) copia init-course.sh al volumen del profesor
    ├── seed-instructor.sh      # (Linux) idem
    ├── reset-password.py       # Resetea password de un usuario
    ├── inspect-users.py        # Diagnóstico de usuarios en la BD
    └── inspect-groups.py       # Diagnóstico de grupos (formgrade-<curso>)
```

## 1. Desarrollo local en Windows

Requisitos: Docker Desktop con WSL2.

```powershell
# 1. Configura variables
Copy-Item .env.example .env
# Edita .env y pon tu usuario admin en JUPYTERHUB_ADMIN

# 2. Construye imágenes (Hub + singleuser)
docker compose build

# 3. Arranca
docker compose up -d

# 4. Ver logs
docker compose logs -f jupyterhub
```

Abre `http://localhost:8000`:

1. Ve a **Signup** (`/hub/signup`) y registra el usuario admin que pusiste en `.env`.
2. Inicia sesión como admin.
3. En `/hub/authorize` aprueba a otros usuarios cuando se registren.

## 2. Migración a Ubuntu Server

Tienes dos caminos. El **A** es el recomendado.

### A. Re-build en el servidor (recomendado, repo Git)

En el servidor Ubuntu (con Docker y Docker Compose v2 instalados):

```bash
# 1. Instalar Docker (una sola vez)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# 2. Clonar este proyecto
git clone <tu-repo> jupiterLab
cd jupiterLab

# 3. Configurar
cp .env.example .env
nano .env   # define JUPYTERHUB_ADMIN, etc.

# 4. Levantar
docker compose build
docker compose up -d

# 5. Firewall (opcional)
sudo ufw allow 8000/tcp
```

### B. Exportar imágenes desde Windows e importar en Ubuntu

Útil si la VM Ubuntu no tiene salida a internet para `docker pull` ni acceso al repo.

En **Windows**:

```powershell
docker compose build
docker save -o jupyterhub-custom.tar jupyterhub-custom:latest
docker save -o jupyterlab-singleuser.tar jupyterlab-singleuser:latest
```

Copia los `.tar` + `docker-compose.yml` + `.env` al servidor por `scp`/`rsync` y en **Ubuntu**:

```bash
docker load -i jupyterhub-custom.tar
docker load -i jupyterlab-singleuser.tar
docker compose up -d
```

## 3. HTTPS en producción (Ubuntu)

Pon un reverse proxy delante. Ejemplo rápido con Caddy en el host:

```caddy
# /etc/caddy/Caddyfile
hub.tu-dominio.com {
    reverse_proxy localhost:8000
}
```

Caddy gestiona Let's Encrypt automáticamente. Alternativa: Nginx + certbot, o
añadir [Traefik](https://traefik.io) como servicio adicional al `docker-compose.yml`.

## 4. Repartir tareas con nbgitpuller

Sube tus notebooks a un repo público de GitHub, luego genera el enlace:

```bash
python scripts/generate-nbgitpuller-link.py \
    --hub https://hub.tu-dominio.com \
    --repo https://github.com/tu-usuario/curso-notebooks \
    --branch main \
    --notebook tareas/tarea-01.ipynb
```

Comparte el link generado con tus estudiantes. Al hacer click:

1. Se loguean en el Hub.
2. `nbgitpuller` clona/actualiza el repo en su `~/work`.
3. Se abre el notebook indicado.

## 5. Operaciones útiles

```bash
# Ver usuarios y servidores activos
docker compose exec jupyterhub jupyterhub token <usuario>

# Reiniciar el Hub conservando datos
docker compose restart jupyterhub

# Backup de datos del Hub (DB de usuarios)
docker run --rm -v jupyterhub-data:/data -v ${PWD}:/backup alpine \
    tar czf /backup/jupyterhub-data-backup.tar.gz -C /data .

# Backup del workspace de un usuario
docker run --rm -v jupyterhub-user-juan:/data -v ${PWD}:/backup alpine \
    tar czf /backup/juan-workspace.tar.gz -C /data .

# Listar contenedores de usuario activos
docker ps --filter "name=jupyter-"

# Apagar todo
docker compose down
```

## 6. nbgrader: tareas autocalificadas (entorno universitario)

El profesor (admin) crea notebooks con celdas de ejercicio + tests ocultos, los distribuye, los recoge automáticamente y los autocalifica. Los alumnos sólo ven el enunciado y los tests visibles.

### 6.1 Cómo está armado en este Hub

```
                            ┌─────────────────────────┐
                            │  nbgrader-exchange       │  (volumen Docker compartido)
                            │  └─ curso-2026/          │
                            │     ├─ outbound/   ◄─ profesor "release"
                            │     ├─ inbound/    ─► alumnos "submit"
                            │     └─ feedback/   ◄─ profesor "release feedback"
                            └─────────────────────────┘
                                    ▲    ▲    ▲
                       montado en   │    │    │
                                    │    │    │
                       ┌────────────┴────┴────┴─────────┐
                       │                                │
                  jupyter-admin                  jupyter-usuario, jupyter-juan_marino
                  (ve Formgrader)                (ven Assignment List)
```

- **Quién es instructor**: pertenece al grupo `formgrade-<NBGRADER_COURSE_ID>` (definido en `.env`). Por defecto solo `admin`.
- **Auth plugin**: `nbgrader.auth.JupyterHubAuthPlugin` consulta JupyterHub para saber el rol → muestra/oculta UI según corresponda.
- **Exchange**: volumen `nbgrader-exchange` montado en `/srv/nbgrader/exchange` en TODOS los contenedores de usuario.

### 6.2 Inicialización del curso (PRIMERA VEZ)

El profesor entra a su JupyterLab y abre una terminal:

```bash
bash ~/work/init-course.sh
```

Esto crea `~/work/curso-2026/` con la estructura estándar (`source/`, `release/`, `submitted/`, `autograded/`, `feedback/`) e inicializa los subdirectorios del exchange con permisos correctos (sticky bit en `inbound/` para que un alumno no pueda leer la entrega de otro).

> Si recreas el contenedor del admin (rebuild), tras el primer login vuelve a sembrar los archivos con: `.\scripts\seed-instructor.ps1` (Windows) o `./scripts/seed-instructor.sh` (Linux).

### 6.3 Flujo del PROFESOR

1. **Crear tarea**:
   - Sidebar de JupyterLab → icono **Formgrader**.
   - Click **"Add new assignment"** → nombre + fecha límite.
   - En `~/work/curso-2026/source/<nombre>/` crea un notebook nuevo.
   - **Toolbar superior → "Create Assignment"** activa el menú de tipos de celda:

     | Tipo | Para qué |
     |---|---|
     | **Read-only** | Enunciado / instrucciones (no se puede modificar) |
     | **Manually graded answer** | Pregunta abierta — calificación humana |
     | **Autograded answer** | Donde el alumno escribe código (`# YOUR CODE HERE`) |
     | **Autograder tests** | Tests que el alumno NO ve, otorgan puntos |
     | **Manually graded task** | Tarea que combina ambos |

2. **Tarea de ejemplo lista**: en `~/work/example-assignment/tarea-01.ipynb` tienes una tarea completa (`factorial` + `es_primo`) con tests visibles y ocultos. Cópiala a tu source:

   ```bash
   mkdir -p ~/work/curso-2026/source/tarea-01
   cp ~/work/example-assignment/tarea-01.ipynb ~/work/curso-2026/source/tarea-01/
   ```

3. **Liberar a los alumnos**:
   - Formgrader → tu tarea → click **"Generate"** (produce versión limpia, sin soluciones).
   - Click **"Release"** → la copia a `outbound/` del exchange. Los alumnos ya pueden verla.

4. **Recolectar entregas** (después del deadline):
   - Formgrader → **"Collect"** → trae todas las entregas a `~/work/curso-2026/submitted/`.

5. **Autocalificar**:
   - Formgrader → **"Autograde"** → para cada estudiante:
     - Levanta un kernel limpio.
     - Ejecuta el notebook con TODOS los tests (visibles + ocultos).
     - Suma puntos automáticos.
   - Para preguntas abiertas (Manually graded), Formgrader te muestra una vista anonimizada para puntuarlas a mano.

6. **Devolver feedback**:
   - Formgrader → **"Generate Feedback"** → produce HTML con respuestas correctas y desglose de puntos.
   - Click **"Release Feedback"** → publica en `feedback/`.

### 6.4 Flujo del ESTUDIANTE

1. Login como `usuario` / `juan_marino` / etc.
2. Sidebar de JupyterLab → icono **"Assignment List"**.
3. Pestaña **"Released assignments"** → ve `tarea-01` → click **"Fetch"**.
4. La tarea aparece en `~/work/curso-2026/tarea-01/`.
5. Trabaja en el notebook. Botón **"Validate"** corre los tests visibles para chequear antes de entregar.
6. Click **"Submit"** → entrega.
7. Puede re-entregar las veces que quiera mientras no haya pasado el deadline.
8. Tras la calificación, pestaña "Submitted" muestra la nota → **"Fetch Feedback"** descarga el HTML con detalle.

### 6.5 Múltiples cursos / múltiples profesores

Para un segundo curso (`curso-2026-2`):

1. Edita `.env`:

   ```
   NBGRADER_COURSE_ID=curso-2026-2
   ```

2. Recrea: `docker compose up -d`. Se crea el grupo `formgrade-curso-2026-2`.
3. El admin (o el profesor que añadas) hace `bash ~/work/init-course.sh` dentro de su JupyterLab para inicializar la estructura.

Para añadir más profesores al mismo curso, en `.env`:

```
JUPYTERHUB_ADMIN=admin,profesor2,profesor3
```

Todos quedan en `formgrade-<curso>` y todos ven Formgrader.

### 6.6 Backup de calificaciones

Las notas viven en `~/work/<curso>/gradebook.db` (SQLite) **dentro del volumen del profesor**. Para hacer backup:

```powershell
# Windows
docker run --rm -v jupyterhub-user-admin:/data -v ${PWD}:/backup alpine `
    tar czf /backup/admin-workspace.tar.gz -C /data .
```

```bash
# Linux
docker run --rm -v jupyterhub-user-admin:/data -v $(pwd):/backup alpine \
    tar czf /backup/admin-workspace.tar.gz -C /data .
```

### 6.7 Exportar calificaciones (CSV)

En la terminal de JupyterLab del profesor:

```bash
cd ~/work/curso-2026
nbgrader export --to=notas.csv
```

Genera un CSV con `student_id`, `assignment`, `score`, `max_score` listo para importar al SIS de la universidad.

## 7. Personalizar paquetes Python para los alumnos

Edita `singleuser/requirements.txt` y reconstruye:

```bash
docker compose build singleuser-builder
```

La próxima vez que un usuario abra su servidor, recibirá la imagen actualizada (cierra y abre sesión, o desde `/hub/admin` "Stop Server" → "Start Server").

## Notas de portabilidad Windows → Ubuntu

- **Volúmenes nombrados, no bind mounts**: `jupyterhub-data` y
  `jupyterhub-user-<usuario>` son volúmenes Docker manejados por el daemon
  → no dependen de rutas tipo `D:\...` ni `/home/...`.
- **Socket Docker**: se monta igual en ambos SO (Docker Desktop expone el
  socket Linux dentro del contenedor del Hub).
- **Sin scripts `.sh` con CRLF**: solo Python y YAML, así que no hay problemas
  de fin de línea al pasar de Windows a Linux.
- **Imágenes idénticas**: la base es Linux en ambos lados, así que las
  imágenes construidas en Windows se ejecutan tal cual en Ubuntu.
