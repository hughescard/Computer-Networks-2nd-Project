# Topología de red de laboratorio

Este documento describe la topología de red utilizada para el desarrollo y las pruebas del **portal cautivo**.

## Visión general

El entorno de laboratorio está montado sobre **VirtualBox** y consta de:

- Una máquina virtual **Portal / Gateway** (`gateway-redes`), que implementará el portal cautivo.
- Una máquina virtual **Cliente** (`cliente1`), que simula un usuario final de la red y podrá alojar contenedores Docker para generar múltiples clientes concurrentes.

Esquema lógico:

```text
[ Contenedores Docker (futuros) en cliente1 ]
                    |
                [ cliente1 ]
                    |
        (red interna 192.168.50.0/24)
                    |
[  Portal / Gateway (gateway-redes) ]
                    |
      (NAT de VirtualBox - "Internet")
                    |
                [ Internet real ]
