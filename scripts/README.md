# Directorio `scripts/`

Este directorio contiene **scripts auxiliares** para trabajar con el proyecto.

## Contenido esperado

Ejemplos de scripts que se irán añadiendo:

- Scripts de firewall:
  - `firewall_init.sh`: aplica las reglas base (bloqueo por defecto, permiso al portal, etc.).
  - `firewall_clear.sh` (o similar): limpia reglas o restaura un estado conocido.
- Scripts de arranque/parada:
  - `run_portal.sh`: arranca el servidor del portal cautivo con la configuración adecuada.
  - `stop_portal.sh`: detiene el servidor (si aplica).
- Scripts relacionados con el entorno de desarrollo:
  - Instalación de dependencias.
  - Puesta en marcha del entorno de pruebas.
- Scripts de mantenimiento:
  - `reset_sessions.sh`: elimina todas las sesiones persistidas (`config/sessions.json`).
- Scripts auxiliares de arranque:
  - `start_gateway.sh`: prepara firewall + portal HTTP.
  - `start_gateway_https.sh`: same pero con TLS y reconfigura firewall.
  - `start_tls_only.sh`: arranca solo el servidor HTTPS sin volver a tocar iptables (útil para tener ambas instancias simultáneas).

## Convenciones

- Scripts preferiblemente en **bash** (o el shell que se documente).
- Añadir al principio de cada script un comentario breve explicando qué hace.
- Cualquier script importante debe estar documentado también en `docs/desarrollo.md` o `docs/firewall.md`.
