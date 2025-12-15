# Soporte HTTPS para el portal (Issue #15)

El portal cautivo puede servir la misma UI sobre **HTTPS** usando únicamente la
biblioteca estándar (`ssl`). Esta guía explica cómo generar un certificado,
habilitar TLS en `src/http_server.py` y ajustar el firewall.

---

## 1. Generar un certificado autofirmado para el laboratorio

> Requisitos: `openssl`

```bash
mkdir -p config/tls
openssl req \
  -x509 -newkey rsa:4096 -sha256 -days 365 \
  -nodes \
  -keyout config/tls/portal.key \
  -out   config/tls/portal.crt \
  -subj "/CN=portal.local"
```

- Guarda los archivos en `config/tls/portal.crt` y `config/tls/portal.key`.
- Importa el certificado (`portal.crt`) en el navegador/cliente para evitar
  advertencias (al ser autofirmado).

## 2. Variables de entorno para habilitar TLS

El servidor sigue escuchando en un único socket; puedes elegir el puerto que
prefieras (ej. 8443 para laboratorio o 443 si interceptas HTTPS).

```bash
sudo -E \
  PORTAL_ENABLE_TLS=1 \
  PORTAL_TLS_CERT="$PWD/config/tls/portal.crt" \
  PORTAL_TLS_KEY="$PWD/config/tls/portal.key" \
  PORTAL_HTTP_PORT=8443 \
  PORTAL_LAN_IF=enp0s8 \
  python3 src/http_server.py
```

Variables relevantes:

| Variable              | Descripción                                                                 |
| --------------------- | --------------------------------------------------------------------------- |
| `PORTAL_ENABLE_TLS`   | Activa el modo HTTPS (`1`, `true`, `yes`, `on`).                            |
| `PORTAL_TLS_CERT`     | Ruta absoluta/relativa al certificado en formato PEM.                       |
| `PORTAL_TLS_KEY`      | Ruta a la clave privada PEM asociada al certificado.                        |
| `PORTAL_HTTP_PORT`    | Puerto donde escucha el portal (puede ser 8443).                            |
| `PORTAL_TLS_CIPHERS`  | (Opcional) Cadena OpenSSL con la lista de cifrados permitidos.              |
| `PORTAL_LAN_IF`       | Interfaz LAN usada por `firewall_dynamic.py` para las reglas por cliente.   |

> Nota: el servidor sigue funcionando sin TLS si `PORTAL_ENABLE_TLS` no está
> activo; simplemente sirve tráfico HTTP como antes.

## 3. Firewall y puertos

- `scripts/firewall_init.sh` abre siempre el puerto HTTP definido en
  `PORTAL_HTTP_PORT`.
- Para permitir también el puerto TLS, exporta `PORTAL_HTTPS_PORT` antes de
  ejecutar el script:

  ```bash
  sudo PORTAL_HTTPS_PORT=8443 bash scripts/firewall_init.sh
  ```

- Si quieres redirigir el tráfico `HTTPS (443)` hacia el portal (similar a
  Issue #13 para HTTP), deberás añadir reglas específicas en la tabla `nat`.
  Esa parte es opcional y dependerá del escenario donde despliegues el portal.

## 4. Validación rápida

1. Aplica el firewall base (dejando abierto el puerto HTTPS configurado).
2. Arranca el servidor con TLS (comando anterior).
3. Desde un cliente dentro de la LAN, ejecuta:

   ```bash
   curl -k https://portal.local:8443/
   ```

   Debe devolver la página de login. Usa `-k` sólo si el certificado no está en
   el store del sistema.

4. Repite el flujo de login. Tras autenticación, las reglas de `iptables` deben
   mostrarse como siempre (`FORWARD` + `PREROUTING`). TLS no cambia la lógica de
   sesiones, solo cifra el transporte.
