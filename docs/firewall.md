# Firewall y IP forwarding

Este documento describe la configuración base del firewall en la máquina **gateway** (`gateway-redes`) para el portal cautivo.

## Objetivos

- Habilitar el **IP forwarding** en el kernel para permitir que el gateway pueda reenviar paquetes.
- Definir una política por defecto que **bloquee el tráfico reenviado** (requisito: no debe haber enrutamiento hasta el inicio de sesión).
- Permitir el acceso HTTP al portal cautivo desde la red interna.
- Dejar preparado el entorno para añadir, en issues posteriores, reglas por cliente y NAT.

## Requisitos previos

- Ejecutar los scripts como **root** (por ejemplo, `sudo bash scripts/firewall_init.sh`).
- El kernel debe exponer el módulo `nf_conntrack` (los scripts verifican que esté disponible antes de usar `--ctstate`).
- Para persistir reglas tras un reinicio se recomienda tener `iptables-save`/`iptables-persistent` instalados.

## IP forwarding y scripts

- **Inicializar firewall base:** habilita IPv4 forwarding, establece DROP por defecto en INPUT/FORWARD, permite tráfico de loopback y tráfico establecido/relacionado, y abre HTTP/SSH/ICMP desde la LAN.

  ```bash
  sudo bash scripts/firewall_init.sh
  ```

- Ajusta las variables `WAN_IF` y `LAN_IF` en el script si cambian los nombres de interfaz.
- Al final ejecuta `iptables-save` (si está disponible) para escribir las reglas en `/etc/iptables/rules.v4`.

- **Limpieza / modo abierto:** deshabilita forwarding, limpia las tablas y deja todas las cadenas en ACCEPT (útil solo para depuración).

  ```bash
  sudo bash scripts/firewall_clear.sh
  ```

  - También intenta persistir el estado resultante con `iptables-save`.

## Persistencia de reglas

En Debian/Ubuntu, instala el paquete `iptables-persistent` para que las reglas guardadas en `/etc/iptables/rules.v4` se apliquen automáticamente al arrancar:

```bash
sudo apt-get update
sudo apt-get install iptables-persistent
```

## Redirección automática al portal y DNS

- El script `scripts/firewall_init.sh` añade una regla en `PREROUTING` (tabla `nat`) que redirige cualquier tráfico HTTP (`--dport 80`) que entra por la LAN al puerto real del portal (`PORTAL_HTTP_PORT`, por defecto 8080).
- También abre DNS (TCP/UDP 53) en FORWARD para que los clientes puedan resolver dominios y alcancen la redirección.
- Ejemplo de regla de redirección (valores por defecto):

```bash
iptables -t nat -A PREROUTING -i enp0s8 -p tcp --dport 80 -j REDIRECT --to-ports 8080
```

Comportamiento esperado:
- Cliente no autenticado → cualquier sitio HTTP abre el portal cautivo.
- Cliente autenticado → el portal inserta una regla de bypass (ver abajo) y el tráfico HTTP ya no se redirige.

## Reglas dinámicas por cliente (login)

Cuando un cliente se autentica exitosamente, el portal crea una sesión y añade reglas dinámicas para permitir el enrutamiento desde la IP del cliente hacia Internet y saltar la redirección HTTP.

Ejemplo de regla añadida:

    # Permitir forwarding para la IP autenticada
    iptables -I FORWARD 1 -s <IP_CLIENTE> -j ACCEPT

    # Evitar que sus peticiones HTTP sigan siendo redirigidas al portal
    iptables -t nat -I PREROUTING 1 -i enp0s8 -s <IP_CLIENTE> -p tcp --dport 80 -j RETURN

- Se inserta en la posición 1 para darle prioridad.
- Al cerrar la sesión (o expirar el TTL) se elimina la regla:

    iptables -D FORWARD -s <IP_CLIENTE> -j ACCEPT
    iptables -t nat -D PREROUTING -i enp0s8 -s <IP_CLIENTE> -p tcp --dport 80 -j RETURN

Notas operativas:
- Requiere que `scripts/firewall_init.sh` configure FORWARD en DROP por defecto.
- El módulo `src/firewall_dynamic.py` es el encargado de añadir/retirar reglas dinámicas (FORWARD + bypass de redirección).
- El endpoint `POST /login` del servidor (`src/http_server.py`) crea la sesión llamando a `sessions.crear_sesion(...)`, lo que dispara las reglas anteriores de forma automática tras autenticación exitosa.
- El proceso que modifica iptables debe ejecutarse con privilegios (root) o a través de un helper confiable.
- Para depuración puedes listar las reglas FORWARD con:
    sudo iptables -L FORWARD -n -v

## Bypass temporal para descargas

Si necesitas dar Internet completo a un cliente puntual (por ejemplo, para instalar paquetes) sin tocar el resto de reglas, usa el helper:

```bash
sudo bash scripts/firewall_bypass.sh enable <IP_CLIENTE>
# cuando ya no se necesite:
sudo bash scripts/firewall_bypass.sh disable <IP_CLIENTE>
```

Esto inserta (o elimina) un `RETURN` en PREROUTING y un `ACCEPT` en FORWARD para la IP indicada, evitando la redirección y permitiendo la navegación.
