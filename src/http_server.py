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
import threading
from pathlib import Path
from typing import Tuple

# Host y puerto del servidor HTTP (configurables por variables de entorno)
HOST = os.getenv("PORTAL_HTTP_HOST", "0.0.0.0")
PORT = int(os.getenv("PORTAL_HTTP_PORT", "8080"))

# Directorios de plantillas 
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
INDEX_TEMPLATE = TEMPLATES_DIR / "index.html"

# Plantillas de cabecera HTTP
HTTP_OK_TEMPLATE = (
    "HTTP/1.1 200 OK\r\n"
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

# Aquí dejaremos en memoria el contenido de index.html
HTML_INDEX: bytes = b""


def load_index_html() -> bytes:
    """
    Carga el contenido de src/templates/index.html en memoria.

    Si no existe, devolvemos una página de error sencilla.
    """
    try:
        return INDEX_TEMPLATE.read_bytes()
    except FileNotFoundError:
        logging.error("No se encontro la plantilla %s", INDEX_TEMPLATE)
        return (
            b"<!DOCTYPE html><html><body>"
            b"<h1>Error interno</h1>"
            b"<p>No se encontro la plantilla index.html.</p>"
            b"</body></html>"
        )


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

        # Respuesta 200 OK con la página HTML de prueba
        body = HTML_INDEX
        header = HTTP_OK_TEMPLATE.format(length=len(body)).encode("ascii")
        conn.sendall(header + body)

    finally:
        conn.close()


def run_server(host: str = HOST, port: int = PORT) -> None:
    """
    Arranca el servidor HTTP y acepta conexiones en bucle.

    Cada conexión se maneja en un hilo separado.
    """
    global HTML_INDEX
    HTML_INDEX = load_index_html()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((host, port))
        server_sock.listen(5)

        logging.info("Servidor HTTP (socket) escuchando en %s:%d", host, port)

        try:
            while True:
                conn, addr = server_sock.accept()
                thread = threading.Thread(
                    target=handle_client,
                    args=(conn, addr),
                    daemon=True,
                )
                thread.start()
        except KeyboardInterrupt:
            logging.info("Se recibio Ctrl+C, deteniendo servidor...")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    run_server()
