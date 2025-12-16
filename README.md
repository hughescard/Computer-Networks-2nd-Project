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

## Extras implementados

- Redirección automática de HTTP (80/tcp) hacia el portal con bypass tras login.
- **NAT/MASQUERADE** en la salida WAN para que los clientes naveguen usando la IP del gateway.
- Portal disponible también por **HTTPS** usando solo la stdlib (`ssl`).
- Reglas dinámicas **IP + MAC** para mitigar suplantación de identidad (cuando la MAC está disponible en ARP).
- Plantillas HTML mejoradas (login, éxito y error) con mensajes claros para el usuario final.
- Sistema de **logs** con trazabilidad de logins, creación/eliminación de sesiones y cambios en el firewall.

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
```

## Servidor HTTP básico (issue #5)

- Ejecución: `PORTAL_HTTP_HOST=0.0.0.0 PORTAL_HTTP_PORT=8080 python3 src/http_server.py`
- El servidor solo usa sockets de la biblioteca estándar y sirve `src/templates/index.html` para peticiones GET.
- Ajusta host/puerto vía variables de entorno `PORTAL_HTTP_HOST` y `PORTAL_HTTP_PORT`.
- Concurrencia: pool de hilos configurable con `PORTAL_HTTP_WORKERS` (por defecto 16).
- Límite de tamaño de petición (cabeceras) con `PORTAL_HTTP_MAX_REQUEST` (por defecto 65536 bytes) para evitar abuso.

## Autenticación y sesiones

- Usuarios de ejemplo en `config/usuarios.txt` (formato `usuario:contraseña`).
- Sesiones en memoria con persistencia a `config/sessions.json`; el módulo `src/sessions.py` restaura sesiones activas al iniciar (descarta las expiradas) y guarda en disco en cada alta/baja/limpieza.
- TTL configurable vía `PORTAL_SESSION_TTL` (por defecto 3600 s; valores ≤ 0 generan sesiones sin expiración).

## Scripts de firewall (gateway)

- Ejecutar como root: `sudo bash scripts/firewall_init.sh` (aplica la política base, verifica `nf_conntrack`, habilita forwarding y guarda reglas con `iptables-save` en `/etc/iptables/rules.v4` si está disponible).
- Para depuración: `sudo bash scripts/firewall_clear.sh` (deshabilita forwarding, limpia reglas y deja todo en ACCEPT; también intenta persistir con `iptables-save`).
- Ajusta `WAN_IF` y `LAN_IF` en `scripts/firewall_init.sh` según los nombres de interfaz del gateway.
- Para cargar reglas al arranque instala `iptables-persistent` (Debian/Ubuntu: `sudo apt-get install iptables-persistent`).

## Despliegue paso a paso (Issue #19)

1) **Prerrequisitos (gateway):** Linux, `python3`, `iptables`, `sudo`, `openssl` (para HTTPS). Ejecuta `./scripts/dev_env.sh` para verificar/habilitar lo básico.
2) **Clona el repositorio** en la máquina gateway y sitúate en la raíz del proyecto.
3) **Configura la red** según `docs/topologia.md`: interfaz LAN con `192.168.50.1/24` (ej. `enp0s8`) y WAN con salida a Internet/DHCP (`enp0s3`).
4) **Alta de usuarios:** edita `config/usuarios.txt` con el formato `usuario:contraseña`.
5) **Aplica el firewall base** (abre el puerto del portal, bloquea forwarding y habilita redirección + NAT):

   ```bash
   sudo PORTAL_HTTP_PORT=8080 PORTAL_LAN_IF=enp0s8 bash scripts/firewall_init.sh
   ```

   - Ajusta `WAN_IF`/`LAN_IF` dentro del script si tus interfaces tienen otros nombres.
   - El script añade `MASQUERADE` en la salida para que DNS/navegación funcionen desde la LAN tras autenticación.

6) **Arranca el portal cautivo** (requiere root para modificar iptables). Variables útiles:

   ```bash
   sudo -E PORTAL_LAN_IF=enp0s8 \
          PORTAL_HTTP_PORT=8080 \
          PORTAL_SESSION_TTL=3600 \
          python3 src/http_server.py
   ```

   - Activa HTTPS exportando además `PORTAL_ENABLE_TLS=1`, `PORTAL_TLS_CERT`, `PORTAL_TLS_KEY` y, si usas un puerto dedicado, `PORTAL_HTTPS_PORT` antes de ejecutar `firewall_init.sh`.

7) **Validación rápida:** desde un cliente en la LAN abre cualquier `http://` → debe aparecer el portal. Inicia sesión con un usuario válido → se carga `login_success.html` y la navegación hacia Internet queda habilitada para esa IP/MAC.
8) **Parada y limpieza:** detén el servidor con `Ctrl+C` y, si deseas, deja el firewall en modo abierto para depuración con `sudo bash scripts/firewall_clear.sh`.

## Arranque rápido (laboratorio)

- En el gateway: `sudo bash scripts/firewall_init.sh`.
- Portal: `sudo -E PORTAL_LAN_IF=enp0s8 PORTAL_HTTP_PORT=8080 python3 src/http_server.py`.
- Cliente LAN (ej. `192.168.50.10/24`, gateway `192.168.50.1`):
  - Antes de login → siempre se muestra el portal al abrir HTTP.
  - Después de login → navegación real habilitada (reglas dinámicas en `iptables`).

## Documentación clave

- `docs/arquitectura.md`: módulos y flujo lógico del portal cautivo.
- `docs/topologia.md`: IPs, máscaras, gateway y rutas del laboratorio.
- `docs/firewall.md`: reglas base, redirección al portal y reglas dinámicas tras login.
- `docs/desarrollo.md`: preparar entorno, ejecutar el servidor (como root) y convención de commits (`scripts/commit.sh`).
- `docs/pruebas_basicas.md`: escenarios ejecutados con múltiples clientes (issue #12).
- `docs/antisuplantacion.md`: enfoque IP+MAC para reducir la suplantación (issue #16).
- `docs/https.md`: generación de certificados y activación de HTTPS con la stdlib (issue #15).
- `docs/checklist_requisitos.md`: checklist final de requisitos y guía de pruebas integrales (issue #20).

## Notas adicionales

- El proyecto usa únicamente la biblioteca estándar de Python.
- Plantillas HTML en `src/templates/` (`login`, `success`, `error`).
- Concurrencia: `ThreadPoolExecutor` en `src/http_server.py` (issue #11).
