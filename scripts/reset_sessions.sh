#!/usr/bin/env bash
# scripts/reset_sessions.sh
# Elimina todas las sesiones persistidas en config/sessions.json.

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && cd .. && pwd)"
cd "$REPO_ROOT"

python3 <<'PY'
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / "src"))

from sessions import eliminar_sesion, obtener_todas_las_sesiones

sessions = obtener_todas_las_sesiones()

if not sessions:
    print("No hay sesiones guardadas.")
    raise SystemExit(0)

for (ip, mac) in list(sessions.keys()):
    eliminar_sesion(ip, mac)

print(f"Sesiones eliminadas: {len(sessions)}")
PY
