# Pruebas básicas – Issue #12

Este documento resume las **pruebas funcionales** ejecutadas tras integrar las issues #1–#11 y #13–#16.  
Todas las pruebas se hicieron en el laboratorio descrito en `docs/topologia.md`:

- **Gateway/Portal** (`gateway-redes`):
  - Interfaz LAN `enp0s8` → `192.168.50.1/24`
  - Interfaz WAN `enp0s3` → NAT de VirtualBox (DHCP)
  - Portal en ejecución: `sudo -E PORTAL_HTTP_PORT=8080 PORTAL_LAN_IF=enp0s8 python3 src/http_server.py`
  - Firewall aplicado con `sudo bash scripts/firewall_init.sh`.
- **Cliente A** (`cliente1`): `192.168.50.10/24`, gateway `192.168.50.1`.
- **Cliente B** (`cliente2`): `192.168.50.11/24`, gateway `192.168.50.1`.
- Archivo de usuarios (`config/usuarios.txt`) con credenciales `admin:admin`, `invitado:invitado123`.

> Todos los comandos se ejecutan como `root` o usando `sudo`, ya que el portal necesita modificar iptables cuando las sesiones cambian.

---

## Escenario 1 – Redirección automática y portal visible

1. En el gateway ejecutar `sudo bash scripts/firewall_init.sh`.
2. Desde Cliente A (sin sesión) ejecutar `curl -i http://example.com`.
3. Resultado esperado/observado:
   - Respuesta `HTTP/1.1 200 OK` con el HTML de `src/templates/login.html`.
   - `sudo iptables -t nat -L PREROUTING -n --line-numbers | head -n 3` muestra la regla `REDIRECT --to-ports 8080` insertada por el script (issue #13).

## Escenario 2 – Login correcto con dos clientes simultáneos

1. Clientes A y B abren `http://portal` (redirigidos vía PREROUTING).
2. Cada cliente envía `POST /login` con credenciales válidas (`admin` y `invitado`).
3. Resultado esperado/observado:
   - Plantilla `login_success.html` en ambos clientes.
   - En el gateway:
     ```bash
     sudo iptables -L FORWARD -n --line-numbers | head -n 5
     # → Entradas ACCEPT para 192.168.50.10 y 192.168.50.11 en primera posición.
     sudo iptables -t nat -L PREROUTING -n --line-numbers | head -n 5
     # → Entradas RETURN para las mismas IPs (bypass del portal).
     ```
   - `config/sessions.json` contiene dos sesiones con usuario/IP (y MAC si estaba en la tabla ARP).
   - Ambos clientes pueden navegar (`curl https://www.example.org` responde correctamente).

## Escenario 3 – Login inválido

1. Cliente A envía `POST /login` con contraseña incorrecta.
2. Resultado esperado/observado:
   - Plantilla `login_error.html`.
   - No se modifica `iptables` (verificado con `sudo iptables -L FORWARD -n | grep 192.168.50.10` → sin coincidencias nuevas).
   - En logs (`journalctl -u portal` o salida estándar) aparece `Login fallido` y no se crean entradas en `config/sessions.json`.

## Escenario 4 – Expiración/limpieza de sesiones

1. Lanzar el portal con `PORTAL_SESSION_TTL=30` (30 s).
2. Cliente A inicia sesión correctamente.
3. Tras 35 s ejecutar `python3 -c "import sessions; sessions.limpiar_sesiones_expiradas()"` en el gateway.
4. Resultado esperado/observado:
   - El comando devuelve `1` sesión eliminada y loguea la eliminación.
   - `sudo iptables -L FORWARD -n --line-numbers | grep 192.168.50.10` ya no muestra la regla ACCEPT (se eliminó).
   - El cliente vuelve a ser redirigido al portal hasta volver a autenticarse.

---

## Resumen

- Las funcionalidades principales (redirigir HTTP, autenticar, crear sesiones, permitir navegación y limpiar reglas) funcionan con múltiples clientes concurrentes.
- Los resultados anteriores sirven como **punto de partida** para automatizar pruebas (bash/python) en `tests/`.
- Si aparece algún comportamiento inesperado durante estas pruebas, se debe crear un nuevo issue y documentarlo en esta misma sección.
