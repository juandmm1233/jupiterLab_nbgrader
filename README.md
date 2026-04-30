# JupyterLab Hub multiusuario (Docker)

JupyterHub multiusuario en contenedores con:

- **NativeAuthenticator**: los usuarios se registran y el admin los autoriza.
- **DockerSpawner**: cada usuario obtiene su propio contenedor de notebook aislado.
- **nbgitpuller**: para repartir tareas desde un repo de GitHub.
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
│   └── jupyterhub_config.py    # Configuración del Hub
├── singleuser/
│   ├── Dockerfile              # Imagen del notebook por usuario
│   └── requirements.txt        # Paquetes Python para tus alumnos
└── scripts/
    └── generate-nbgitpuller-link.py
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

## 6. Personalizar paquetes Python para los alumnos

Edita `singleuser/requirements.txt` y reconstruye:

```bash
docker compose build singleuser-builder
```

La próxima vez que un usuario abra su servidor, recibirá la imagen actualizada.

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
