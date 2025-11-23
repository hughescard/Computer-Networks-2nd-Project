# Portal cautivo – 2do Proyecto de Redes de Computadoras (2025)

Este repositorio contiene la implementación de un **portal cautivo** que actúa como gateway de una red local y controla el acceso a Internet mediante un proceso de autenticación web.

El proyecto se desarrolla como parte de la asignatura **Redes de Computadoras (Curso 2025)**.

---

## Integrantes

- **@hughescard**
- **@D4R102004**

---

## Descripción general

El portal cautivo debe:

- Proveer un **endpoint HTTP** de inicio de sesión para los clientes de la red.
- **Bloquear el enrutamiento** desde la red interna hacia el exterior hasta que el usuario haya iniciado sesión.
- Gestionar un **mecanismo de cuentas de usuario** (definición y validación).
- Soportar el manejo de **múltiples usuarios concurrentes** (procesos y/o hilos).

Además, se buscará implementar varios **extras**:

- Detección automática del portal cautivo.
- Capa de seguridad **HTTPS** sobre la URL del portal.
- Medidas contra la **suplantación de IP** de usuarios autenticados.
- **Enmascaramiento (NAT)** de la red interna.
- Buen diseño y experiencia de usuario en la página del portal.
- Cualquier otra mejora creativa que aporte valor.

---

## Estructura del repositorio

La estructura básica de directorios es:

```text
.
├── src/        # Código fuente del servidor HTTP y lógica del portal
├── config/     # Archivos de configuración (firewall, IPs, usuarios, etc.)
├── docs/       # Documentación (topología, diseño, manuales, etc.)
├── scripts/    # Scripts para firewall, arranque/parada del servicio, etc.
├── tests/      # Pruebas y casos de test
└── logs/       # Logs de ejecución (normalmente ignorados por git)

## Servidor HTTP básico (issue #5)

- Ejecución: `PORTAL_HTTP_HOST=0.0.0.0 PORTAL_HTTP_PORT=8080 python3 src/http_server.py`
- El servidor solo usa sockets de la biblioteca estándar y sirve `src/templates/index.html` para peticiones GET.
- Ajusta host/puerto vía variables de entorno `PORTAL_HTTP_HOST` y `PORTAL_HTTP_PORT`.
- Concurrencia: pool de hilos configurable con `PORTAL_HTTP_WORKERS` (por defecto 16).
- Límite de tamaño de petición (cabeceras) con `PORTAL_HTTP_MAX_REQUEST` (por defecto 65536 bytes) para evitar abuso.

## Autenticación y sesiones

- Usuarios de ejemplo en `config/usuarios.txt` (formato `usuario:contraseña`).
- Sesiones en memoria con persistencia a `config/sessions.json`; el módulo `src/sessions.py` restaura sesiones activas al iniciar (descarta las expiradas) y guarda en disco en cada alta/baja/limpieza.
## Scripts de firewall (gateway)

- Ejecutar como root: `sudo bash scripts/firewall_init.sh` (aplica la política base, verifica `nf_conntrack`, habilita forwarding y guarda reglas con `iptables-save` en `/etc/iptables/rules.v4` si está disponible).
- Para depuración: `sudo bash scripts/firewall_clear.sh` (deshabilita forwarding, limpia reglas y deja todo en ACCEPT; también intenta persistir con `iptables-save`).
- Ajusta `WAN_IF` y `LAN_IF` en `scripts/firewall_init.sh` según los nombres de interfaz del gateway.
- Para cargar reglas al arranque instala `iptables-persistent` (Debian/Ubuntu: `sudo apt-get install iptables-persistent`).
