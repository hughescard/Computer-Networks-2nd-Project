#!/usr/bin/env bash
# Script de comprobación básica del portal cautivo (Issue #12).
# Ejecutar desde un cliente de la LAN para validar:
#   1) Redirección al portal antes del login.
#   2) Login exitoso con credenciales válidas.
#   3) Acceso posterior sin que aparezca de nuevo el portal.
#
# Variables de entorno configurables:
#   PORTAL_HOST   (IP del gateway, por defecto 192.168.50.1)
#   PORTAL_PORT   (puerto donde escucha el portal, por defecto 8080)
#   TARGET_URL    (sitio HTTP a abrir para comprobar redirección, por defecto http://example.com)
#   PORTAL_USER   (usuario válido para login, por defecto admin)
#   PORTAL_PASS   (contraseña válida, por defecto admin)

set -euo pipefail

PORTAL_HOST="${PORTAL_HOST:-192.168.50.1}"
PORTAL_PORT="${PORTAL_PORT:-8080}"
TARGET_URL="${TARGET_URL:-http://example.com}"
PORTAL_USER="${PORTAL_USER:-admin}"
PORTAL_PASS="${PORTAL_PASS:-admin}"

TMP_HEADERS="$(mktemp)"
TMP_BODY="$(mktemp)"
TMP_LOGIN="$(mktemp)"

cleanup() {
  rm -f "$TMP_HEADERS" "$TMP_BODY" "$TMP_LOGIN"
}
trap cleanup EXIT

timestamp() { date +"%Y-%m-%d %H:%M:%S"; }
log() { echo "[$(timestamp)] $*"; }

check_portal_in_body() {
  local body_file="$1"
  if grep -qiE "Portal Cautivo|Iniciar sesi[oó]n|Acceso denegado|Autenticaci[oó]n" "$body_file"; then
    return 0
  fi
  return 1
}

log "=== Prueba básica del portal cautivo ==="
log "Gateway: $PORTAL_HOST:$PORTAL_PORT | TARGET_URL: $TARGET_URL"

log "1) Acceso SIN login a $TARGET_URL (debería aparecer el portal)..."
if curl -s -D "$TMP_HEADERS" -o "$TMP_BODY" --max-time 8 "$TARGET_URL"; then
  if check_portal_in_body "$TMP_BODY"; then
    log "OK: se detectó el portal en la respuesta inicial."
  else
    log "ERROR: no se detectó el portal antes del login."
    log "Mira el cuerpo almacenado en: $TMP_BODY"
    exit 1
  fi
else
  log "ERROR: no se pudo obtener $TARGET_URL (verifica conectividad/DNS)."
  exit 1
fi

log "2) Login con usuario válido ($PORTAL_USER)..."
if curl -s -o "$TMP_LOGIN" --max-time 8 \
    -d "username=${PORTAL_USER}&password=${PORTAL_PASS}" \
    "http://${PORTAL_HOST}:${PORTAL_PORT}/login"; then
  if grep -qi "Autenticaci[oó]n exitosa" "$TMP_LOGIN"; then
    log "OK: login exitoso."
  else
    log "ERROR: el login no devolvió la página de éxito."
    log "Revisa el cuerpo en: $TMP_LOGIN"
    exit 1
  fi
else
  log "ERROR: fallo al conectar con el portal para login."
  exit 1
fi

log "3) Acceso DESPUÉS del login a $TARGET_URL (no debería mostrarse el portal)..."
if curl -s -D "$TMP_HEADERS" -o "$TMP_BODY" --max-time 8 "$TARGET_URL"; then
  if check_portal_in_body "$TMP_BODY"; then
    log "ERROR: se sigue mostrando el portal después del login."
    log "Cuerpo guardado en: $TMP_BODY"
    exit 1
  else
    log "OK: acceso posterior sin portal (se asume navegación real)."
  fi
else
  log "ERROR: no se pudo obtener $TARGET_URL tras el login."
  exit 1
fi

log "Prueba completada. Respuestas HTTP guardadas en:"
log "  - Headers: $TMP_HEADERS"
log "  - Body:    $TMP_BODY"
