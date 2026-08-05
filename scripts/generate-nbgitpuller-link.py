"""
Genera enlaces nbgitpuller para repartir tareas/notebooks a los estudiantes.

Uso:
    python scripts/generate-nbgitpuller-link.py \
        --hub http://localhost:8000 \
        --repo https://github.com/usuario/curso-notebooks \
        --branch main \
        --notebook tareas/tarea-01.ipynb
"""
import argparse
from urllib.parse import urlencode, quote


def build_link(hub: str, repo: str, branch: str, notebook: str | None) -> str:
    params = {
        "repo": repo,
        "urlpath": f"lab/tree/{quote(notebook)}" if notebook else "lab",
        "branch": branch,
    }
    return f"{hub.rstrip('/')}/hub/user-redirect/git-pull?{urlencode(params)}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hub", required=True, help="URL pública del JupyterHub")
    parser.add_argument("--repo", required=True, help="URL del repositorio Git")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--notebook", default=None,
                        help="Ruta del notebook dentro del repo (opcional)")
    args = parser.parse_args()

    print(build_link(args.hub, args.repo, args.branch, args.notebook))


if __name__ == "__main__":
    main()
