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

## Convenciones

- Scripts preferiblemente en **bash** (o el shell que se documente).
- Añadir al principio de cada script un comentario breve explicando qué hace.
- Cualquier script importante debe estar documentado también en `docs/desarrollo.md` o `docs/firewall.md`.
