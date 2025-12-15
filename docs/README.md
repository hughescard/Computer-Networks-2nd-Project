# 🔒 Portal Cautivo: Servidor de Control de Acceso (Redes 2025)

## 🌟 1. Descripción del Proyecto

Este proyecto implementa un Portal Cautivo (Captive Portal) utilizando únicamente la biblioteca estándar de Python, cumpliendo el rol de un Network Access Control (NAC) a nivel de red. El sistema fuerza a los clientes a autenticarse mediante un formulario web antes de que puedan tener acceso al exterior.

### ✔️ Características implementadas

- Servidor HTTP/HTTPS concurrente basado en sockets + `ssl`.
- Módulo de autenticación basado en archivo (`config/usuarios.txt`).
- Gestión de sesiones con persistencia en `sessions.json`.
- Firewall dinámico con `iptables` para autorizar IP/MAC tras login.
- Sistema de logging completo para auditoría de eventos de seguridad.

## ⚙️ 2. Despliegue y Configuración Inicial

### 2.1 Prerrequisitos de software

- Sistema operativo: Linux (Debian/Ubuntu recomendado).
- Python: versión 3.8 o superior.
- Herramientas del sistema: `sudo`, `iptables` (o `nftables`), `openssl`.

### 2.2 Preparación del entorno

Ejecuta el script de configuración inicial para instalar dependencias y crear directorios esenciales:

```bash
./scripts/dev_env.sh
```

### 2.3 Configuración de usuarios

Añade los usuarios en `config/usuarios.txt`. Usa el formato:

```
usuario:contraseña
```

#### Ejemplo:

```
alumno1:redes2025
prueba:1234
```

### 2.4 Inicialización del firewall (Bloqueo y redirección)

Configura la interfaz LAN que usarán los clientes (ej. `enp0s8`) y el puerto interno del portal cautivo.

#### Ejemplo:

```bash
sudo PORTAL_LAN_IF=enp0s8 PORTAL_HTTP_PORT=8080 ./scripts/firewall_init.sh
```

> Nota: El script añade reglas en PREROUTING/NAT para redirigir todo el tráfico HTTP (puerto 80) desde `PORTAL_LAN_IF` hacia el servidor local en `PORTAL_HTTP_PORT`.

## 🚀 3. Uso y Operación

### 3.1 Arrancar el servidor (HTTP)

Una vez activado el firewall:

```bash
python3 src/http_server.py
```

### 3.2 Arrancar con HTTPS

Para habilitar HTTPS (ver `docs/https.md` para la generación de certificados):

```bash
sudo PORTAL_HTTP_PORT=443 \
     PORTAL_ENABLE_TLS=1 \
     PORTAL_TLS_CERT=config/tls/portal.crt \
     PORTAL_TLS_KEY=config/tls/portal.key \
     python3 src/http_server.py
```

### 3.3 Detener y limpiar

Detén el servidor con `Ctrl + C`.

Limpia las reglas de firewall:

```bash
sudo ./scripts/firewall_clear.sh
```

## 📚 4. Documentación y Arquitectura

Para comprender en profundidad el funcionamiento del portal cautivo, revisa los siguientes documentos:

| Documento                             | Contenido                                                        |
|---------------------------------------|------------------------------------------------------------------|
| `docs/arquitectura.md`               | Diseño modular: Auth, Sessions, Server.                          |
| `docs/topologia.md`                  | Diagrama y requerimientos de topología de red.                  |
| `docs/firewall.md`                   | Explicación detallada de las reglas de `iptables` usadas.       |
| `docs/https.md`                      | Generación de certificados y habilitación de TLS.                |
| `docs/antisuplantacion.md`           | Medidas anti-suplantación y uso de ARP lookup.                  |
