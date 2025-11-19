# Directorio `config/`

En este directorio se guardan **archivos de configuración** del portal cautivo.

## Contenido esperado

- Archivos de usuarios, por ejemplo:
  - `usuarios.txt`, `usuarios.csv` o similar.
- Archivos de configuración de red o del portal, por ejemplo:
  - IPs/puertos de escucha.
  - Parámetros de sesión (tiempos de expiración, etc.).
- Variables de entorno o plantillas de configuración:
  - Por ejemplo `config.example.env` o similar (sin credenciales reales).

## Convenciones

- No guardar aquí contraseñas reales en texto plano que no deban estar en el repositorio.
- Mantener un archivo de ejemplo que sirva de referencia para configurar el sistema.
- Cualquier cambio de formato debe documentarse también en `docs/` (por ejemplo en `docs/desarrollo.md` o documento de usuarios).
