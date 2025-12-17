#!/usr/bin/env bash
# Arranca el gateway del portal cautivo en un solo paso:
# 1) Configura IP en la interfaz LAN.
# 2) Aplica el firewall base (drop por defecto, redirección al portal y NAT).
# 3) Levanta el servidor del portal (HTTP o HTTPS) con el entorno actual.
#
# Variables ajustables (exporta antes de ejecutar o edita aquí):
#   LAN_IF           -> interfaz LAN (por defecto enp0s8)
#   WAN_IF           -> interfaz WAN (por defecto enp0s3)
#   PORTAL_HTTP_PORT -> puerto del portal (por defecto 8080; usa 8443 si TLS)
#   PORTAL_SESSION_TTL -> TTL de sesión en segundos (por defecto 3600)
#   PORTAL_ENABLE_TLS -> 1/true para activar HTTPS
#   PORTAL_TLS_CERT / PORTAL_TLS_KEY -> rutas a certificado/llave PEM si TLS
#   PORTAL_HTTPS_PORT -> puerto HTTPS a abrir en el firewall (igual a HTTP si no se define)

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

LAN_IF="${LAN_IF:-enp0s8}"
WAN_IF="${WAN_IF:-enp0s3}"
PORTAL_HTTP_PORT="${PORTAL_HTTP_PORT:-8080}"
PORTAL_SESSION_TTL="${PORTAL_SESSION_TTL:-3600}"
PORTAL_SESSION_CLEANUP_INTERVAL="${PORTAL_SESSION_CLEANUP_INTERVAL:-30}"

# Si TLS está activo y no se definió PORTAL_HTTPS_PORT, usa el mismo puerto.
if [[ "${PORTAL_ENABLE_TLS:-0}" =~ ^(1|true|yes|on)$ ]]; then
  PORTAL_HTTPS_PORT="${PORTAL_HTTPS_PORT:-$PORTAL_HTTP_PORT}"
fi

echo "[1/3] Configurando IP en LAN ($LAN_IF = 192.168.50.1/24)..."
sudo ip addr flush dev "$LAN_IF"
sudo ip addr add 192.168.50.1/24 dev "$LAN_IF"
sudo ip link set "$LAN_IF" up

echo "[2/3] Aplicando firewall base..."
sudo WAN_IF="$WAN_IF" LAN_IF="$LAN_IF" \
  PORTAL_HTTP_PORT="$PORTAL_HTTP_PORT" \
  PORTAL_HTTPS_PORT="${PORTAL_HTTPS_PORT:-}" \
  bash "$SCRIPT_DIR/firewall_init.sh"

echo "[3/3] Arrancando portal cautivo..."
cd "$REPO_ROOT"
exec sudo -E \
  PORTAL_LAN_IF="$LAN_IF" \
  PORTAL_HTTP_PORT="$PORTAL_HTTP_PORT" \
  PORTAL_SESSION_TTL="$PORTAL_SESSION_TTL" \
  PORTAL_SESSION_CLEANUP_INTERVAL="$PORTAL_SESSION_CLEANUP_INTERVAL" \
  PORTAL_ENABLE_TLS="${PORTAL_ENABLE_TLS:-0}" \
  PORTAL_TLS_CERT="${PORTAL_TLS_CERT:-}" \
  PORTAL_TLS_KEY="${PORTAL_TLS_KEY:-}" \
  PORTAL_HTTPS_PORT="${PORTAL_HTTPS_PORT:-}" \
  python3 "$REPO_ROOT/src/http_server.py"
