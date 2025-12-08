# Auditoría del Portal Cautivo: Logs del Sistema

Este documento describe la ubicación, formato y los eventos clave registrados por el servidor del portal cautivo (`http_server.py`).

## Ubicación del Archivo de Log

Todos los eventos de registro se guardan en el archivo:
`logs/portal_captivo.log`

## Formato del Registro

El formato de cada línea de log está estandarizado y contiene la siguiente información:

`[AAAA-MM-DD HH:MM:SS,ms] [NIVEL] MENSAJE`

* **`AAAA-MM-DD HH:MM:SS,ms`**: Marca de tiempo exacta del evento.
* **`NIVEL`**: Nivel de severidad (INFO, WARNING, ERROR).
* **`MENSAJE`**: Contenido detallado del evento, incluyendo IP y usuario cuando sea aplicable.

## Eventos Clave Registrados

Se registran los siguientes eventos para auditoría y depuración:

| Nivel | Evento | Ejemplo de Mensaje | Propósito |
| :--- | :--- | :--- | :--- |
| `INFO` | **Inicio de Servidor** | `Servidor HTTP escuchando en 0.0.0.0:8080` | Verificar la inicialización del servicio. |
| `INFO` | **Login Exitoso** | `Login exitoso para 'admin' desde 192.168.1.100` | Trazabilidad del acceso de usuarios. |
| `WARNING` | **Login Fallido** | `Login FALLIDO para 'guest' desde 192.168.1.101` | Detección de intentos de acceso no autorizados. |
| `INFO` | **Sesión Creada** | `Creada/actualizada sesión para ('192.168.1.100', 'aabbccddeeff') (usuario=admin, ttl=3600)` | Confirmación de la sesión activa. |
| `INFO` | **Regla de Firewall Añadida** | `Regla de firewall añadida para permitir navegación a 192.168.1.100 (MAC aabbccddeeff)` | Auditoría de los cambios en la seguridad de red. |
| `INFO` | **Sesión Expirada** | `Sesión expirada para ('192.168.1.100', 'aabbccddeeff'); eliminando` | Monitoreo del ciclo de vida de las sesiones. |
| `INFO` | **Regla de Firewall Eliminada** | `Regla de firewall eliminada (sesión expirada) para 192.168.1.100` | Auditoría de la limpieza del firewall. |

## Cómo Revisar los Logs

Para ver los logs en tiempo real (útil para depuración):

```bash
tail -f logs/portal_captivo.log