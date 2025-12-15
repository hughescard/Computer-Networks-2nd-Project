#!/bin/bash
# scripts/firewall_init.sh
# Configuración base del firewall para el portal cautivo.
# Debe ejecutarse en la máquina gateway (gateway-redes) como root.

set -e

IPTABLES_BIN=${IPTABLES_BIN:-$(command -v iptables || echo /sbin/iptables)}
IPTABLES_SAVE_BIN=${IPTABLES_SAVE_BIN:-$(command -v iptables-save || echo /sbin/iptables-save)}
MODPROBE_BIN=${MODPROBE_BIN:-$(command -v modprobe || echo /sbin/modprobe)}

# Verifica que nf_conntrack esté disponible antes de usar --ctstate.
ensure_conntrack() {
  if [ -x "$MODPROBE_BIN" ]; then
    if ! "$MODPROBE_BIN" -n nf_conntrack >/dev/null 2>&1; then
      echo "El módulo nf_conntrack no está disponible en este kernel." >&2
      exit 1
    fi
    if ! lsmod | grep -q '^nf_conntrack'; then
      "$MODPROBE_BIN" nf_conntrack >/dev/null 2>&1 || true
    fi
  elif [ ! -e /proc/net/nf_conntrack ] && [ ! -e /proc/net/ip_conntrack ]; then
    echo "No se detectó soporte conntrack y no se pudo verificar con modprobe." >&2
    exit 1
  fi
}

persist_rules() {
  if [ -x "$IPTABLES_SAVE_BIN" ]; then
    mkdir -p /etc/iptables
    "$IPTABLES_SAVE_BIN" > /etc/iptables/rules.v4
    echo "[*] Reglas guardadas en /etc/iptables/rules.v4 (iptables-persistent)."
  else
    echo "[!] iptables-save no disponible; instala iptables-persistent para cargar reglas al arranque." >&2
  fi
}

# Interfaces (ajustar si cambian los nombres)
WAN_IF="enp0s3"          # interfaz hacia Internet (NAT VirtualBox)
LAN_IF="enp0s8"          # interfaz hacia la red interna 192.168.50.0/24
HOST_IF="enp0s9"         # interfaz host-only hacia el PC admin
HOST_NET="192.168.56.0/24"

PORTAL_HTTP_PORT=${PORTAL_HTTP_PORT:-8080}   # puerto real donde escuchará el portal cautivo
CAPTIVE_HTTP_PORT=${CAPTIVE_HTTP_PORT:-80}   # puerto que interceptamos de los clientes (HTTP claro)
PORTAL_HTTPS_PORT=${PORTAL_HTTPS_PORT:-}     # si se define, habilita un puerto TLS para el portal

if [ "$EUID" -ne 0 ]; then
  echo "Este script debe ejecutarse como root" >&2
  exit 1
fi

if [ ! -x "$IPTABLES_BIN" ]; then
  echo "No se encontró el binario de iptables (buscado en PATH y /sbin/iptables)." >&2
  exit 1
fi

ensure_conntrack

echo "[*] Habilitando IP forwarding (IPv4)..."
echo 1 > /proc/sys/net/ipv4/ip_forward

echo "[*] Limpiando reglas anteriores..."
"$IPTABLES_BIN" -F
"$IPTABLES_BIN" -t nat -F
"$IPTABLES_BIN" -t mangle -F
"$IPTABLES_BIN" -X || true

echo "[*] Estableciendo políticas por defecto..."
# IMPORTANTE: por diseño del proyecto, el tráfico reenviado
# debe estar bloqueado hasta que el usuario inicie sesión.
"$IPTABLES_BIN" -P INPUT DROP
"$IPTABLES_BIN" -P FORWARD DROP
"$IPTABLES_BIN" -P OUTPUT ACCEPT

echo "[*] Permitiendo tráfico local (loopback)..."
"$IPTABLES_BIN" -A INPUT -i lo -j ACCEPT

echo "[*] Permitiendo tráfico ya establecido/relacionado..."
"$IPTABLES_BIN" -A INPUT   -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
"$IPTABLES_BIN" -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

### --- NUEVO: ADMIN POR HOST-ONLY (HOST_IF / HOST_NET) ---

echo "[*] Permitiendo ICMP (ping) desde el host (host-only)..."
"$IPTABLES_BIN" -A INPUT -i "$HOST_IF" -s "$HOST_NET" -p icmp -j ACCEPT

echo "[*] Permitiendo SSH al gateway desde el host (host-only)..."
"$IPTABLES_BIN" -A INPUT -i "$HOST_IF" -s "$HOST_NET" -p tcp --dport 22 -j ACCEPT

### --- FIN BLOQUE HOST-ONLY ---

echo "[*] Permitiendo ICMP (ping) desde la LAN al gateway (debug)..."
"$IPTABLES_BIN" -A INPUT -i "$LAN_IF" -p icmp -j ACCEPT

echo "[*] Permitiendo DNS desde la LAN hacia la WAN..."
"$IPTABLES_BIN" -A FORWARD -i "$LAN_IF" -o "$WAN_IF" -p udp --dport 53 -j ACCEPT
"$IPTABLES_BIN" -A FORWARD -i "$LAN_IF" -o "$WAN_IF" -p tcp --dport 53 -j ACCEPT

# NAT/enmascaramiento para que el tráfico de la LAN salga con la IP del gateway (necesario para resolver DNS y navegar)
echo "[*] Habilitando MASQUERADE en la salida WAN..."
"$IPTABLES_BIN" -t nat -A POSTROUTING -o "$WAN_IF" -j MASQUERADE



echo "[*] Permitiendo SSH al gateway desde la LAN (opcional)..."
"$IPTABLES_BIN" -A INPUT -i "$LAN_IF" -p tcp --dport 22 -j ACCEPT

echo "[*] Permitiendo acceso HTTP al portal desde la LAN (puerto $PORTAL_HTTP_PORT)..."
"$IPTABLES_BIN" -A INPUT -i "$LAN_IF" -p tcp --dport "$PORTAL_HTTP_PORT" -j ACCEPT

if [ -n "$PORTAL_HTTPS_PORT" ]; then
  echo "[*] Permitiendo acceso HTTPS al portal desde la LAN (puerto $PORTAL_HTTPS_PORT)..."
  "$IPTABLES_BIN" -A INPUT -i "$LAN_IF" -p tcp --dport "$PORTAL_HTTPS_PORT" -j ACCEPT
fi

echo "[*] Redirigiendo HTTP de clientes no autenticados hacia el portal..."
"$IPTABLES_BIN" -t nat -A PREROUTING -i "$LAN_IF" -p tcp --dport "$CAPTIVE_HTTP_PORT" -j REDIRECT --to-ports "$PORTAL_HTTP_PORT"



echo "[*] Firewall base aplicado."
"$IPTABLES_BIN" -L -n -v

echo "[*] Guardando reglas (iptables-save)..."
persist_rules
