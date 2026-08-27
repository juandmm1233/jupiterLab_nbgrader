"""Test que llama al endpoint del formgrader desde dentro del contenedor."""
import os
import urllib.request

url = "http://0.0.0.0:8888/user/admin/formgrader/manage_assignments"
req = urllib.request.Request(url)
req.add_header("Authorization", f"token {os.environ['JUPYTERHUB_API_TOKEN']}")

try:
    r = urllib.request.urlopen(req, timeout=10)
    print("STATUS:", r.status)
    body = r.read().decode()
    print("SIZE:", len(body), "bytes")
    if "Formgrader" in body or "manage_assignments" in body or "nbgrader" in body.lower():
        print("OK: respuesta contiene UI de Formgrader")
    else:
        print("SNIPPET:", body[:500])
except urllib.error.HTTPError as e:
    print(f"HTTP ERROR {e.code}: {e.reason}")
    print(e.read().decode()[:500])
except Exception as e:
    print("ERROR:", type(e).__name__, e)
