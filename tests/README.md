# Directorio `tests/`

En este directorio se colocan **pruebas** del sistema.

## Contenido esperado

- Scripts o programas para pruebas automáticas del servidor HTTP.
- Casos de pruebas funcionales (por ejemplo, varios clientes haciendo login y navegando).
- Archivos de datos para pruebas, si hacen falta.

Aunque parte de la documentación de pruebas quede en `docs/` (por ejemplo `docs/pruebas_basicas.md`), aquí se guardan los archivos que se ejecutan directamente.

## Convenciones

- Nombrar las pruebas de forma descriptiva (por ejemplo `test_login_basico.sh`, `test_concurrencia.py`, etc.).
- Indicar en los propios scripts cómo se ejecutan y qué se espera que pase.
- En la documentación de pruebas se debería indicar qué pruebas viven en este directorio y cómo lanzarlas.
