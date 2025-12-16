#!/usr/bin/env bash
# scripts/start_tls_only.sh
# Arranca solo el servidor HTTPS (no toca iptables) para complementar la versión HTTP.

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && cd .. && pwd)"
cd "$REPO_ROOT"

PORTAL_LAN_IF="${PORTAL_LAN_IF:-enp0s8}"
PORTAL_HTTP_PORT="${PORTAL_HTTP_PORT:-8443}"
PORTAL_SESSION_TTL="${PORTAL_SESSION_TTL:-3600}"

if [[ -z "${PORTAL_TLS_CERT:-}" || -z "${PORTAL_TLS_KEY:-}" ]]; then
  echo "ERROR: define PORTAL_TLS_CERT y PORTAL_TLS_KEY antes de ejecutar este script." >&2
  exit 1
fi

echo "[1/2] Usando LAN $PORTAL_LAN_IF, puerto TLS $PORTAL_HTTP_PORT..."
echo "[2/2] Arrancando solo el servidor HTTPS..."

exec sudo -E \
  PORTAL_LAN_IF="$PORTAL_LAN_IF" \
  PORTAL_HTTP_PORT="$PORTAL_HTTP_PORT" \
  PORTAL_ENABLE_TLS=1 \
  PORTAL_TLS_CERT="$PORTAL_TLS_CERT" \
  PORTAL_TLS_KEY="$PORTAL_TLS_KEY" \
  PORTAL_SESSION_TTL="$PORTAL_SESSION_TTL" \
  python3 "$REPO_ROOT/src/http_server.py"
