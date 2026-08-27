"""Lista grupos del Hub y sus miembros (verifica formgrade-<curso>)."""
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:////data/jupyterhub.sqlite")

with engine.connect() as conn:
    print("=== groups ===")
    for row in conn.execute(text("SELECT id, name FROM groups")):
        gid, gname = row.id, row.name
        members = conn.execute(
            text(
                "SELECT u.name FROM users u "
                "JOIN user_group_map m ON m.user_id = u.id "
                "WHERE m.group_id = :gid"
            ),
            {"gid": gid},
        ).all()
        print(f"  [{gid}] {gname} -> {[r.name for r in members]}")
