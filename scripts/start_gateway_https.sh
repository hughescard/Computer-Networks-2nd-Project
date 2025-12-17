#!/usr/bin/env bash
# Arranca el gateway del portal cautivo en modo HTTPS.
# 1) Configura IP LAN 192.168.50.1/24 (ajustable).
# 2) Aplica firewall con puerto HTTPS.
# 3) Arranca el portal con TLS usando certificado/llave locales.
#
# Variables ajustables (exporta antes de ejecutar o edita aquí):
#   LAN_IF            -> interfaz LAN (por defecto enp0s8)
#   WAN_IF            -> interfaz WAN (por defecto enp0s3)
#   PORTAL_HTTP_PORT  -> puerto HTTPS del portal (por defecto 8443)
#   PORTAL_SESSION_TTL -> TTL de sesión en segundos (por defecto 3600)
#   PORTAL_TLS_CERT / PORTAL_TLS_KEY -> rutas a certificado/llave PEM (requeridos)
#   PORTAL_HTTPS_PORT -> puerto a abrir en firewall (por defecto igual a PORTAL_HTTP_PORT)

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

LAN_IF="${LAN_IF:-enp0s8}"
WAN_IF="${WAN_IF:-enp0s3}"
PORTAL_HTTP_PORT="${PORTAL_HTTP_PORT:-8443}"
PORTAL_SESSION_TTL="${PORTAL_SESSION_TTL:-3600}"
PORTAL_SESSION_CLEANUP_INTERVAL="${PORTAL_SESSION_CLEANUP_INTERVAL:-30}"
PORTAL_HTTPS_PORT="${PORTAL_HTTPS_PORT:-$PORTAL_HTTP_PORT}"

if [[ -z "${PORTAL_TLS_CERT:-}" || -z "${PORTAL_TLS_KEY:-}" ]]; then
  echo "ERROR: debes definir PORTAL_TLS_CERT y PORTAL_TLS_KEY antes de lanzar HTTPS." >&2
  exit 1
fi

echo "[1/3] Configurando IP en LAN ($LAN_IF = 192.168.50.1/24)..."
sudo ip addr flush dev "$LAN_IF"
sudo ip addr add 192.168.50.1/24 dev "$LAN_IF"
sudo ip link set "$LAN_IF" up

echo "[2/3] Aplicando firewall base para HTTPS..."
sudo WAN_IF="$WAN_IF" LAN_IF="$LAN_IF" \
  PORTAL_HTTP_PORT="$PORTAL_HTTP_PORT" \
  PORTAL_HTTPS_PORT="$PORTAL_HTTPS_PORT" \
  bash "$SCRIPT_DIR/firewall_init.sh"

echo "[3/3] Arrancando portal cautivo en modo TLS..."
cd "$REPO_ROOT"
exec sudo -E \
  PORTAL_LAN_IF="$LAN_IF" \
  PORTAL_HTTP_PORT="$PORTAL_HTTP_PORT" \
  PORTAL_SESSION_TTL="$PORTAL_SESSION_TTL" \
  PORTAL_SESSION_CLEANUP_INTERVAL="$PORTAL_SESSION_CLEANUP_INTERVAL" \
  PORTAL_ENABLE_TLS=1 \
  PORTAL_TLS_CERT="$PORTAL_TLS_CERT" \
  PORTAL_TLS_KEY="$PORTAL_TLS_KEY" \
  PORTAL_HTTPS_PORT="$PORTAL_HTTPS_PORT" \
  python3 "$REPO_ROOT/src/http_server.py"
