"""
Resetea (o crea) el password de un usuario de NativeAuthenticator.

Uso desde el host (PowerShell):
    docker cp scripts/reset-password.py jupyterhub:/tmp/reset.py
    docker exec -it jupyterhub python /tmp/reset.py admin nuevoPass123

Si el usuario no existe lo crea ya autorizado y como admin.
"""
import sys
import bcrypt
from sqlalchemy import create_engine, text


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    username, new_password = sys.argv[1], sys.argv[2]

    if len(new_password) < 8:
        print("ERROR: la contraseña debe tener al menos 8 caracteres")
        sys.exit(1)

    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    engine = create_engine("sqlite:////data/jupyterhub.sqlite")
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT username FROM users_info WHERE username = :u"),
            {"u": username},
        ).first()

        if existing:
            conn.execute(
                text(
                    "UPDATE users_info SET password = :p, is_authorized = 1 "
                    "WHERE username = :u"
                ),
                {"p": pw_hash, "u": username},
            )
            print(f"OK: password de '{username}' actualizado y usuario autorizado.")
        else:
            conn.execute(
                text(
                    "INSERT INTO users_info "
                    "(username, password, is_authorized, has_2fa, login_email_sent) "
                    "VALUES (:u, :p, 1, 0, 0)"
                ),
                {"u": username, "p": pw_hash},
            )
            conn.execute(
                text("INSERT OR IGNORE INTO users (name, admin) VALUES (:u, 1)"),
                {"u": username},
            )
            print(f"OK: usuario '{username}' creado y autorizado como admin.")


if __name__ == "__main__":
    main()
