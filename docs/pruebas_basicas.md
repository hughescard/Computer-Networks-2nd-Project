# Pruebas funcionales básicas (Issue #12)

Objetivo: validar que el portal cautivo funciona con **2+ clientes simultáneos** siguiendo la topología de laboratorio y los requisitos previos (issues 1‑11).

## Preparación

- Topología según `docs/topologia.md` (gateway `192.168.50.1/24`, clientes `192.168.50.x/24`).
- Firewall base aplicado: `sudo bash scripts/firewall_init.sh` (incluye redirección HTTP y NAT).
- Servidor del portal activo: `sudo PORTAL_HTTP_PORT=8080 python3 src/http_server.py`.
- Dos clientes configurados (ejemplo): `cliente1=192.168.50.10`, `cliente2=192.168.50.11`, con DNS accesible (ej. `8.8.8.8`).
- Credenciales de prueba en `config/usuarios.txt` (por defecto `admin:admin`).

## Escenarios de prueba

1) **Redirección HTTP sin login (cliente1 y cliente2)**
   - Paso: desde cada cliente `curl -i http://example.com` (o abre cualquier sitio HTTP).
   - Esperado: aparece la página del portal (login), no se resuelve el sitio real; en el gateway no hay reglas FORWARD/RETURN específicas para esas IPs.

2) **Login exitoso + navegación (cliente1)**
   - Paso: POST `/login` con credenciales válidas (`admin:admin`), luego repetir `curl http://example.com`.
   - Esperado: el POST devuelve página de éxito; en el gateway aparecen reglas `ACCEPT` en FORWARD y `RETURN` en `nat PREROUTING` para `cliente1`; el segundo `curl` ya llega al destino real (no vuelve el portal).

3) **Concurrencia: login cliente2 mientras cliente1 ya navega**
   - Paso: con cliente1 autenticado, repetir el escenario 2 en cliente2.
   - Esperado: ambos pueden navegar; en iptables hay dos entradas (cliente1 y cliente2); el portal responde a múltiples peticiones simultáneas sin bloquearse.

4) **Login fallido (cliente2)**
   - Paso: enviar credenciales incorrectas.
   - Esperado: página de error; no se crean reglas FORWARD/RETURN nuevas para esa IP.

5) *(Opcional)* **Expiración de sesión**
   - Paso: ajustar `PORTAL_SESSION_TTL` a un valor pequeño, autenticarse y esperar la expiración.
   - Esperado: tras TTL, desaparecen las reglas dinámicas para la IP y vuelve a mostrarse el portal.

## Scripts de apoyo

- `tests/pruebas_basicas.sh`: ejecutarlo en cada cliente para automatizar los escenarios 1 y 2.

  ```bash
  PORTAL_HOST=192.168.50.1 PORTAL_PORT=8080 \
  TARGET_URL=http://example.com \
  PORTAL_USER=admin PORTAL_PASS=admin \
  bash tests/pruebas_basicas.sh
  ```

  - Salida esperada: detecta portal antes del login, login exitoso y acceso posterior sin portal. Devuelve código distinto de 0 si el login falla o si después del login se sigue viendo el portal.
  - Para cubrir concurrencia, lanza el script casi al mismo tiempo en cliente1 y cliente2.

### Pruebas con contenedores Docker en el cliente (concurrencia en una sola VM)

Si solo tienes una VM cliente, puedes simular varios clientes con contenedores usando macvlan (cada contenedor recibe una IP de la LAN):

1. En la VM cliente, ejecuta:

   ```bash
   LAN_IF=enp0s3 CLIENT_IPS="192.168.50.101 192.168.50.102" \
   PORTAL_HOST=192.168.50.1 PORTAL_PORT=8080 \
   bash tests/pruebas_contenedores.sh
   ```

   - `LAN_IF` es la interfaz de la VM cliente hacia el gateway.
   - Ajusta `CLIENT_IPS` con tantas IPs libres como contenedores quieras lanzar.
2. El script crea una red macvlan y corre una versión ligera de `pruebas_basicas` dentro de cada contenedor usando `alpine:3` (solo requiere `wget`, ya incluido).
3. Verifica en el gateway que aparezcan reglas `RETURN`/`ACCEPT` para todas las IPs usadas.

## Registro de resultados (rellenar tras ejecución)

| Escenario | Cliente(s) | Observado | Fecha |
| --------- | ---------- | --------- | ----- |
| Redirección sin login | cliente1, cliente2 | _pendiente de ejecutar en laboratorio_ | |
| Login + navegación | cliente1 | _pendiente de ejecutar en laboratorio_ | |
| Concurrencia (dos clientes) | cliente1 + cliente2 | _pendiente de ejecutar en laboratorio_ | |
| Login fallido | cliente2 | _pendiente de ejecutar en laboratorio_ | |
| Expiración (opcional) | cliente1 | _pendiente de ejecutar en laboratorio_ | |

## Checklist rápido en el gateway

- `sudo iptables -t nat -L PREROUTING -n --line-numbers` muestra la regla REDIRECT global y, tras login, reglas `RETURN` para cada IP autenticada.
- `sudo iptables -L FORWARD -n --line-numbers` muestra reglas `ACCEPT` para las IPs autenticadas.
- `sudo tail -f /var/log/syslog` (o el log de tu elección) mientras ejecutas las pruebas para ver eventos del servidor y del firewall.
