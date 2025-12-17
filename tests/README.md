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

## Scripts actuales

- `pruebas_basicas.sh`: prueba automatizada para el Issue #12. Ejecutar desde un cliente de la LAN:

  ```bash
  PORTAL_HOST=192.168.50.1 PORTAL_PORT=8080 \
  TARGET_URL=http://example.com \
  PORTAL_USER=admin PORTAL_PASS=admin \
  bash tests/pruebas_basicas.sh
  ```

  Ver `docs/pruebas_basicas.md` para el contexto y los escenarios completos.

- `pruebas_contenedores.sh`: ejecuta `pruebas_basicas.sh` dentro de varios contenedores Docker con IPs distintas (macvlan) para probar concurrencia desde un único host cliente.

  ```bash
  LAN_IF=enp0s3 CLIENT_IPS="192.168.50.101 192.168.50.102 192.168.50.103" \
  PORTAL_HOST=192.168.50.1 PORTAL_PORT=8080 \
  bash tests/pruebas_contenedores.sh
  ```

  Requiere Docker y permisos para crear redes macvlan en el cliente.

- `prueba_r12_antisuplantacion.sh`: prueba automatizada del requisito R12 (anti-suplantación IP+MAC) usando Docker/macvlan desde la VM cliente.

  ```bash
  LAN_IF=enp0s3 CLIENT_IP=192.168.50.101 \
  PORTAL_HOST=192.168.50.1 PORTAL_PORT=8080 \
  bash tests/prueba_r12_antisuplantacion.sh
  ```

  Si falla en `[1/3]` y no se ve el motivo, ejecutar con `DEBUG=1` para dejar contenedores y ver mensajes de error:

  ```bash
  DEBUG=1 LAN_IF=enp0s3 CLIENT_IP=192.168.50.101 \
  PORTAL_HOST=192.168.50.1 PORTAL_PORT=8080 \
  bash tests/prueba_r12_antisuplantacion.sh
  ```
