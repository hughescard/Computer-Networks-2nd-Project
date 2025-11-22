#!/bin/bash
# scripts/firewall_clear.sh
# Limpia reglas y deja el firewall en modo "todo permitido".
# Usar solo para depuración en laboratorio.

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Este script debe ejecutarse como root" >&2
  exit 1
fi

echo "[*] Deshabilitando IP forwarding..."
echo 0 > /proc/sys/net/ipv4/ip_forward

echo "[*] Limpiando reglas..."
iptables -F
iptables -t nat -F
iptables -t mangle -F
iptables -X || true

echo "[*] Políticas por defecto: ACCEPT en todas las cadenas..."
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
iptables -P OUTPUT ACCEPT

iptables -L -n -v
