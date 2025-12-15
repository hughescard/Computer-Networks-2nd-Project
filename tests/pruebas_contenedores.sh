#!/usr/bin/env bash
# Prueba de concurrencia con contenedores Docker como clientes (Issue #12).
# Ejecutar en la VM cliente (no en el gateway) para levantar varios clientes
# simultáneos en la misma máquina usando una red macvlan con IPs de la LAN.
#
# Requisitos: Docker instalado y permisos para crear redes macvlan.
# Ejecutar desde la raíz del repo (para montar tests/pruebas_basicas.sh).
#
# Variables configurables:
#   LAN_IF        Interfaz del cliente hacia el gateway (por defecto enp0s3)
#   NET_NAME      Nombre de la red macvlan (por defecto portal_macvlan)
#   SUBNET        Subred de la LAN (por defecto 192.168.50.0/24)
#   GATEWAY       Gateway de la LAN (por defecto 192.168.50.1)
#   CLIENT_IPS    Lista de IPs para los contenedores (por defecto "192.168.50.101 192.168.50.102")
#   PORTAL_HOST   IP del gateway/portal
#   PORTAL_PORT   Puerto donde escucha el portal (redirigido desde 80)
#   TARGET_URL    URL HTTP para probar redirección (por defecto http://example.com)
#   PORTAL_USER   Usuario para login (por defecto admin)
#   PORTAL_PASS   Contraseña para login (por defecto admin)
#   IMAGE         Imagen base (por defecto alpine:3; instala curl+bash en el entrypoint)

set -euo pipefail

LAN_IF="${LAN_IF:-enp0s3}"
NET_NAME="${NET_NAME:-portal_macvlan}"
SUBNET="${SUBNET:-192.168.50.0/24}"
GATEWAY="${GATEWAY:-192.168.50.1}"
CLIENT_IPS="${CLIENT_IPS:-192.168.50.101 192.168.50.102}"
PORTAL_HOST="${PORTAL_HOST:-192.168.50.1}"
PORTAL_PORT="${PORTAL_PORT:-8080}"
TARGET_URL="${TARGET_URL:-http://example.com}"
PORTAL_USER="${PORTAL_USER:-admin}"
PORTAL_PASS="${PORTAL_PASS:-admin}"
IMAGE="${IMAGE:-alpine:3}"

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"; }

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker no está instalado o no está en PATH." >&2
  exit 1
fi

if ! docker network inspect "$NET_NAME" >/dev/null 2>&1; then
  log "Creando red macvlan '$NET_NAME' en $LAN_IF ($SUBNET, gw $GATEWAY)..."
  docker network create -d macvlan \
    --subnet "$SUBNET" \
    --gateway "$GATEWAY" \
    -o parent="$LAN_IF" \
    "$NET_NAME"
else
  log "Red '$NET_NAME' ya existe, reutilizando."
fi

ROOT_DIR="$(pwd)"

for ip in $CLIENT_IPS; do
  cname="cliente-$(echo "$ip" | tr . -)"
  log "Lanzando contenedor $cname con IP $ip..."
  docker run --rm --name "$cname" \
    --network "$NET_NAME" --ip "$ip" \
    -e PORTAL_HOST -e PORTAL_PORT -e TARGET_URL -e PORTAL_USER -e PORTAL_PASS \
    "$IMAGE" sh -c "
      set -e
      check_portal() {
        wget -qO- \"$TARGET_URL\" | grep -qi 'Portal Cautivo\\|Iniciar sesi' && return 0
        return 1
      }
      echo \"[conteiner-$ip] Paso 1: comprobar portal sin login...\"
      check_portal || { echo 'ERROR: no se detectó portal antes de login'; exit 1; }
      echo \"[conteiner-$ip] Paso 2: login...\"
      wget -qO- --post-data \"username=${PORTAL_USER}&password=${PORTAL_PASS}\" \"http://${PORTAL_HOST}:${PORTAL_PORT}/login\" | grep -qi 'Autenticaci' || { echo 'ERROR: login falló'; exit 1; }
      echo \"[conteiner-$ip] Paso 3: comprobar acceso tras login...\"
      if wget -qO- \"$TARGET_URL\" | grep -qi 'Portal Cautivo\\|Iniciar sesi'; then
        echo 'ERROR: aún aparece el portal después de login'; exit 1;
      fi
      echo \"[conteiner-$ip] OK\"
    "
done

log "Pruebas en contenedores finalizadas."
