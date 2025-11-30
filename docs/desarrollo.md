# Guía de desarrollo – Portal cautivo

Este documento explica cómo preparar un entorno de desarrollo **reproducible** a partir de un clon del repositorio, cómo levantar el sistema en modo desarrollo y cómo trabajar con ramas, commits y Pull Requests siguiendo la convención acordada.

Repositorio: `hughescard/Computer-Networks-2nd-Project`  
Integrantes: **@hughescard** y **@D4R102004**

---

## 1. Objetivo del entorno de desarrollo

El objetivo de este documento es que cualquier integrante del equipo sepa:

- Qué herramientas necesita tener instaladas.
- Qué scripts del repositorio debe usar para preparar su entorno.
- Cómo organizar el trabajo en ramas por issue.
- Cómo escribir mensajes de commit y crear Pull Requests de forma consistente.

Al final del documento hay un **checklist** (sección 10) que se puede usar para validar la Issue #21.

---

## 2. Requisitos previos

En la máquina donde se va a desarrollar se asume:

- Sistema operativo: GNU/Linux (probado en Ubuntu Server).
- Herramientas básicas instaladas:
  - `git`
  - `bash`
  - `python3`
  - `python3-venv` y `pip` (para gestionar el entorno virtual)
  - `iptables`, `ip`, `ss`/`netstat` u otras herramientas de red
- Acceso a `sudo` (recomendado) para configurar firewall y red en el entorno de laboratorio.

Para detalles de diseño y red, ver:

- `docs/arquitectura.md` – arquitectura lógica (módulos del portal).
- `docs/topologia.md` – topología de red del laboratorio.
- `docs/firewall.md` – reglas de firewall, NAT, anti-suplantación, etc.

---

## 3. Flujo rápido (TL;DR)

1. Clonar el repositorio y crear una rama para la issue.
2. Ejecutar el script de entorno de desarrollo.
3. Configurar entorno de laboratorio (IP forwarding + firewall base).
4. Levantar el servidor del portal cautivo (`src/http_server.py`).
5. Hacer cambios en código / docs.
6. Confirmar cambios con el script de commits.
7. Abrir un Pull Request hacia `main` mencionando la issue.

Las secciones siguientes explican cada paso en detalle.

---

## 4. Clonar el repositorio y crear rama por issue

Ejemplo de flujo inicial:

    # 1. Clonar el repositorio
    git clone git@github.com:hughescard/Computer-Networks-2nd-Project.git

    # 2. Entrar al directorio
    cd Computer-Networks-2nd-Project

    # 3. Actualizar rama main
    git checkout main
    git pull origin main

### 4.1. Flujo de ramas

Para mantener el proyecto ordenado, se usa un flujo basado en **ramas por issue** y **Pull Requests**.

- `main`: rama principal, estable, con trabajo ya revisado.
- Ramas de feature/fix por issue, por ejemplo:
  - `feature/issue-1-estructura-repo`
  - `feature/issue-3-topologia-lab`
  - `feature/issue-4-firewall-base`
  - `feature/issue-21-dev-env-y-commits`

**Convención recomendada para nombres de rama:**

- `feature/issue-XX-descripcion-corta`
- `fix/issue-XX-descripcion-corta`
- `docs/issue-XX-descripcion-corta`

Ejemplo para la issue 21:

    git checkout -b feature/issue-21-dev-env-y-commits

Toda la implementación de una issue se hace en su rama y luego termina en un PR contra `main`.

---

## 5. Preparar el entorno de desarrollo (script `scripts/dev_env.sh`)

Desde la raíz del repositorio:

    ./scripts/dev_env.sh

Este script se encarga de:

- Comprobar la existencia de herramientas básicas (`git`, utilidades de red, etc.).
- En sistemas basados en `apt` (Ubuntu/Debian), ofrecer instalar paquetes mínimos recomendados (por ejemplo `python3`, `python3-venv`, herramientas de red, etc.).
- Preparar un entorno virtual de Python (`.venv`) o, al menos, comprobar que `python3` y `pip` están disponibles, ya que el proyecto se implementa en **Python**.

> Nota: si ya tienes Python y las dependencias instaladas como tú quieras, puedes responder **No** a las preguntas de instalación y usar el script solo como **checklist automático**.

Este script cumple con el requisito de tener al menos un **archivo o script claro** para instalar/activar las dependencias del proyecto en `scripts/`.

---

## 6. Entorno de laboratorio

El portal cautivo se prueba en un entorno de laboratorio con:

- Una máquina **portal/gateway** (donde corre el servidor del portal en Python).
- Una o varias máquinas **cliente** que usan el portal como gateway para salir a la red externa.

La configuración completa (IPs, máscaras, gateways y rutas) está documentada en `docs/topologia.md`. Aquí se resume lo necesario para el **desarrollo**:

### 6.1. Topología básica

- Interfaz LAN del portal → conectada a la red interna de clientes.
- Interfaz WAN del portal → conectada a la salida (por ejemplo, NAT de VirtualBox o una red externa).
- Los clientes deben tener como **gateway por defecto** la IP de la interfaz LAN del portal.

Antes de probar el portal en condiciones reales, la máquina portal debe tener:

1. **IP forwarding habilitado**.
2. **Firewall base** aplicado.

### 6.2. IP forwarding y firewall base

Ejemplo de configuración mínima desde la máquina portal (ajustar al nombre real de los scripts):

    # Habilitar IP forwarding temporalmente
    sudo sysctl -w net.ipv4.ip_forward=1

    # Aplicar el firewall base del proyecto
    sudo ./scripts/firewall_init.sh

El script de firewall debería:

- Limpiar reglas previas si es necesario.
- Bloquear el forwarding por defecto para clientes no autenticados.
- Permitir el acceso al puerto HTTP/HTTPS del portal.
- Aplicar NAT/enmascaramiento según el diseño del proyecto.

Los detalles completos de las reglas están en `docs/firewall.md`. Este documento solo resume lo necesario para que un desarrollador pueda reproducir el **escenario de pruebas**.

---

## 7. Ejecutar el servidor del portal cautivo (Python)

El servidor del portal está implementado en **Python** en `src/http_server.py` y solo usa la stdlib (sockets + ThreadPoolExecutor).

1. (Opcional) Activar el entorno virtual creado por `dev_env.sh`:

       source .venv/bin/activate

2. (Gateway) Asegúrate de que el firewall base está aplicado:

       sudo bash scripts/firewall_init.sh   # requiere root

3. Arranca el servidor:

       PORTAL_HTTP_PORT=8080 PORTAL_HTTP_WORKERS=16 python3 src/http_server.py

   Variables útiles:
   - `PORTAL_HTTP_HOST` (por defecto `0.0.0.0`)
   - `PORTAL_HTTP_PORT` (por defecto `8080`; el firewall redirige HTTP 80 hacia este puerto)
   - `PORTAL_HTTP_MAX_REQUEST` (límite de bytes a leer por petición)
   - `PORTAL_SESSION_TTL` (segundos de vigencia de cada sesión)

4. Desde un cliente de la LAN, abre cualquier URL `http://` y deberías ser redirigido al portal (issue #13). Tras login exitoso, el módulo `sessions` crea la sesión y `firewall_dynamic.py` inserta reglas para permitir la navegación real.

---

## 8. Convención de mensajes de commit

Se usa la siguiente convención para los mensajes de commit:

    <tipo>: <resumen breve> (#<numero_issue>)

Donde `<tipo>` puede ser:

- `feat` → nueva funcionalidad
- `fix` → corrección de error
- `docs` → documentación
- `chore` → tareas de mantenimiento/refactor
- `test` → pruebas

Ejemplos:

- `feat: ip forwarding y firewall base (#4)`
- `docs: definir topología de red de laboratorio (#3)`
- `chore: entorno de desarrollo y convención de commits (#21)`

---

## 9. Uso del script `scripts/commit.sh`

Para facilitar la convención de commits, se usa el script `scripts/commit.sh`.

Flujo típico:

    # Ver cambios
    git status

    # Añadir archivos
    git add <archivos>    # o git add .

    # Ejecutar el asistente de commit
    ./scripts/commit.sh

El script:

1. Muestra los tipos disponibles (`feat`, `fix`, `docs`, `chore`, `test`).
2. Pide:
   - Tipo de commit.
   - Resumen breve (en imperativo, sin punto final).
   - Número de issue (solo el número, por ejemplo `21`).
3. Genera un mensaje con el formato:

       <tipo>: <resumen breve> (#<numero_issue>)

   Por ejemplo:

       chore: entorno de desarrollo y convención de commits (#21)

4. Muestra el mensaje final y pregunta confirmación antes de ejecutar `git commit -m "<mensaje>"`.

Este script implementa la **herramienta de convención de commits** requerida por la Issue #21.

---

## 10. Checklist rápido (Issue #21)

- [ ] Clonaste el repo y creaste una rama por issue (`git checkout -b feature/issue-XX-...`).
- [ ] Ejecutaste `./scripts/dev_env.sh` y tienes `python3` + herramientas de red disponibles.
- [ ] Configuraste la topología del laboratorio (`docs/topologia.md`) y aplicaste `scripts/firewall_init.sh`.
- [ ] Arrancaste el servidor del portal con `python3 src/http_server.py` y confirmaste que responde en el puerto configurado.
- [ ] Probaste la redirección HTTP y el login básico (issue #13 + #8).
- [ ] Usaste `./scripts/commit.sh` para generar el mensaje de commit siguiendo la convención.
