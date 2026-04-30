#!/bin/bash
# Copia el script de inicialización del curso y la tarea de ejemplo
# al workspace del usuario admin (volumen jupyterhub-user-admin).
#
# Uso (Linux/Ubuntu, desde la raíz del proyecto):
#     ./scripts/seed-instructor.sh           # admin por defecto
#     ./scripts/seed-instructor.sh otroProf

set -euo pipefail

USER_NAME="${1:-admin}"
CONTAINER_NAME="seed-helper-${USER_NAME}"
VOLUME_NAME="jupyterhub-user-${USER_NAME}"

echo "[i] Sembrando archivos de nbgrader en ${VOLUME_NAME} ..."

docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true

docker run -d --name "${CONTAINER_NAME}" \
    -v "${VOLUME_NAME}:/home/jovyan/work" \
    --user root \
    jupyterlab-singleuser:latest sleep 30 >/dev/null

docker cp ./nbgrader/init-course.sh "${CONTAINER_NAME}:/home/jovyan/work/init-course.sh"
docker cp ./nbgrader/example-assignment "${CONTAINER_NAME}:/home/jovyan/work/example-assignment"
docker exec "${CONTAINER_NAME}" chown -R 1000:100 /home/jovyan/work
docker exec "${CONTAINER_NAME}" chmod +x /home/jovyan/work/init-course.sh

docker rm -f "${CONTAINER_NAME}" >/dev/null

echo "[OK] Listo. En la terminal de JupyterLab del profesor ejecuta:"
echo "       bash ~/work/init-course.sh"
