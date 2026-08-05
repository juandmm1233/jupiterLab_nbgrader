#!/bin/bash
# Inicializa la carpeta de curso de nbgrader dentro del workspace del profesor.
# Se ejecuta UNA VEZ desde la terminal del JupyterLab del admin.
#
# Uso (desde la terminal de JupyterLab del admin):
#     bash /home/jovyan/work/init-course.sh
#
# Crea ~/work/<course_id>/ con la estructura estándar de nbgrader y
# inicializa el directorio del exchange con sticky bit en inbound/.

set -euo pipefail

COURSE_ID="${NBGRADER_COURSE_ID:-curso-2026}"
COURSE_DIR="${HOME}/work/${COURSE_ID}"
EXCHANGE_ROOT="/srv/nbgrader/exchange"

if [ -d "${COURSE_DIR}" ]; then
    echo "[i] El curso ${COURSE_ID} ya existe en ${COURSE_DIR}. No se sobreescribe."
else
    echo "[i] Creando estructura del curso en ${COURSE_DIR}..."
    nbgrader quickstart "${COURSE_ID}" --force
    mv "${HOME}/${COURSE_ID}" "${COURSE_DIR}"
    echo "[OK] Curso creado."
fi

echo "[i] Inicializando exchange en ${EXCHANGE_ROOT}/${COURSE_ID}/..."
mkdir -p "${EXCHANGE_ROOT}/${COURSE_ID}/outbound"
mkdir -p "${EXCHANGE_ROOT}/${COURSE_ID}/inbound"
mkdir -p "${EXCHANGE_ROOT}/${COURSE_ID}/feedback"

chmod 0755 "${EXCHANGE_ROOT}/${COURSE_ID}"
chmod 0755 "${EXCHANGE_ROOT}/${COURSE_ID}/outbound"
chmod 0755 "${EXCHANGE_ROOT}/${COURSE_ID}/feedback"
# sticky bit -> los alumnos pueden escribir su entrega pero NO leer las de otros
chmod 1733 "${EXCHANGE_ROOT}/${COURSE_ID}/inbound"

echo "[OK] Exchange listo:"
ls -la "${EXCHANGE_ROOT}/${COURSE_ID}"

cat <<'EOF'

================================================================
 Curso inicializado correctamente.
 Próximos pasos (desde el JupyterLab del profesor):

  1. Abre Formgrader (icono en la barra lateral izquierda).
  2. Click "Add new assignment" para crear una tarea.
  3. Edita los notebooks en source/<tarea>/
     (usa el menú "Create Assignment" para marcar celdas).
  4. Click "Generate" + "Release" para liberarla a los alumnos.

================================================================
EOF
