# Directorio `src/`

En este directorio va **todo el código fuente** del portal cautivo.

## Contenido típico

- Módulos del servidor HTTP (manejo de sockets, parsing de peticiones, respuestas).
- Módulo de autenticación (validación de usuarios/contraseñas).
- Módulo de sesiones en memoria.
- Módulo de integración con el firewall (llamadas al CLI del sistema).
- Plantillas HTML (si se ubican dentro de `src/templates/`).
- Utilidades comunes (funciones auxiliares, helpers, etc.).

## Convenciones

- Solo se usan bibliotecas de la **biblioteca estándar** del lenguaje que elijamos para el proyecto.
- Mantener el código organizado por responsabilidad (por ejemplo: `http_*.c`, `auth_*.c`, `sessions_*.c` o nombres equivalentes).
- Evitar mezclar código fuente con archivos de configuración o datos; eso va en `config/`.
