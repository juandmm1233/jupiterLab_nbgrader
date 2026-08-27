"""Reemplaza course_id en nbgrader_config.py del curso del admin."""
import re
import os
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "/home/jovyan/work/curso-2026/nbgrader_config.py"
target = os.environ.get("NBGRADER_COURSE_ID", "curso-2026")

with open(path) as f:
    content = f.read()

content = re.sub(
    r'course_id\s*=\s*["\']curso-2026-tmp["\']',
    f'course_id = "{target}"',
    content,
)

with open(path, "w") as f:
    f.write(content)

print(f"OK: course_id = '{target}' en {path}")
