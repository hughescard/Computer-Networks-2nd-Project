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

## Redirección automática al portal (detección de portal cautivo)

- El script `scripts/firewall_init.sh` añade una regla en `PREROUTING` (tabla `nat`) para capturar cualquier tráfico HTTP (`--dport 80`) que entre por la interfaz LAN y redirigirlo al puerto donde escucha el portal.
  - Variables configurables:
    - `PORTAL_HTTP_PORT` (puerto real del servidor del portal, por defecto `8080`).
    - `CAPTIVE_HTTP_PORT` (puerto que se captura a los clientes, por defecto `80`).
- Comando aplicado por el script (valores por defecto):

```bash
iptables -t nat -A PREROUTING -i enp0s8 -p tcp --dport 80 -j REDIRECT --to-ports 8080
```

Comportamiento esperado:
- Cliente no autenticado → cualquier sitio HTTP abre el portal cautivo.
- Cliente autenticado → el portal inserta una regla de bypass (ver abajo) y el tráfico HTTP ya no se redirige.
- Para que los clientes resuelvan nombres y lleguen a la redirección es imprescindible permitir DNS (53/udp y 53/tcp) desde la LAN hacia la WAN. El script `scripts/firewall_init.sh` ya añade esas reglas en FORWARD.

## NAT / Enmascaramiento (salida de la LAN)

Para que las peticiones de los clientes (DNS y navegación tras login) salgan correctamente a Internet, el gateway debe enmascararlas. El script `scripts/firewall_init.sh` añade:

```bash
iptables -t nat -A POSTROUTING -o enp0s3 -j MASQUERADE
```

- `enp0s3` es la interfaz WAN por defecto (ajustar si cambia).
- Sin esta regla, los clientes verán errores como “server not found” porque las respuestas nunca regresan a las IPs privadas de la LAN.

## Reglas dinámicas por cliente (login)

Cuando un cliente se autentica exitosamente, el portal crea una sesión y añade una regla dinámica en la cadena FORWARD para permitir el enrutamiento desde la IP del cliente hacia Internet.

Ejemplo de reglas añadidas (orden de inserción):

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

## Prueba rápida de la redirección (Issue #13)

1. En el gateway, aplica el firewall base:

   ```bash
   sudo bash scripts/firewall_init.sh
   ```

2. Arranca el servidor del portal (`PORTAL_HTTP_PORT` debe coincidir con `--to-ports` del paso anterior, por defecto `8080`):

   ```bash
   PORTAL_HTTP_PORT=8080 python3 src/http_server.py
   ```

3. Desde un cliente sin autenticar en la LAN:
   - `curl -i http://example.com` debe devolver la página del portal (HTTP 200 con HTML del login).  
   - `sudo iptables -t nat -L PREROUTING -n --line-numbers | head` debería mostrar la regla `REDIRECT --to-ports 8080`.

4. Tras login correcto (POST /login):
   - El comando `sudo iptables -t nat -L PREROUTING -n --line-numbers` debe mostrar una regla `RETURN` en primera posición para la IP del cliente.
   - El comando `sudo iptables -L FORWARD -n --line-numbers` debe mostrar `ACCEPT` para la IP del cliente.
   - El mismo `curl http://example.com` debe llegar al destino real (no al portal).


NAT / Enmascaramiento (Issue #14)

El portal cautivo actúa como gateway entre la red interna (LAN) y la red externa (WAN).
Los clientes en la LAN usan direcciones privadas (por ejemplo, 192.168.50.x) que no son válidas en Internet.

Para que puedan acceder a DNS y navegación web tras iniciar sesión, el gateway debe realizar NAT (Network Address Translation), concretamente enmascaramiento (MASQUERADE).
Esto hace que:

Las peticiones de cualquier cliente salgan hacia Internet usando la IP pública del gateway.

Las respuestas regresen correctamente al gateway, que luego las reenvía al cliente correspondiente.

¿Por qué es necesario?

Sin NAT, una consulta DNS desde un cliente parecería venir de 192.168.50.x.
Internet no sabe devolver paquetes hacia redes privadas, por lo que:

Las respuestas nunca volverían al cliente.

Los clientes verían errores como “server not found”, “DNS unreachable” o “timeout”.

Implementación en el script

El script scripts/firewall_init.sh configura NAT automáticamente mediante la siguiente regla:

iptables -t nat -A POSTROUTING -o <WAN_IF> -j MASQUERADE


Con los valores por defecto del proyecto:

iptables -t nat -A POSTROUTING -o enp0s3 -j MASQUERADE


Significado:

POSTROUTING → se aplica justo antes de que el paquete salga hacia la WAN.

-o enp0s3 → la interfaz de salida hacia Internet.

MASQUERADE → reemplaza la IP origen por la IP pública del gateway.

Esta regla es suficiente para:

Permitir que DNS funcione correctamente.

Permitir navegación web completa a los clientes después de autenticarse.

Mantener el portal cautivo en funcionamiento, ya que el firewall sigue bloqueando tráfico LAN→WAN por defecto hasta que el portal inserte reglas dinámicas para cada cliente autenticado.

Relación con reglas dinámicas

El NAT está siempre activo, pero no libera la navegación por sí mismo.
La navegación solo se habilita cuando el portal añade:

Una regla de FORWARD para la IP del cliente autenticado.

Una regla de bypass en PREROUTING para evitar la redirección HTTP hacia el portal.

De este modo:

NAT proporciona la traducción de direcciones.

El portal cautivo proporciona el control de acceso.

Cómo verificar que NAT funciona

En el gateway:

sudo iptables -t nat -L POSTROUTING -n -v


Deberías ver una línea similar a:

MASQUERADE  all  --  0.0.0.0/0   0.0.0.0/0   /* salida WAN */  OUT=enp0s3


En un cliente sin autenticar:

nslookup example.com debe resolver correctamente, gracias al NAT para DNS.

En un cliente autenticado:

curl https://example.com debe conectar al destino real.

En sudo iptables -t nat -L PREROUTING -n --line-numbers debe existir un RETURN para su IP.

En sudo iptables -L FORWARD -n --line-numbers debe existir un ACCEPT para su IP.
