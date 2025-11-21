# Firewall y IP forwarding

Este documento describe la configuración base del firewall en la máquina **gateway** (`gateway-redes`) para el portal cautivo.

## Objetivos

- Habilitar el **IP forwarding** en el kernel para permitir que el gateway pueda reenviar paquetes.
- Definir una política por defecto que **bloquee el tráfico reenviado** (requisito: no debe haber enrutamiento hasta el inicio de sesión).
- Permitir el acceso HTTP al portal cautivo desde la red interna.
- Dejar preparado el entorno para añadir, en issues posteriores, reglas por cliente y NAT.

## IP forwarding

Se habilita IPv4 forwarding:

```bash
sudo sysctl -w net.ipv4.ip_forward=1
