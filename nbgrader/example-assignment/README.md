# Tarea de ejemplo

Este `tarea-01.ipynb` es un notebook **fuente** (con soluciones y tests ocultos) listo para usar como ejemplo.

## Cómo usarlo en tu Hub

1. Logueado como admin, abre la terminal de JupyterLab.
2. Inicializa el curso si no lo has hecho:

   ```bash
   bash /home/jovyan/work/init-course.sh
   ```

3. Copia este notebook a la carpeta source del curso:

   ```bash
   mkdir -p ~/work/curso-2026/source/tarea-01
   cp /tmp/example-assignment/tarea-01.ipynb ~/work/curso-2026/source/tarea-01/
   ```

   *(Más fácil: simplemente arrastra el archivo desde tu PC al panel de archivos de JupyterLab dentro de `curso-2026/source/tarea-01/`)*.

4. Abre el Formgrader (sidebar izquierdo) → la tarea aparece como **"draft"**.
5. Click en **"Generate"** → produce versión limpia para alumnos.
6. Click en **"Release"** → la deja disponible para que los estudiantes la "fetcheen".

## Qué celdas contiene esta tarea de ejemplo

| Celda | Tipo nbgrader | Puntos |
|---|---|---|
| Introducción | Read-only | — |
| Ejercicio 1 enunciado | Read-only | — |
| Ejercicio 1 solución | Autograded answer | — |
| Ejercicio 1 tests visibles | Autograder tests (visible) | 1 |
| Ejercicio 1 tests ocultos | Autograder tests (oculto) | 2 |
| Ejercicio 2 enunciado | Read-only | — |
| Ejercicio 2 solución | Autograded answer | — |
| Ejercicio 2 tests | Autograder tests (mixto) | 2 |

**Total: 5 puntos** repartidos en autograder.
