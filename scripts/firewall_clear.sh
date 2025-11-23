#!/bin/bash
# scripts/firewall_clear.sh
# Limpia reglas y deja el firewall en modo "todo permitido".
# Usar solo para depuración en laboratorio.

set -e

IPTABLES_BIN=${IPTABLES_BIN:-$(command -v iptables || echo /sbin/iptables)}
IPTABLES_SAVE_BIN=${IPTABLES_SAVE_BIN:-$(command -v iptables-save || echo /sbin/iptables-save)}

persist_rules() {
  if [ -x "$IPTABLES_SAVE_BIN" ]; then
    mkdir -p /etc/iptables
    "$IPTABLES_SAVE_BIN" > /etc/iptables/rules.v4
    echo "[*] Reglas guardadas en /etc/iptables/rules.v4 (iptables-persistent)."
  else
    echo "[!] iptables-save no disponible; instala iptables-persistent para cargar reglas al arranque." >&2
  fi
}

if [ "$EUID" -ne 0 ]; then
  echo "Este script debe ejecutarse como root" >&2
  exit 1
fi

if [ ! -x "$IPTABLES_BIN" ]; then
  echo "No se encontró el binario de iptables (buscado en PATH y /sbin/iptables)." >&2
  exit 1
fi

echo "[*] Deshabilitando IP forwarding..."
echo 0 > /proc/sys/net/ipv4/ip_forward

echo "[*] Limpiando reglas..."
"$IPTABLES_BIN" -F
"$IPTABLES_BIN" -t nat -F
"$IPTABLES_BIN" -t mangle -F
"$IPTABLES_BIN" -X || true

echo "[*] Políticas por defecto: ACCEPT en todas las cadenas..."
"$IPTABLES_BIN" -P INPUT ACCEPT
"$IPTABLES_BIN" -P FORWARD ACCEPT
"$IPTABLES_BIN" -P OUTPUT ACCEPT

"$IPTABLES_BIN" -L -n -v

echo "[*] Guardando reglas (iptables-save)..."
persist_rules
