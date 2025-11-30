# Topología de red de laboratorio

Este documento describe la topología de red utilizada para el desarrollo y las pruebas del **portal cautivo**.

## Visión general

El entorno de laboratorio está montado sobre **VirtualBox** y consta de:

- Una máquina virtual **Portal / Gateway** (`gateway-redes`), que implementa el portal cautivo.
- Una máquina virtual **Cliente** (`cliente1`), que simula a los usuarios de la red interna y puede alojar contenedores Docker para más clientes concurrentes.

Esquema lógico:

```text
[ cliente1 (192.168.50.10/24) ] --[enp0s8]--> [ Portal/Gateway (192.168.50.1/24) ] --[enp0s3]--> [ NAT VirtualBox / Internet ]
                        red interna 192.168.50.0/24                           salida WAN (DHCP/NAT)
```

## Direccionamiento usado en laboratorio

| Nodo                  | Interfaz    | IP / Máscara        | Gateway por defecto | DNS recomendado                    |
| --------------------- | ----------- | ------------------- | ------------------- | ---------------------------------- |
| Portal (`gateway-redes`) | enp0s8 (LAN) | `192.168.50.1/24`   | — (no aplica)       | —                                  |
| Portal (`gateway-redes`) | enp0s3 (WAN) | Asignada por NAT de VirtualBox (DHCP) | La que entregue el NAT | La que entregue el NAT             |
| Cliente (`cliente1`)     | enp0s3/eth0  | `192.168.50.10/24`  | `192.168.50.1`      | `8.8.8.8` o el DNS aguas arriba    |

> Para más clientes usa IPs libres en `192.168.50.0/24` (ej. `192.168.50.11`, `192.168.50.12`, etc.), siempre con gateway `192.168.50.1`.

## Configuración paso a paso

1. **Portal / Gateway**

   ```bash
   # Interfaz LAN (hacia clientes)
   sudo ip addr flush dev enp0s8
   sudo ip addr add 192.168.50.1/24 dev enp0s8
   sudo ip link set enp0s8 up

   # Interfaz WAN (NAT de VirtualBox normalmente via DHCP)
   sudo dhclient enp0s3
   ```

2. **Cliente (`cliente1`)**

   ```bash
   sudo ip addr flush dev enp0s3        # o el nombre de la interfaz del cliente
   sudo ip addr add 192.168.50.10/24 dev enp0s3
   sudo ip link set enp0s3 up
   sudo ip route add default via 192.168.50.1
   echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
   ```

3. **Rutas**

   - Los clientes envían todo el tráfico a su **gateway** `192.168.50.1`.
   - El gateway reenvía hacia `enp0s3` (WAN) cuando el firewall lo permite.

## Comprobaciones rápidas

- Ver IPs en el portal:

  ```bash
  ip -br a show enp0s8 enp0s3
  ```

- Hacer ping desde cliente al gateway y viceversa:

  ```bash
  ping -c3 192.168.50.1        # desde cliente
  ping -c3 192.168.50.10       # desde gateway
  ```

- Confirmar ruta por defecto en el cliente:

  ```bash
  ip route
  ```

- Probar redirección del portal (issue #13):
  1. En el gateway: `sudo bash scripts/firewall_init.sh`.
  2. En el cliente (sin autenticación): `curl -i http://example.com` debe mostrar la página del portal (HTTP 200 y HTML del login).

Si algo falla, revisa `docs/firewall.md` y valida que el firewall esté aplicado y que el cliente use el gateway correcto.
