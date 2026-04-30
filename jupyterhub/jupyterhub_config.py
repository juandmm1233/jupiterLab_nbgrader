"""
Configuración de JupyterHub para entorno multiusuario en Docker.
Funciona idénticamente en Windows (Docker Desktop) y Ubuntu Server.
"""
import os
import sys

c = get_config()  # noqa: F821

# ---------------------------------------------------------------------------
# Hub general
# ---------------------------------------------------------------------------
c.JupyterHub.bind_url = "http://:8000"
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_connect_ip = os.environ.get("HUB_CONNECT_IP", "jupyterhub")
c.JupyterHub.cleanup_servers = False
c.ConfigurableHTTPProxy.should_start = True
c.JupyterHub.log_level = "INFO"

# Datos persistentes (montados como volumen)
c.JupyterHub.cookie_secret_file = "/data/jupyterhub_cookie_secret"
c.JupyterHub.db_url = "sqlite:////data/jupyterhub.sqlite"

# ---------------------------------------------------------------------------
# Autenticación: NativeAuthenticator
#   - Los usuarios se registran en /hub/signup
#   - El admin los aprueba en /hub/authorize
# ---------------------------------------------------------------------------
c.JupyterHub.authenticator_class = "nativeauthenticator.NativeAuthenticator"

admin_users = os.environ.get("JUPYTERHUB_ADMIN", "admin").split(",")
c.Authenticator.admin_users = {u.strip() for u in admin_users if u.strip()}

# IMPORTANTE: en JupyterHub 5.x, `allow_all` controla la capa de autorización
# del CORE (previa a NativeAuthenticator). Si lo dejamos en False, ni siquiera
# los admins pueden loguearse. La gestión de "quién está aprobado" la delegamos
# a NativeAuthenticator a través del flag `is_authorized` en su propia tabla.
c.Authenticator.allow_all = True

c.NativeAuthenticator.open_signup = False
c.NativeAuthenticator.check_common_password = True
c.NativeAuthenticator.minimum_password_length = 8
c.NativeAuthenticator.allowed_failed_logins = 5
c.NativeAuthenticator.seconds_before_next_try = 600

# ---------------------------------------------------------------------------
# Spawner: DockerSpawner -> cada usuario obtiene su propio contenedor
# ---------------------------------------------------------------------------
c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"

c.DockerSpawner.image = os.environ.get(
    "DOCKER_NOTEBOOK_IMAGE", "jupyterlab-singleuser:latest"
)
c.DockerSpawner.network_name = os.environ.get(
    "DOCKER_NETWORK_NAME", "jupyterhub-network"
)
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.remove = True

c.DockerSpawner.notebook_dir = "/home/jovyan/work"
c.DockerSpawner.volumes = {
    "jupyterhub-user-{username}": "/home/jovyan/work",
    # Volumen COMPARTIDO entre todos los usuarios para nbgrader.
    # El profesor escribe en outbound/feedback; los alumnos en inbound.
    # Los permisos sticky-bit los gestiona nbgrader al inicializar el curso.
    "nbgrader-exchange": "/srv/nbgrader/exchange",
}

c.DockerSpawner.environment = {
    "GRANT_SUDO": "no",
    "CHOWN_HOME": "yes",
    # ID del curso (debe coincidir con el grupo formgrade-{course_id} de abajo)
    "NBGRADER_COURSE_ID": os.environ.get("NBGRADER_COURSE_ID", "curso-2026"),
    "NBGRADER_TIMEZONE": os.environ.get("NBGRADER_TIMEZONE", "America/Bogota"),
}

c.DockerSpawner.cmd = ["start-singleuser.sh"]
c.DockerSpawner.default_url = "/lab"
c.DockerSpawner.start_timeout = 300
c.DockerSpawner.http_timeout = 120

c.Spawner.mem_limit = os.environ.get("USER_MEM_LIMIT", "2G")
c.Spawner.cpu_limit = float(os.environ.get("USER_CPU_LIMIT", "1.0"))

# ---------------------------------------------------------------------------
# Servicios: idle-culler para apagar notebooks inactivos
# ---------------------------------------------------------------------------
c.JupyterHub.services = [
    {
        "name": "idle-culler",
        "command": [
            sys.executable,
            "-m",
            "jupyterhub_idle_culler",
            "--timeout=3600",
        ],
    }
]

c.JupyterHub.load_roles = [
    {
        "name": "idle-culler-role",
        "scopes": [
            "list:users",
            "read:users:activity",
            "read:servers",
            "delete:servers",
        ],
        "services": ["idle-culler"],
    },
    # Rol que permite a nbgrader (corriendo dentro del server del usuario)
    # consultar grupos del Hub y saber si el usuario es instructor.
    # Se asigna al rol "user" para que TODOS los servers de usuario lo tengan.
    {
        "name": "user",
        "scopes": [
            "self",
            "read:groups",
            "list:groups",
        ],
    },
]

# ---------------------------------------------------------------------------
# Grupos para nbgrader
#   Los miembros de `formgrade-<course_id>` son INSTRUCTORES del curso.
#   Cualquier otro usuario autenticado se considera estudiante.
#   Nombre del grupo determinado por la convención de nbgrader.
# ---------------------------------------------------------------------------
NBGRADER_COURSE_ID = os.environ.get("NBGRADER_COURSE_ID", "curso-2026")
c.JupyterHub.load_groups = {
    f"formgrade-{NBGRADER_COURSE_ID}": {
        "users": [u.strip() for u in admin_users if u.strip()],
    },
}
