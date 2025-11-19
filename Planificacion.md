# Planificación del proyecto – Portal cautivo

Repositorio: `hughescard/Computer-Networks-2nd-Project`  
Integrantes: **@hughescard** y **@D4R102004**

Objetivo: desarrollar en **10 días** un portal cautivo con todos los requisitos y extras, trabajando con issues en GitHub.

---

## Resumen de planificación

- Duración: **10 días**
- Total issues: **21**
- Reparto general:
  - **@hughescard** → estructura del repo, servidor HTTP, sesiones, concurrencia, UX, HTTPS, redirección, entorno de desarrollo, convención de commits, documentación final.
  - **@D4R102004** → arquitectura, firewall, integración login-firewall, NAT, anti-suplantación, pruebas, logs, checklist final.

---

## Día 1 – Base del repositorio, diseño y entorno de desarrollo

### [Issue #1 – Estructurar el repositorio del proyecto](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/1)  
**Asignado a:** @hughescard  

**Descripción:**  
Crear la estructura inicial del repositorio: `src/`, `config/`, `scripts/`, `docs/`, `tests/` (y `logs/` si aplica). Añadir un `README.md` mínimo y `.gitignore`.

**Criterios de aceptación:**
- Estructura de directorios creada y commiteada.
- `README.md` con descripción, integrantes y requisitos generales.
- `.gitignore` básico.

---

### [Issue #2 – Diseño de arquitectura y módulos del sistema](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/2)  
**Asignado a:** @D4R102004  

**Descripción:**  
Definir y documentar en `docs/arquitectura.md` la arquitectura lógica: módulos (HTTP, auth, sesiones, firewall/red, plantillas, logs) y su interacción.

**Criterios de aceptación:**
- Documento `docs/arquitectura.md` creado.
- Descripción de módulos y responsabilidades.
- Diagrama simple de red (cliente ↔ portal ↔ salida).
- Indicar dónde encajan extras (HTTPS, NAT, detección de portal, anti-suplantación).

---

### [Issue #21 – Entorno de desarrollo reproducible y convención de commits](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/21)  
**Asignado a:** @hughescard  

**Descripción:**  
Configurar un entorno de desarrollo reproducible (scripts/archivos de dependencias) y establecer una convención de commits uniforme (por ejemplo, usando Commitizen o herramienta equivalente). Documentar el flujo de trabajo de desarrollo (instalación de dependencias, ejecución del proyecto y cómo realizar commits siguiendo el formato acordado).

**Criterios de aceptación:**
- Existe al menos un archivo o script claro para instalar/activar las dependencias del proyecto (por ejemplo en `scripts/` y/o archivo de dependencias).
- Documento `docs/desarrollo.md` con pasos detallados para preparar el entorno local desde un clon del repo y para ejecutar el sistema en modo desarrollo.
- Herramienta de convención de commits configurada (Commitizen u otra) y documentada (formato esperado de mensajes, comando a usar para commitear).
- Flujo probado: clonar → preparar entorno → ejecutar → hacer al menos un commit usando la convención definida.

---

## Día 2 – Topología de red y firewall base

### [Issue #3 – Montar topología de red de laboratorio](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/3)  
**Asignado a:** @hughescard  

**Descripción:**  
Configurar el entorno de pruebas: portal/gateway con dos interfaces (LAN y salida) y al menos un cliente usando el portal como gateway. Documentar en `docs/topologia.md`.

**Criterios de aceptación:**
- Máquina portal y cliente(s) configurados.
- IPs, máscaras, gateway y rutas documentadas.

---

### [Issue #4 – IP forwarding y firewall base por defecto](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/4)  
**Asignado a:** @hughescard  

**Descripción:**  
Habilitar IP forwarding y crear `scripts/firewall_init.sh` (o similar) para las reglas base: bloqueo de forwarding por defecto y permiso de acceso al puerto HTTP del portal. Documentar en `docs/firewall.md`.

**Criterios de aceptación:**
- IP forwarding activado.
- Script que limpia reglas (si hace falta) y fija políticas por defecto.
- Permiso de acceso al puerto HTTP del portal.
- `docs/firewall.md` actualizado.

---

## Día 3 – Servidor HTTP mínimo y plantillas

### [Issue #5 – Servidor HTTP básico (GET) con librería estándar](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/5)  
**Asignado a:** @hughescard  

**Descripción:**  
Implementar un servidor HTTP mínimo en `src/` usando solo la stdlib: escucha en un puerto, responde a GET con una página HTML simple.

**Criterios de aceptación:**
- Servidor activo en el puerto configurado.
- Respuesta `200 OK` con HTML simple.
- Código organizado (por ejemplo `src/http_server.*`).

---

### [Issue #6 – Plantillas HTML iniciales (login, éxito, error)](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/6)  
**Asignado a:** @D4R102004  

**Descripción:**  
Crear plantillas `login.html`, `login_success.html`, `login_error.html` (por ejemplo en `src/templates/`) e integrarlas mínimamente con el servidor.

**Criterios de aceptación:**
- Plantillas creadas y servidas por el servidor.
- Estilo simple pero legible.

---

## Día 4 – Autenticación de usuarios

### [Issue #7 – Formato de archivo de usuarios y carga en memoria](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/7)  
**Asignado a:** @hughescard  

**Descripción:**  
Definir el formato de `config/usuarios.*` y desarrollar funciones para cargar usuarios/contraseñas en memoria.

**Criterios de aceptación:**
- Archivo de ejemplo en `config/`.
- Función de carga que devuelve estructura de usuarios.
- Manejo de errores de archivo/formato.

---

### [Issue #8 – Endpoint de login (POST) integrado con autenticación](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/8)  
**Asignado a:** @D4R102004  

**Descripción:**  
Extender el servidor HTTP con un endpoint `/login` (o similar) que maneje GET (formulario) y POST (credenciales), valide contra el módulo de auth y muestre éxito/error.

**Criterios de aceptación:**
- GET `/login` → formulario.
- POST `/login` → valida credenciales.
- Credenciales correctas → `login_success.html`.
- Incorrectas → `login_error.html`.

---

## Día 5 – Sesiones y firewall por cliente

### [Issue #9 – Módulo de gestión de sesiones en memoria](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/9)  
**Asignado a:** @hughescard  

**Descripción:**  
Crear un módulo que mantenga sesiones activas asociadas al menos a IP y usuario (y opcionalmente MAC), con funciones de crear/obtener/eliminar sesión.

**Criterios de aceptación:**
- Mapa `(IP[, MAC]) → datos_sesion`.
- Funciones `crear_sesion`, `obtener_sesion`, `eliminar_sesion`.
- Almacenar usuario y hora de login (y posible expiración).

---

### [Issue #10 – Integración login ↔ firewall (permitir salida tras autenticación)](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/10)  
**Asignado a:** @D4R102004  

**Descripción:**  
Cuando el login es exitoso, crear sesión y añadir reglas al firewall para permitir el tráfico de esa IP (y opcionalmente MAC) hacia la red externa.

**Criterios de aceptación:**
- Antes de login → cliente sin Internet.
- Después de login éxito → cliente con Internet.
- Reglas por cliente documentadas en `docs/firewall.md`.

---

## Día 6 – Concurrencia y pruebas básicas

### [Issue #11 – Concurrencia en el servidor HTTP (hilos/procesos)](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/11)  
**Asignado a:** @hughescard  

**Descripción:**  
Modificar el servidor para soportar múltiples conexiones simultáneas usando hilos, procesos o mecanismo concurrente equivalente.

**Criterios de aceptación:**
- Varias peticiones concurrentes sin bloqueo.
- Sesiones correctas bajo concurrencia.

---

### [Issue #12 – Pruebas funcionales con múltiples clientes](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/12)  
**Asignado a:** @D4R102004  

**Descripción:**  
Diseñar y ejecutar pruebas con 2+ clientes simultáneos (login y navegación). Documentar en `docs/pruebas_basicas.md`.

**Criterios de aceptación:**
- Escenarios probados documentados.
- Comportamiento esperado vs observado.
- Bugs registrados como issues adicionales si aparecen.

---

## Día 7 – Extras de red: redirección y NAT

### [Issue #13 – Redirección automática de HTTP al portal (detección portal cautivo)](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/13)  
**Asignado a:** @hughescard  

**Descripción:**  
Configurar firewall/servidor para que todo HTTP (puerto 80) de clientes no autenticados se redirija al portal, de modo que cualquier web abra el login.

**Criterios de aceptación:**
- Cliente no autenticado → siempre ve portal al abrir HTTP.
- Cliente autenticado → navega a destino real.
- Configuración documentada en `docs/firewall.md`.

---

### [Issue #14 – Configurar NAT/enmascaramiento IP para la red interna](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/14)  
**Asignado a:** @D4R102004  

**Descripción:**  
Implementar NAT/enmascaramiento en el portal para que los clientes salgan usando la IP del portal. Integrarlo en el script de firewall.

**Criterios de aceptación:**
- Tráfico de clientes sale con IP del portal.
- Script de firewall aplica NAT automáticamente.
- NAT documentado en `docs/firewall.md`.

---

## Día 8 – Extras: HTTPS y anti-suplantación

### [Issue #15 – Soporte HTTPS para el portal (TLS con stdlib)](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/15)  
**Asignado a:** @hughescard  

**Descripción:**  
Añadir soporte HTTPS al portal usando solo la stdlib: configurar certificado (autofirmado o válido) y servir login también por HTTPS.

**Criterios de aceptación:**
- Portal accesible por `https://`.
- Certificado documentado y cómo confiar en él.
- Login funcionando sobre HTTPS.

---

### [Issue #16 – Control de suplantación de IP (IP + MAC / ARP)](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/16)  
**Asignado a:** @D4R102004  

**Descripción:**  
Implementar mecanismo básico anti-suplantación: sesiones asociadas a IP + MAC (si es posible), reglas de firewall que consideren ambas y documentación de limitaciones.

**Criterios de aceptación:**
- Sesiones con MAC incluida (cuando se pueda obtener).
- Firewall usando IP + MAC o alternativa documentada.
- Documento `docs/antisuplantacion.md` creado.

---

## Día 9 – UX y logging

### [Issue #17 – Mejora de la interfaz web y experiencia de usuario](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/17)  
**Asignado a:** @hughescard  

**Descripción:**  
Mejorar las páginas HTML con CSS básico, mensajes claros e instrucciones de uso (qué ocurre tras login, cómo cerrar sesión si existe, etc.).

**Criterios de aceptación:**
- Páginas de login, éxito y error con diseño coherente.
- Mensajes claros de error/información para el usuario.

---

### [Issue #18 – Sistema de logs y registro de eventos importantes](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/18)  
**Asignado a:** @D4R102004  

**Descripción:**  
Registrar eventos importantes (logins correctos/fallidos, creación/eliminación de sesiones, cambios de reglas de firewall) en archivos de log (por ejemplo en `logs/`).

**Criterios de aceptación:**
- Directorio `logs/` creado.
- Archivo de log con timestamp, IP, usuario (si aplica) y evento.
- `docs/logs.md` explicando formato y ubicación.

---

## Día 10 – Documentación final y pruebas integrales

### [Issue #19 – Documentación final de despliegue y uso](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/19)  
**Asignado a:** @hughescard  

**Descripción:**  
Completar documentación para desplegar el portal desde cero: prerequisitos, instalación, configuración de red, alta de usuarios, arranque/parada del sistema.

**Criterios de aceptación:**
- `README.md` actualizado con:
  - Descripción completa del proyecto.
  - Pasos de instalación y configuración.
  - Instrucciones de uso.
  - Lista de extras implementados.
- Referencias claras a documentos en `docs/`.

---

### [Issue #20 – Pruebas integrales y checklist de requisitos](https://github.com/hughescard/Computer-Networks-2nd-Project/issues/20)  
**Asignado a:** @D4R102004  

**Descripción:**  
Realizar pruebas integrales del sistema completo y crear un checklist que relacione cada requisito del enunciado con su implementación.

**Criterios de aceptación:**
- `docs/checklist_requisitos.md` con:
  - Lista de requisitos del proyecto.
  - Cómo se cumple cada uno (archivo/módulo/regla).
  - Estado probado/no probado.
- Pruebas finales:
  - Sin login → sin navegación.
  - Con login → navegación OK.
  - Redirección automática → OK.
  - NAT → OK.
  - HTTPS → OK.
  - Anti-suplantación → verificada en lo posible.
- Bugs críticos abiertos como nuevas issues.

---

## Cómo usar esta planificación

- Cada issue corresponde a un bloque de trabajo dentro de los 10 días.
- Esta página sirve como visión general del plan y como índice de las issues.
- Se puede ir marcando el progreso en la wiki y usando los enlaces directos a cada issue en GitHub.
