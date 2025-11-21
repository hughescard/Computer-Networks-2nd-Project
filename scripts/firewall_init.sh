#!/bin/bash
# scripts/firewall_init.sh
# Configuración base del firewall para el portal cautivo.
# Debe ejecutarse en la máquina gateway (gateway-redes) como root.

set -e

# Interfaces (ajustar si cambian los nombres)
WAN_IF="enp0s3"   # interfaz hacia Internet (NAT VirtualBox)
LAN_IF="enp0s8"   # interfaz hacia la red interna 192.168.50.0/24

PORTAL_HTTP_PORT=80   # puerto donde escuchará el portal cautivo

if [ "$EUID" -ne 0 ]; then
  echo "Este script debe ejecutarse como root" >&2
  exit 1
fi

echo "[*] Habilitando IP forwarding (IPv4)..."
echo 1 > /proc/sys/net/ipv4/ip_forward

echo "[*] Limpiando reglas anteriores..."
iptables -F
iptables -t nat -F
iptables -t mangle -F
iptables -X || true

echo "[*] Estableciendo políticas por defecto..."
# IMPORTANTE: por diseño del proyecto, el tráfico reenviado
# debe estar bloqueado hasta que el usuario inicie sesión.
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

echo "[*] Permitiendo tráfico local (loopback)..."
iptables -A INPUT -i lo -j ACCEPT

echo "[*] Permitiendo tráfico ya establecido/relacionado..."
iptables -A INPUT   -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

echo "[*] Permitiendo ICMP (ping) desde la LAN al gateway (debug)..."
iptables -A INPUT -i "$LAN_IF" -p icmp -j ACCEPT

echo "[*] Permitiendo SSH al gateway desde la LAN (opcional)..."
iptables -A INPUT -i "$LAN_IF" -p tcp --dport 22 -j ACCEPT

echo "[*] Permitiendo acceso HTTP al portal desde la LAN..."
iptables -A INPUT -i "$LAN_IF" -p tcp --dport "$PORTAL_HTTP_PORT" -j ACCEPT

echo "[*] Firewall base aplicado."
iptables -L -n -v
