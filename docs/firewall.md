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
