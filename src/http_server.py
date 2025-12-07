#!/usr/bin/env python3
"""
Servidor HTTP del portal cautivo.

- Sirve múltiples plantillas HTML desde src/templates/ según la ruta solicitada.
- GET /          → index.html
- GET /login     → login.html (formulario de autenticación)
- POST /login    → procesa credenciales enviadas por formulario
- Autenticación correcta   → login_success.html
- Autenticación incorrecta → login_error.html
- Manejo básico de errores: 400, 404, 405 y 500.
"""


import logging
import os
import socket
from concurrent.futures import ThreadPoolExecutor
import threading
from pathlib import Path
from typing import Optional, Tuple
import ssl

from urllib.parse import parse_qs
from auth import load_users, authenticate, UserLoadError, UsersDict


from sessions import crear_sesion  # o import sessions
import arp_lookup



# Host y puerto del servidor HTTP (configurables por variables de entorno)
HOST = os.getenv("PORTAL_HTTP_HOST", "0.0.0.0")
PORT = int(os.getenv("PORTAL_HTTP_PORT", "8080"))
# Número máximo de hilos para atender clientes (concurrencia)
MAX_WORKERS = int(os.getenv("PORTAL_HTTP_WORKERS", "16"))
# Límite de bytes a leer de la petición (cabeceras + body) para evitar consumo desmedido
MAX_REQUEST_BYTES = int(os.getenv("PORTAL_HTTP_MAX_REQUEST", "65536"))
TLS_ENABLED = os.getenv("PORTAL_ENABLE_TLS", "0").strip().lower() in {"1", "true", "yes", "on"}
TLS_CERT_FILE = os.getenv("PORTAL_TLS_CERT")
TLS_KEY_FILE = os.getenv("PORTAL_TLS_KEY")
TLS_CIPHERS = os.getenv("PORTAL_TLS_CIPHERS")

# Directorios de plantillas
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
INDEX_TEMPLATE = TEMPLATES_DIR / "index.html"
LOGIN_TEMPLATE = TEMPLATES_DIR / "login.html"
LOGIN_SUCCESS_TEMPLATE = TEMPLATES_DIR / "login_success.html"
LOGIN_ERROR_TEMPLATE = TEMPLATES_DIR / "login_error.html"

# Mapeo ruta -> Path de plantilla (permitlist)
TEMPLATE_ROUTE_MAP = {
    "/": INDEX_TEMPLATE,
    "/index": INDEX_TEMPLATE,
    "/login": LOGIN_TEMPLATE,
    "/success": LOGIN_SUCCESS_TEMPLATE,
    "/error": LOGIN_ERROR_TEMPLATE,
}

# Cache en memoria de plantillas cargadas (route -> bytes)
TEMPLATE_CACHE: dict[str, bytes] = {}
# Usuarios cargados en memoria (solo-lectura después de cargar)
USERS: UsersDict = {}

# Plantillas de cabecera HTTP
HTTP_OK_TEMPLATE = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: text/html; charset=utf-8\r\n"
    "Content-Length: {length}\r\n"
    "Connection: close\r\n"
    "\r\n"
)

# HTTP 405 ahora usa placeholder para Allow, se rellenará donde corresponda.
HTTP_405_TEMPLATE = (
    "HTTP/1.1 405 Method Not Allowed\r\n"
    "Content-Type: text/html; charset=utf-8\r\n"
    "Content-Length: {length}\r\n"
    "Connection: close\r\n"
    "Allow: {allow}\r\n"
    "\r\n"
)

HTTP_400_TEMPLATE = (
    "HTTP/1.1 400 Bad Request\r\n"
    "Content-Type: text/html; charset=utf-8\r\n"
    "Content-Length: {length}\r\n"
    "Connection: close\r\n"
    "\r\n"
)

HTTP_404_TEMPLATE = (
    "HTTP/1.1 404 Not Found\r\n"
    "Content-Type: text/html; charset=utf-8\r\n"
    "Content-Length: {length}\r\n"
    "Connection: close\r\n"
    "\r\n"
)

HTTP_500_TEMPLATE = (
    "HTTP/1.1 500 Internal Server Error\r\n"
    "Content-Type: text/html; charset=utf-8\r\n"
    "Content-Length: {length}\r\n"
    "Connection: close\r\n"
    "\r\n"
)


def _build_tls_context() -> Optional[ssl.SSLContext]:
    """
    Configura un contexto TLS si PORTAL_ENABLE_TLS está activo.
    Retorna None si TLS está deshabilitado.
    """
    if not TLS_ENABLED:
        return None

    if not TLS_CERT_FILE or not TLS_KEY_FILE:
        logging.error(
            "PORTAL_ENABLE_TLS=1 pero faltan PORTAL_TLS_CERT/PORTAL_TLS_KEY (cert=%s, key=%s)",
            TLS_CERT_FILE,
            TLS_KEY_FILE,
        )
        raise SystemExit(1)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    except AttributeError:
        # En versiones antiguas de Python/SSL no existe TLSVersion
        pass
    if hasattr(ssl, "OP_NO_COMPRESSION"):
        context.options |= ssl.OP_NO_COMPRESSION
    if TLS_CIPHERS:
        try:
            context.set_ciphers(TLS_CIPHERS)
        except ssl.SSLError as exc:
            logging.error("Lista de cifrados inválida en PORTAL_TLS_CIPHERS: %s", exc)
            raise SystemExit(1) from exc

    try:
        context.load_cert_chain(certfile=TLS_CERT_FILE, keyfile=TLS_KEY_FILE)
    except Exception as exc:
        logging.error("No se pudo cargar el certificado/llave TLS: %s", exc)
        raise SystemExit(1) from exc

    return context


def load_template(path: Path, fallback_message: str = "Plantilla no encontrada") -> bytes:
    """
    Lee y devuelve el contenido en bytes de la plantilla indicada.
    En caso de error devuelve una página de error mínima.
    """
    try:
        return path.read_bytes()
    except FileNotFoundError:
        logging.error("Plantilla no encontrada: %s", path)
        return (
            f"<!DOCTYPE html><html><body><h1>Error interno</h1><p>{fallback_message}.</p></body></html>"
        ).encode("utf-8")
    except Exception as exc:
        logging.error("Error leyendo plantilla %s: %s", path, exc)
        return (
            "<!DOCTYPE html><html><body><h1>Error interno</h1><p>No se pudo cargar plantilla.</p></body></html>"
        ).encode("utf-8")


def fill_template_cache() -> None:
    """
    Carga en memoria todas las plantillas definidas en TEMPLATE_ROUTE_MAP.
    Safe to call at startup.
    """
    for route, p in TEMPLATE_ROUTE_MAP.items():
        if route not in TEMPLATE_CACHE:
            TEMPLATE_CACHE[route] = load_template(p, f"No se encontró {p.name}")
    logging.info("Plantillas pre-cargadas: %s", ", ".join(sorted(set(TEMPLATE_CACHE.keys()))))


def read_post_body_and_parse(initial_data: bytes, conn: socket.socket) -> dict:
    """
    Extrae Content-Length de las cabeceras incluidas en initial_data,
    lee el cuerpo restante desde conn hasta Content-Length y parsea
    application/x-www-form-urlencoded -> dict.

    Protección contra DoS:
      - Si Content-Length > MAX_REQUEST_BYTES => rechazamos (retornamos {}).
      - Al leer, nunca se superan MAX_REQUEST_BYTES bytes.
    Devuelve {} ante cualquier error.
    """
    try:
        # Asegurarnos de que initial_data contiene cabeceras completas
        if b"\r\n\r\n" not in initial_data:
            return {}

        headers, rest = initial_data.split(b"\r\n\r\n", 1)
        headers_text = headers.decode("iso-8859-1")

        # Encontrar Content-Length (si existe)
        content_length = 0
        for line in headers_text.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    logging.warning("Content-Length inválido en POST")
                    return {}

        # Rechazar Content-Length sospechosamente grande
        if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
            logging.warning("Content-Length fuera de rango o 0 (%d). Rechazando POST.", content_length)
            return {}

        # rest puede contener parte del body; leer el resto (sin pasar MAX_REQUEST_BYTES)
        body = rest
        # calcular cuantos bytes adicionales pedir, pero nunca pasar MAX_REQUEST_BYTES
        max_body_remaining = min(content_length - len(body), MAX_REQUEST_BYTES - len(headers) - 4)
        bytes_to_read = max(0, max_body_remaining)
        total_read = len(body)
        while bytes_to_read > 0:
            chunk = conn.recv(min(4096, bytes_to_read))
            if not chunk:
                break
            body += chunk
            total_read += len(chunk)
            bytes_to_read = min(content_length - len(body), MAX_REQUEST_BYTES - len(headers) - 4)

        # Si no leimos todo lo que dijo Content-Length, consideramos válido lo que tenemos,
        # pero no aceptamos que el cliente pidiera más que MAX_REQUEST_BYTES (lo rechazamos arriba).
        body_text = body.decode("utf-8", errors="replace")
        parsed = parse_qs(body_text, keep_blank_values=True)
        # Aplanar valores: de listas a strings
        return {k: v[0] for k, v in parsed.items()}

    except Exception as exc:
        logging.exception("Error leyendo/parsing POST body: %s", exc)
        return {}


def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
    """
    Maneja una conexión TCP con un cliente.
    Soporta GET y POST en /login.
    """
    try:
        conn.settimeout(2.0)
        data = b""

        # Leemos hasta encontrar el fin de cabeceras HTTP
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(1024)
            if not chunk:
                break
            data += chunk
            if len(data) > MAX_REQUEST_BYTES:
                body = (
                    b"<!DOCTYPE html><html><body>"
                    b"<h1>400 Bad Request</h1>"
                    b"<p>Peticion demasiado grande.</p>"
                    b"</body></html>"
                )
                header = HTTP_400_TEMPLATE.format(length=len(body)).encode("ascii")
                conn.sendall(header + body)
                return

        if not data:
            return

        # Primera línea de la petición: "GET /ruta HTTP/1.1"
        try:
            request_line = data.split(b"\r\n", 1)[0].decode("iso-8859-1")
            parts = request_line.split(" ")
            if len(parts) != 3:
                logging.warning("Linea de peticion mal formada: %r", request_line)
                return
            method, path, version = parts
        except Exception as exc:
            logging.warning("Error parseando la peticion: %s", exc)
            return

        logging.info("Peticion %s %s desde %s", method, path, addr[0])

        # Soporte para GET y POST
        method_upper = method.upper()

        if method_upper == "GET":
            # GET: continuamos al flujo que sirve plantillas por route más abajo.
            pass

        elif method_upper == "POST":
            # Normalizar ruta (sin query ni fragment)
            route = path.split("?", 1)[0].split("#", 1)[0]

            # Solo permitimos POST en /login
            if route != "/login":
                body = (
                    b"<!DOCTYPE html><html><body>"
                    b"<h1>405 Method Not Allowed</h1>"
                    b"<p>POST no permitido en esta ruta.</p>"
                    b"</body></html>"
                )
                header = HTTP_405_TEMPLATE.format(length=len(body), allow="GET")
                conn.sendall(header.encode("ascii") + body)
                return

            # Parsear body del POST robustamente
            form = read_post_body_and_parse(data, conn)
            if form == {}:
                body = (
                    b"<!DOCTYPE html><html><body>"
                    b"<h1>400 Bad Request</h1><p>POST mal formado.</p>"
                    b"</body></html>"
                )
                header = HTTP_400_TEMPLATE.format(length=len(body)).encode("ascii")
                conn.sendall(header + body)
                return


            username = form.get("username", "").strip()
            password = form.get("password", "")

            # Validaciones básicas (campos vacíos)
            if not username or not password:
                logging.info("Login con campos vacíos desde %s", addr[0])
                body = TEMPLATE_CACHE.get("/error") or (
                    b"<!DOCTYPE html><html><body><h1>Acceso denegado</h1></body></html>"
                )
                header = HTTP_OK_TEMPLATE.format(length=len(body))
                conn.sendall(header.encode("ascii") + body)
                return

            # Validación con auth (USERS cargado en run_server)
            try:
                if authenticate(username, password, USERS):
                    logging.info("Login exitoso para '%s' desde %s", username, addr[0])

                    # Intentar obtener MAC desde el gateway (arp)
                    client_ip = addr[0]
                    try:
                        mac = arp_lookup.get_mac(client_ip)
                        if mac:
                            logging.info("MAC encontrada para %s : %s", client_ip, mac)
                        else:
                            logging.info("No se encontró MAC para %s; continuará solo con IP", client_ip)
                    except Exception as exc:
                        logging.warning("Error obteniendo MAC para %s: %s", client_ip, exc)
                        mac = None

                    # Crear sesión guardando IP y (si se obtuvo) MAC
                    try:
                        # usar sessions.crear_sesion (importarlo arriba)
                        crear_sesion(username, client_ip, mac=mac)
                    except Exception as exc:
                        logging.exception("Error creando sesión para %s: %s", username, exc)

                    body = TEMPLATE_CACHE.get("/success") or "<h1>Autenticación exitosa</h1>".encode("utf-8")

                    header = HTTP_OK_TEMPLATE.format(length=len(body))
                    conn.sendall(header.encode("ascii") + body)
                    return

                else:
                    body = TEMPLATE_CACHE.get("/error") or (
                        b"<!DOCTYPE html><html><body><h1>Acceso denegado</h1></body></html>"
                    )
                    header = HTTP_OK_TEMPLATE.format(length=len(body))
                    conn.sendall(header.encode("ascii") + body)
                    return
            except Exception as exc:
                logging.exception("Error validando credenciales: %s", exc)
                body = (
                    b"<!DOCTYPE html><html><body>"
                    b"<h1>Error interno</h1><p>Fallo validando credenciales.</p>"
                    b"</body></html>"
                )
                header = HTTP_500_TEMPLATE.format(length=len(body)).encode("ascii")
                conn.sendall(header + body)
                return

        else:
            # Método no permitido. Si la ruta es /login, permitir GET,POST; si no, solo GET.
            allow = "GET, POST" if path.split("?", 1)[0].split("#", 1)[0] == "/login" else "GET"
            body = (
                "<!DOCTYPE html><html><body>"
                "<h1>405 Method Not Allowed</h1>"
                "<p>Solo se permiten métodos permitidos en esta ruta.</p>"
                "</body></html>"
            ).encode("utf-8")
            header = HTTP_405_TEMPLATE.format(length=len(body), allow=allow)
            conn.sendall(header.encode("ascii") + body)
            return

        # Normalizar la ruta: quitar query string y fragmento
        route = path.split("?", 1)[0].split("#", 1)[0]

        # Rechazar intentos evidentes de path-traversal o percent-encoding peligroso
        if ".." in route or "%" in route:
            logging.warning("Intento de ruta inválida desde %s: %s", addr[0], path)
            body = (
                b"<!DOCTYPE html><html><body>"
                b"<h1>404 Not Found</h1><p>Ruta no encontrada.</p>"
                b"</body></html>"
            )
            header = HTTP_404_TEMPLATE.format(length=len(body)).encode("ascii")
            conn.sendall(header + body)
            return

        body = TEMPLATE_CACHE.get(route)
        if body is None:
            # Ruta no encontrada → 404 real
            body = (
                b"<!DOCTYPE html><html><body>"
                b"<h1>404 Not Found</h1><p>Ruta no encontrada.</p>"
                b"</body></html>"
            )
            header = HTTP_404_TEMPLATE.format(length=len(body)).encode("ascii")
            conn.sendall(header + body)
            return

        # Si llegamos aquí, hay plantilla válida: enviar 200 OK
        header = HTTP_OK_TEMPLATE.format(length=len(body)).encode("ascii")
        conn.sendall(header + body)

    finally:
        conn.close()


def run_server(host: str = HOST, port: int = PORT) -> None:
    """
    Arranca el servidor HTTP y acepta conexiones en bucle.

    Cada conexión se maneja en un hilo del pool (ThreadPoolExecutor).
    """
    # Precargar todas las plantillas en cache
    fill_template_cache()

    global USERS

    # Cargar usuarios desde config/usuarios.txt
    try:
        USERS = load_users()
        logging.info("Usuarios cargados en memoria: %d", len(USERS))
    except UserLoadError as err:
        logging.error("No se pudieron cargar usuarios: %s. El login fallará hasta corregir.", err)
        USERS = {}

    stop_event = threading.Event()

    tls_context = _build_tls_context()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((host, port))
        server_sock.listen(64)  # backlog decente para picos breves
        server_sock.settimeout(1.0)  # para permitir cerrar con Ctrl+C

        if tls_context:
            logging.info(
                "Servidor HTTPS escuchando en %s:%d (cert=%s)",
                host,
                port,
                TLS_CERT_FILE,
            )
        else:
            logging.info("Servidor HTTP escuchando en %s:%d", host, port)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            try:
                while not stop_event.is_set():
                    try:
                        conn, addr = server_sock.accept()
                    except socket.timeout:
                        continue
                    except OSError:
                        break  # socket cerrado
                    if tls_context:
                        try:
                            conn = tls_context.wrap_socket(conn, server_side=True)
                        except ssl.SSLError as exc:
                            logging.warning(
                                "Fallo handshake TLS con %s: %s", addr[0], exc
                            )
                            conn.close()
                            continue

                    executor.submit(handle_client, conn, addr)
            except KeyboardInterrupt:
                logging.info("Se recibio Ctrl+C, deteniendo servidor...")
                stop_event.set()
            finally:
                server_sock.close()
                executor.shutdown(wait=True)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    run_server()
