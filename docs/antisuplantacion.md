# Anti-suplantación básica (IP + MAC)

## Objetivo
Reducir la posibilidad de que un equipo malicioso use la IP de otro cliente autenticado
(“IP spoofing” dentro de la LAN) permitiendo reglas de firewall que tengan en cuenta
tanto la IP como la dirección MAC cuando sea posible.

## Enfoque implementado
1. En el login, el gateway consulta su tabla ARP para obtener la MAC asociada a la IP del cliente.
   - Implementación: `src/arp_lookup.py` (usa `ip neigh show <IP>` y `/proc/net/arp`).
2. `sessions.crear_sesion(username, ip, mac=mac)` guarda ip+mac en memoria y disco.
3. `src/firewall_dynamic.py` crea reglas dinámicas que usan IP+MAC:
   - FORWARD: `-s <IP> -m mac --mac-source <MAC> -j ACCEPT`
   - PREROUTING (nat bypass): `-i <LAN_IF> -s <IP> -m mac --mac-source <MAC> -p tcp --dport 80 -j RETURN`
4. Si no se puede obtener la MAC, el sistema cae a reglas solo por IP (compatibilidad).

## Limitaciones
- **MAC spoofing:** un atacante en la misma red L2 puede falsificar la MAC; la protección no detiene a un atacante determinado.
- **ARP incompleta:** si el gateway no tiene entrada ARP para la IP (cliente inactivo), no se recuperará MAC. Se puede provocar ARP enviando ping al cliente antes del lookup, pero no lo hacemos automáticamente por seguridad/tiempo.
- **Compatibilidad de iptables:** `-m mac --mac-source` solo funciona en reglas que ven la cabecera Ethernet (de entrada por interfaz).
- **No aplicable si el cliente está detrás de NAT a su vez.**

## Verificación
- Comprobar regla NAT/POSTROUTING:
  ```bash
  sudo iptables -t nat -L POSTROUTING -n -v

- Comprobar reglas dinámicas (FORWARD + PREROUTING) para un cliente:

  ```bash
sudo iptables -L FORWARD -n --line-numbers | grep <IP>
sudo iptables -t nat -L PREROUTING -n --line-numbers | grep <IP>

- Si la sesión contiene MAC, la regla mostrará match mac y --mac-source <MAC>.

## Recomendaciones adicionales

*   **Hacer expiración corta para sesiones (TTL razonable).**
*   **Registrar y alertar si se detecta actividad anómala** (IP con MAC cambiante).
*   **En despliegues sensibles, usar port-security en switches** (limita cambio de MAC en puertos) o 802.1X.


