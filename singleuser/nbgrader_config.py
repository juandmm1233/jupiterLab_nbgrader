"""
Configuración GLOBAL de nbgrader (se aplica dentro de cada contenedor de usuario).

- Define dónde está el "exchange" compartido entre profesor y alumnos.
- Activa el plugin de autenticación de JupyterHub para que nbgrader sepa
  quién es instructor consultando los grupos del Hub.
"""
import os

c = get_config()  # noqa: F821

# ---------------------------------------------------------------------------
# Exchange compartido (volumen Docker `nbgrader-exchange` montado en todos)
# ---------------------------------------------------------------------------
c.Exchange.root = "/srv/nbgrader/exchange"
c.Exchange.timezone = os.environ.get("NBGRADER_TIMEZONE", "America/Bogota")

# ID del curso por defecto. Se sobreescribe por curso si configuras varios.
c.CourseDirectory.course_id = os.environ.get("NBGRADER_COURSE_ID", "curso-2026")

# ---------------------------------------------------------------------------
# Autenticación basada en JupyterHub:
#   - El usuario es INSTRUCTOR si pertenece al grupo `formgrade-{course_id}`.
#   - Cualquier otro usuario autenticado es ESTUDIANTE.
# El plugin lee JUPYTERHUB_API_TOKEN/URL inyectados automáticamente
# por JupyterHub en el server de cada usuario.
# ---------------------------------------------------------------------------
c.Authenticator.plugin_class = "nbgrader.auth.JupyterHubAuthPlugin"

# ---------------------------------------------------------------------------
# Comportamiento general
# ---------------------------------------------------------------------------
c.ClearSolutions.code_stub = {
    "python": "# YOUR CODE HERE\nraise NotImplementedError()",
    "r": "# YOUR CODE HERE\nstop('Not implemented')",
    "julia": "# YOUR CODE HERE\nthrow(ErrorException(\"Not implemented\"))",
}

c.ExecutePreprocessor.timeout = 60
