#!/bin/bash
# Inicializa la carpeta de curso de nbgrader dentro del workspace del profesor.
# Es IDEMPOTENTE: puede ejecutarse las veces que quieras, repara lo que falte.
#
# Uso (desde la terminal de JupyterLab del admin):
#     bash ~/work/init-course.sh

set -euo pipefail

COURSE_ID="${NBGRADER_COURSE_ID:-curso-2026}"
COURSE_DIR="${HOME}/work/${COURSE_ID}"
EXCHANGE_ROOT="/srv/nbgrader/exchange"

mkdir -p "${COURSE_DIR}"

# Si falta el nbgrader_config.py del curso, lo generamos.
# Usamos quickstart en una carpeta temporal y solo copiamos el config.
if [ ! -f "${COURSE_DIR}/nbgrader_config.py" ]; then
    echo "[i] Generando nbgrader_config.py para ${COURSE_ID}..."
    TMP_DIR="$(mktemp -d)"
    pushd "${TMP_DIR}" > /dev/null
    nbgrader quickstart "${COURSE_ID}-bootstrap" --force > /dev/null
    cp "${COURSE_ID}-bootstrap/nbgrader_config.py" "${COURSE_DIR}/nbgrader_config.py"
    popd > /dev/null
    rm -rf "${TMP_DIR}"

    # Reemplaza el course_id placeholder por el real.
    python - "${COURSE_DIR}/nbgrader_config.py" "${COURSE_ID}" <<'PY'
import re, sys
path, course_id = sys.argv[1], sys.argv[2]
with open(path) as f:
    content = f.read()
content = re.sub(
    r'course_id\s*=\s*["\'][^"\']*-bootstrap["\']',
    f'course_id = "{course_id}"',
    content,
)
with open(path, "w") as f:
    f.write(content)
PY
    echo "[OK] nbgrader_config.py creado."
else
    echo "[i] ${COURSE_DIR}/nbgrader_config.py ya existe (no se sobreescribe)."
fi

# Crea las subcarpetas estándar si faltan.
for d in source release submitted autograded feedback; do
    mkdir -p "${COURSE_DIR}/${d}"
done
echo "[OK] Estructura del curso completa."

# Inicializa el exchange compartido (volumen Docker).
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

  1. Recarga la pestaña del navegador (F5) si tenías Formgrader abierto.
  2. Click en el icono de Formgrader (barra lateral izquierda).
  3. Click "Add new assignment" para crear una tarea, O usa
     la tarea de ejemplo en ~/work/example-assignment/

================================================================
EOF
