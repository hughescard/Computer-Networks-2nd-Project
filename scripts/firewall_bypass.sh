#!/bin/bash
# scripts/firewall_bypass.sh
# Activa o desactiva un bypass temporal de redirección/forwarding para una IP de cliente.
# Útil para dar Internet mientras se instalan paquetes y luego restaurar el portal cautivo.

set -euo pipefail

IPTABLES_BIN=${IPTABLES_BIN:-$(command -v iptables || echo /sbin/iptables)}
LAN_IF=${LAN_IF:-enp0s8}          # interfaz hacia la LAN
WAN_IF=${WAN_IF:-enp0s3}          # interfaz hacia Internet/NAT
CAPTIVE_HTTP_PORT=${CAPTIVE_HTTP_PORT:-80}  # puerto interceptado (HTTP claro)

usage() {
  echo "Uso: sudo $0 <enable|disable> <IP_CLIENTE>" >&2
  echo "Ejemplo: sudo $0 enable 192.168.50.10" >&2
  exit 1
}

[ $# -eq 2 ] || usage
ACTION="$1"
CLIENT_IP="$2"

if [ "$EUID" -ne 0 ]; then
  echo "Este script debe ejecutarse como root" >&2
  exit 1
fi

if [ ! -x "$IPTABLES_BIN" ]; then
  echo "No se encontró iptables" >&2
  exit 1
fi

case "$ACTION" in
  enable)
    echo "[*] Añadiendo bypass para $CLIENT_IP (no redirección HTTP y forward permitido)..."
    "$IPTABLES_BIN" -t nat -I PREROUTING 1 -i "$LAN_IF" -s "$CLIENT_IP" -p tcp --dport "$CAPTIVE_HTTP_PORT" -j RETURN
    "$IPTABLES_BIN" -I FORWARD 1 -s "$CLIENT_IP" -j ACCEPT
    ;;
  disable)
    echo "[*] Eliminando bypass para $CLIENT_IP..."
    "$IPTABLES_BIN" -t nat -D PREROUTING -i "$LAN_IF" -s "$CLIENT_IP" -p tcp --dport "$CAPTIVE_HTTP_PORT" -j RETURN || true
    "$IPTABLES_BIN" -D FORWARD -s "$CLIENT_IP" -j ACCEPT || true
    ;;
  *)
    usage
    ;;
esac

echo "[*] Reglas actuales (resumen):"
"$IPTABLES_BIN" -t nat -L PREROUTING -n --line-numbers | head
"$IPTABLES_BIN" -L FORWARD -n --line-numbers | head
