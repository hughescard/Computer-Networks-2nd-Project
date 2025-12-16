# Checklist de requisitos y pruebas integrales (Issue #20)

Este documento resume los requisitos del portal cautivo, donde estan implementados y como validarlos. Los estados se dejan en **Pendiente** hasta ejecutar las pruebas en el laboratorio (gateway con iptables y clientes reales). Al completar cada prueba, actualiza la columna de estado.

## Checklist de requisitos

| Req | Implementacion / referencia | Prueba o verificacion rapida | Estado (probado / no) |
| --- | --------------------------- | ---------------------------- | --------------------- |
| R1  | Topologia y forwarding base: `docs/topologia.md`, `scripts/firewall_init.sh` habilita `ip_forward` y politicas DROP | En el gateway: `cat /proc/sys/net/ipv4/ip_forward` -> 1 y `sudo iptables -L FORWARD -n` muestra politica DROP por defecto | TESTED |
| R2  | Redireccion HTTP al portal (issue 13): regla `REDIRECT` en `scripts/firewall_init.sh`, detalle en `docs/firewall.md` | Cliente sin login: `curl -i http://example.com` debe mostrar el portal; gateway: `sudo iptables -t nat -L PREROUTING -n --line-numbers | grep REDIRECT` | TESTED |
| R3  | Servidor HTTP/HTTPS concurrente: `src/http_server.py` con `ThreadPoolExecutor` y soporte TLS | Arrancar `python3 src/http_server.py` (o con TLS usando `PORTAL_ENABLE_TLS=1`) y hacer GET concurrentes desde 2+ clientes | Pendiente lab |
| R4  | UI del portal (login/success/error/logout): plantillas en `src/templates/` con mensajes claros (issue 17) | GET `/login` y revisar que se muestren instrucciones y mensajes de error/resultado coherentes | TESTED |
| R5  | Archivo de usuarios y autenticacion basica: `config/usuarios.txt`, loader en `src/auth.py` | `python3 src/auth.py` para cargar usuarios y validar credenciales; login con usuario valido/invalidos | TESTED |
| R6  | Endpoint POST `/login` y manejo de errores: `handle_client` en `src/http_server.py` | `curl -d "username=admin&password=admin" http://<gateway>:8080/login` -> pagina de exito; credenciales invalidas -> pagina de error | Pendiente lab |
| R7  | Sesiones en memoria con TTL y persistencia: `src/sessions.py` guarda en `config/sessions.json` | Lanzar con `PORTAL_SESSION_TTL=5`, hacer login y esperar expiracion; revisar que la sesion desaparece y que `sessions.json` se actualiza | Pendiente lab |
| R8  | Reglas dinamicas de firewall por cliente: `src/firewall_dynamic.py` (FORWARD ACCEPT + PREROUTING RETURN) llamado desde `sessions.py` y logout en `http_server.py` | Tras login: `sudo iptables -L FORWARD -n --line-numbers` y `sudo iptables -t nat -L PREROUTING -n --line-numbers` deben mostrar reglas para la IP/MAC; tras logout desaparecen | Pendiente lab |
| R9  | Concurrencia y multiusuario: hilos en `http_server.py`, scripts `tests/pruebas_basicas.sh` y `tests/pruebas_contenedores.sh` | Ejecutar el script de pruebas en dos clientes (o contenedores) casi en paralelo y confirmar que ambos logran navegar | Pendiente lab |
| R10 | NAT/enmascaramiento de salida: regla `MASQUERADE` en `scripts/firewall_init.sh` (issue 14) | Gateway: `sudo iptables -t nat -L POSTROUTING -n -v | grep MASQUERADE`; cliente autenticado resuelve DNS y navega | Pendiente lab |
| R11 | Portal por HTTPS: TLS en `_build_tls_context` (`src/http_server.py`), certs en `config/tls`, scripts `scripts/start_tls_only.sh` y `scripts/start_gateway_https.sh`, guia `docs/https.md` | Arrancar con `PORTAL_ENABLE_TLS=1 PORTAL_TLS_CERT=... PORTAL_TLS_KEY=... PORTAL_HTTP_PORT=8443` y `curl -k https://<gateway>:8443/login` desde la LAN | Pendiente lab |
| R12 | Anti-suplantacion IP+MAC: `src/arp_lookup.py`, sesiones guardan MAC y `firewall_dynamic.permitir_ip_mac` usa `--mac-source`; explicado en `docs/antisuplantacion.md` | Verificar que el gateway tenga entrada ARP de la IP y que las reglas `FORWARD`/`PREROUTING` incluyan `--mac-source <MAC>` tras el login | Pendiente lab |
| R13 | Sistema de logs: logging configurado en `src/http_server.py` escribiendo `logs/portal_captivo.log` (documentado en `docs/logs.md`) | Durante intentos de login exitosos/fallidos, revisar `tail -f logs/portal_captivo.log` y confirmar que se registran eventos y reglas de firewall | Pendiente lab |
| R14 | Documentacion y despliegue final (issue 19): `README.md`, `docs/desarrollo.md`, `docs/firewall.md`, `docs/topologia.md`, scripts `start_gateway*.sh` | Seguir README desde cero en el gateway: preparar red, aplicar firewall y arrancar portal; actualizar este estado al completarlo | Pendiente lab |
| R15 | Entorno reproducible y commits: `scripts/dev_env.sh`, convencion en `docs/desarrollo.md` y `scripts/commit.sh` | Ejecutar `./scripts/dev_env.sh` y hacer un commit usando `./scripts/commit.sh` siguiendo el formato acordado | Pendiente lab |

## Pruebas integrales finales

Secuencia recomendada para validar los puntos criticos del sistema (requiere gateway como root y al menos un cliente en la LAN).

1. **Preparacion:** en el gateway, configurar IPs segun `docs/topologia.md` y lanzar `scripts/start_gateway.sh` (o `scripts/start_gateway_https.sh` si probas TLS). Verifica `ip_forward=1` y politicas DROP.
2. **Sin login -> sin navegacion:** desde un cliente, `curl -i http://example.com` debe devolver la pagina del portal; en el gateway no deben aparecer reglas `FORWARD ACCEPT`/`PREROUTING RETURN` para la IP del cliente.
3. **Login + navegacion:** `curl -d "username=<user>&password=<pass>" http://<gateway>:8080/login` debe responder con exito; repite `curl http://example.com` y debe llegar al sitio real. En el gateway deben existir reglas `ACCEPT` y `RETURN` para esa IP (y MAC si se resolvio).
4. **Redireccion automatica:** con otra IP sin autenticar, confirma que sigue viendo el portal y que la regla global `REDIRECT --to-ports <PORTAL_HTTP_PORT>` esta activa en `nat PREROUTING`.
5. **NAT:** en el gateway confirma `MASQUERADE` en `nat POSTROUTING`; desde un cliente autenticado haz `nslookup example.com` y `curl http://example.com` para verificar respuesta.
6. **HTTPS:** iniciar el portal con TLS (cert/llave en `config/tls`), abrir `https://<gateway>:8443/login` con `curl -k` o navegador y repetir el login. Si usas un puerto TLS distinto, exporta `PORTAL_HTTPS_PORT` antes de `firewall_init.sh`.
7. **Anti-suplantacion IP+MAC:** asegurate de que el gateway tenga entrada ARP para la IP del cliente (`ip neigh show <IP>`). Tras el login, revisa que las reglas de `iptables` incluyan `--mac-source <MAC>`; si la MAC cambia, la sesion debe ser rechazada y no se debe crear nueva regla hasta relogin.
8. **Concurrencia:** ejecuta `tests/pruebas_basicas.sh` en dos clientes (o `tests/pruebas_contenedores.sh` en uno solo) casi al mismo tiempo y valida que ambos navegantes mantengan sus reglas activas.
9. **Logs y limpieza:** monitorea `logs/portal_captivo.log` durante las pruebas y ejecuta `scripts/reset_sessions.sh` o logout (`/logout`) para eliminar reglas y sesiones al cierre.

## Registro rapido de ejecucion

Usa esta tabla para anotar la ultima corrida de pruebas integrales.

| Escenario | Fecha | Resultado | Evidencia / notas |
| --------- | ----- | --------- | ----------------- |
| Sin login -> sin navegacion | Pendiente | Pendiente | |
| Login + navegacion | Pendiente | Pendiente | |
| Redireccion automatica | Pendiente | Pendiente | |
| NAT / MASQUERADE | Pendiente | Pendiente | |
| HTTPS | Pendiente | Pendiente | |
| Anti-suplantacion IP+MAC | Pendiente | Pendiente | |
| Concurrencia (2+ clientes) | Pendiente | Pendiente | |
| Logs y limpieza | Pendiente | Pendiente | |
