"""Diagnóstico: lista los usuarios en la BD del Hub y su estado de autorización."""
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:////data/jupyterhub.sqlite")

with engine.connect() as conn:
    print("=== users (JupyterHub core) ===")
    for row in conn.execute(text("SELECT id, name, admin FROM users")):
        print(" ", dict(row._mapping))
    print()
    print("=== users_info (NativeAuthenticator) ===")
    try:
        for row in conn.execute(
            text("SELECT username, is_authorized, has_2fa, login_email_sent FROM users_info")
        ):
            print(" ", dict(row._mapping))
    except Exception as exc:
        print("  (sin tabla users_info o error:", exc, ")")
