#!/usr/bin/env bash
# Prueba automatizada del requisito R12 (anti-suplantación IP+MAC) usando Docker/macvlan.
#
# Se ejecuta en la VM cliente (no en el gateway) y valida:
# - Un cliente "legit" hace login y puede salir a Internet (ping 8.8.8.8).
# - Un "atacante" usa la misma IP pero otra MAC y NO puede salir a Internet,
#   y en HTTP sigue viendo el portal (no aplica bypass).
#
# Requisitos:
# - Docker instalado y con permisos para crear redes macvlan.
# - La interfaz LAN del cliente en modo promiscuo (VirtualBox Allow All y/o promisc en Linux).
#
# Variables (opcional):
#   LAN_IF=enp0s3
#   NET_NAME=portal_macvlan
#   SUBNET=192.168.50.0/24
#   GATEWAY=192.168.50.1
#   CLIENT_IP=192.168.50.101
#   PORTAL_HOST=192.168.50.1
#   PORTAL_PORT=8080
#   TARGET_URL=http://93.184.216.34
#   PORTAL_USER=admin
#   PORTAL_PASS=admin
#   IMAGE=alpine:3
#   PROMISC_ON=1
#   CLEANUP_SESSION=1
#
# Uso:
#   LAN_IF=enp0s3 CLIENT_IP=192.168.50.101 PORTAL_HOST=192.168.50.1 PORTAL_PORT=8080 \
#   bash tests/prueba_r12_antisuplantacion.sh

set -euo pipefail

LAN_IF="${LAN_IF:-enp0s3}"
NET_NAME="${NET_NAME:-portal_macvlan}"
SUBNET="${SUBNET:-192.168.50.0/24}"
GATEWAY="${GATEWAY:-192.168.50.1}"
CLIENT_IP="${CLIENT_IP:-192.168.50.101}"
PORTAL_HOST="${PORTAL_HOST:-192.168.50.1}"
PORTAL_PORT="${PORTAL_PORT:-8080}"
TARGET_URL="${TARGET_URL:-http://93.184.216.34}"
PORTAL_USER="${PORTAL_USER:-admin}"
PORTAL_PASS="${PORTAL_PASS:-admin}"
IMAGE="${IMAGE:-alpine:3}"
PROMISC_ON="${PROMISC_ON:-1}"
CLEANUP_SESSION="${CLEANUP_SESSION:-1}"
DEBUG="${DEBUG:-0}"

log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"; }

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Falta el comando requerido: $1" >&2
    exit 1
  fi
}

random_mac() {
  # MAC local-admin (02:xx:xx:xx:xx:xx)
  printf '02:%02x:%02x:%02x:%02x:%02x\n' \
    $((RANDOM % 256)) $((RANDOM % 256)) $((RANDOM % 256)) $((RANDOM % 256)) $((RANDOM % 256))
}

ensure_promisc() {
  if [[ "$PROMISC_ON" != "1" ]]; then
    return 0
  fi
  if ip link show "$LAN_IF" | head -1 | grep -q "PROMISC"; then
    return 0
  fi
  log "Habilitando modo promiscuo en $LAN_IF..."
  if command -v sudo >/dev/null 2>&1; then
    sudo ip link set "$LAN_IF" promisc on || true
  else
    ip link set "$LAN_IF" promisc on || true
  fi
  if ! ip link show "$LAN_IF" | head -1 | grep -q "PROMISC"; then
    log "WARNING: $LAN_IF no quedó en PROMISC. Si macvlan falla, revisa VirtualBox (Allow All) y promisc en Linux."
  fi
}

ensure_network() {
  if docker network inspect "$NET_NAME" >/dev/null 2>&1; then
    return 0
  fi
  log "Creando red macvlan '$NET_NAME' en $LAN_IF ($SUBNET, gw $GATEWAY)..."
  docker network create -d macvlan \
    --subnet "$SUBNET" \
    --gateway "$GATEWAY" \
    -o parent="$LAN_IF" \
    "$NET_NAME"
}

cleanup_containers() {
  docker rm -f "$1" >/dev/null 2>&1 || true
}

run_capture() {
  # Ejecuta un comando y devuelve su salida. Si falla, imprime salida+error y termina.
  local label="$1"
  shift
  local out rc
  set +e
  out="$("$@" 2>&1)"
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    echo "$out" >&2
    echo "ERROR: $label (exit $rc)" >&2
    exit "$rc"
  fi
  echo "$out"
}

require_cmd ip
require_cmd docker

ensure_promisc
ensure_network

LEGIT_NAME="r12-legit-$(echo "$CLIENT_IP" | tr . -)"
ATTACK_NAME="r12-attacker-$(echo "$CLIENT_IP" | tr . -)"

cleanup_containers "$LEGIT_NAME"
cleanup_containers "$ATTACK_NAME"

log "=== R12 anti-suplantación IP+MAC ==="
log "LAN_IF=$LAN_IF NET_NAME=$NET_NAME CLIENT_IP=$CLIENT_IP PORTAL=$PORTAL_HOST:$PORTAL_PORT TARGET_URL=$TARGET_URL"

log "[1/3] Cliente legit: login y ping a Internet..."
docker_rm_flag=(--rm)
if [[ "$DEBUG" == "1" ]]; then
  docker_rm_flag=()
fi

legit_output="$(run_capture "cliente legit: fallo al loguear o salir a Internet" \
  docker run "${docker_rm_flag[@]}" --name "$LEGIT_NAME" \
    --network "$NET_NAME" --ip "$CLIENT_IP" \
    -e PORTAL_HOST="$PORTAL_HOST" -e PORTAL_PORT="$PORTAL_PORT" \
    -e PORTAL_USER="$PORTAL_USER" -e PORTAL_PASS="$PORTAL_PASS" \
    "$IMAGE" sh -c '
      set -e
      echo "LEGIT_MAC=$(cat /sys/class/net/eth0/address)"
      login_html="$(wget -q -O - --post-data "username=${PORTAL_USER}&password=${PORTAL_PASS}" "http://${PORTAL_HOST}:${PORTAL_PORT}/login" || true)"
      # El error template también contiene la palabra "autenticación", así que buscamos una señal inequívoca de éxito.
      if ! echo "$login_html" | grep -qi "Autenticaci" || ! echo "$login_html" | grep -qi "exitosa"; then
        echo "ERROR: login falló (no se detectó Autenticación exitosa)."
        echo "--- LOGIN_HTML (primeras 15 líneas) ---"
        echo "$login_html" | head -n 15
        exit 10
      fi
      if ! ping -c1 -W2 8.8.8.8 >/dev/null; then
        echo "ERROR: ping 8.8.8.8 falló luego de login (revisa NAT/MASQUERADE y regla IP+MAC)"
        exit 11
      fi
      echo "LEGIT_OK"
    ' \
)"
echo "$legit_output" | sed 's/^/[legit] /'
LEGIT_MAC="$(echo "$legit_output" | sed -n 's/^LEGIT_MAC=//p' | head -n1)"
if [[ -z "${LEGIT_MAC:-}" ]]; then
  echo "No se pudo leer la MAC del cliente legit." >&2
  exit 1
fi

log "[2/3] Atacante: misma IP, distinta MAC (sin login)..."
ATTACKER_MAC="${ATTACKER_MAC:-$(random_mac)}"
if [[ "$ATTACKER_MAC" == "$LEGIT_MAC" ]]; then
  ATTACKER_MAC="$(random_mac)"
fi
log "LEGIT_MAC=$LEGIT_MAC"
log "ATTACKER_MAC=$ATTACKER_MAC"

attack_output="$(run_capture "atacante: anti-spoof no se comportó como se esperaba" \
  docker run "${docker_rm_flag[@]}" --name "$ATTACK_NAME" \
    --network "$NET_NAME" --ip "$CLIENT_IP" --mac-address "$ATTACKER_MAC" \
    -e PORTAL_HOST="$PORTAL_HOST" -e PORTAL_PORT="$PORTAL_PORT" -e TARGET_URL="$TARGET_URL" \
    "$IMAGE" sh -c '
      set -e
      echo "ATTACKER_MAC=$(cat /sys/class/net/eth0/address)"
      # Debe poder llegar al portal (gateway) aunque esté bloqueado para Internet.
      if ! wget -q -O - "http://${PORTAL_HOST}:${PORTAL_PORT}/login" | grep -qi "Iniciar sesi"; then
        echo "ERROR: no se pudo acceder al portal desde el atacante (revisa conectividad al gateway)"
        exit 20
      fi
      # Sin bypass por IP+MAC: al pedir HTTP al exterior debe seguir viendo el portal.
      if ! wget -q -O - "${TARGET_URL}" | grep -qi "Portal Cautivo\|Iniciar sesi"; then
        echo "ERROR: el atacante no vio el portal al pedir HTTP externo (posible bypass indebido)"
        exit 21
      fi
      # No debe poder salir a Internet (ICMP) sin la MAC autorizada.
      if ping -c1 -W2 8.8.8.8 >/dev/null 2>&1; then
        echo "ERROR: el atacante pudo hacer ping a Internet (anti-spoof falló)."
        exit 22
      fi
      echo "ATTACK_OK"
    ' \
)"
echo "$attack_output" | sed 's/^/[attacker] /'

log "[3/3] Limpieza (opcional): logout por IP..."
if [[ "$CLEANUP_SESSION" == "1" ]]; then
  docker run --rm \
    --network "$NET_NAME" --ip "$CLIENT_IP" --mac-address "$ATTACKER_MAC" \
    -e PORTAL_HOST="$PORTAL_HOST" -e PORTAL_PORT="$PORTAL_PORT" \
    "$IMAGE" sh -c 'wget -q -O - "http://${PORTAL_HOST}:${PORTAL_PORT}/logout" >/dev/null || true'
  log "Logout enviado."

  log "Verificando que la sesión fue revocada (ping debe fallar con la MAC original)..."
  if docker run --rm \
      --network "$NET_NAME" --ip "$CLIENT_IP" --mac-address "$LEGIT_MAC" \
      "$IMAGE" sh -c 'ping -c1 -W2 8.8.8.8 >/dev/null'; then
    echo "WARNING: parece que la sesión sigue activa para $CLIENT_IP/$LEGIT_MAC. Ejecuta logout manual o limpia sesiones en el gateway." >&2
  else
    log "Revocación confirmada."
  fi
else
  log "CLEANUP_SESSION=0: no se envió logout."
fi

if [[ "$DEBUG" == "1" ]]; then
  log "DEBUG=1: contenedores (si existen) no se borraron automáticamente."
  log "Para limpiar: docker rm -f \"$LEGIT_NAME\" \"$ATTACK_NAME\""
fi

log "OK: R12 pasó (IP+MAC bloquea al atacante)."
