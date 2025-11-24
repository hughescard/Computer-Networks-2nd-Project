#!/usr/bin/env python3
"""
Servidor HTTP básico para el portal cautivo.

- Usa solo biblioteca estándar.
- NO usa ninguna librería HTTP (ni http.server, ni nada que parsee HTTP).
- Todo el manejo de HTTP se hace "a mano" leyendo del socket.
- Carga el HTML desde src/templates/index.html.
"""

import logging
import os
import socket
from concurrent.futures import ThreadPoolExecutor
import threading
from pathlib import Path
from typing import Tuple

# Host y puerto del servidor HTTP (configurables por variables de entorno)
HOST = os.getenv("PORTAL_HTTP_HOST", "0.0.0.0")
PORT = int(os.getenv("PORTAL_HTTP_PORT", "8080"))
# Número máximo de hilos para atender clientes (concurrencia)
MAX_WORKERS = int(os.getenv("PORTAL_HTTP_WORKERS", "16"))
# Límite de bytes a leer de la petición (cabeceras) para evitar consumo desmedido
MAX_REQUEST_BYTES = int(os.getenv("PORTAL_HTTP_MAX_REQUEST", "65536"))

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


# Plantillas de cabecera HTTP
HTTP_OK_TEMPLATE = (
    "HTTP/1.1 200 OK\r\n"
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


HTTP_405_TEMPLATE = (
    "HTTP/1.1 405 Method Not Allowed\r\n"
    "Content-Type: text/html; charset=utf-8\r\n"
    "Content-Length: {length}\r\n"
    "Connection: close\r\n"
    "Allow: GET\r\n"
    "\r\n"
)

# Respuesta 400 para peticiones demasiado grandes/mal formadas
HTTP_400_TEMPLATE = (
    "HTTP/1.1 400 Bad Request\r\n"
    "Content-Type: text/html; charset=utf-8\r\n"
    "Content-Length: {length}\r\n"
    "Connection: close\r\n"
    "\r\n"
)





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
            "<!DOCTYPE html><html><body><h1>Error interno</h1><p>Fallo leyendo plantilla.</p></body></html>"
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


def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
    """
    Maneja una conexión TCP con un cliente.

    - Lee desde el socket hasta encontrar el final de las cabeceras HTTP (\r\n\r\n).
    - Parsea la primera línea de la petición manualmente.
    - Si es GET, envía el contenido de HTML_INDEX con un 200 OK.
    - Si es otro método, responde 405 Method Not Allowed.
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
        except Exception as exc:  # noqa: BLE001
            logging.warning("Error parseando la peticion: %s", exc)
            return

        logging.info("Peticion %s %s desde %s", method, path, addr[0])

        # Solo aceptamos GET por ahora
        if method.upper() != "GET":
            body = (
                b"<!DOCTYPE html><html><body>"
                b"<h1>405 Method Not Allowed</h1>"
                b"<p>Solo se permite GET.</p>"
                b"</body></html>"
            )
            header = HTTP_405_TEMPLATE.format(length=len(body)).encode("ascii")
            conn.sendall(header + body)
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

    stop_event = threading.Event()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((host, port))
        server_sock.listen(64)  # backlog decente para picos breves
        server_sock.settimeout(1.0)  # para permitir cerrar con Ctrl+C

        logging.info("Servidor HTTP (socket) escuchando en %s:%d", host, port)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            try:
                while not stop_event.is_set():
                    try:
                        conn, addr = server_sock.accept()
                    except socket.timeout:
                        continue
                    except OSError:
                        break  # socket cerrado

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
