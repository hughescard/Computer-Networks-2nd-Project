#!/usr/bin/env python3
"""
Módulo de gestión de sesiones en memoria para el portal cautivo.

- Mantiene un mapa (IP[, MAC]) -> datos de sesión.
- Proporciona funciones para crear, obtener y eliminar sesiones.
- Cada sesión almacena:
    - usuario
    - IP
    - MAC (opcional)
    - hora de login
    - hora de expiración (opcional)

Este módulo está pensado para usarse desde el servidor HTTP
cuando un usuario hace login correctamente.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

# Helper para reglas dinámicas de firewall
import firewall_dynamic


# Tipo de clave: IP sola o IP+MAC
SessionKey = Tuple[str, Optional[str]]


@dataclass
class Session:
    """Datos almacenados para cada sesión activa."""

    username: str
    ip: str
    mac: Optional[str]
    login_time: float          # timestamp (time.time())
    expires_at: Optional[float] = None  # timestamp o None si no expira

    def is_expired(self, now: Optional[float] = None) -> bool:
        """Devuelve True si la sesión está expirada (si tiene expiración)."""
        if self.expires_at is None:
            return False
        if now is None:
            now = time.time()
        return now >= self.expires_at


# Almacenamiento en memoria
_sessions: Dict[SessionKey, Session] = {}

# Lock para hacer el módulo seguro frente a múltiples hilos
_lock = threading.Lock()

# Tiempo por defecto de duración de una sesión (en segundos).
# Se puede ajustar con la variable de entorno PORTAL_SESSION_TTL.
DEFAULT_SESSION_TTL = 60 * 60  # 1 hora
_env_ttl = os.getenv("PORTAL_SESSION_TTL")
if _env_ttl:
    try:
        DEFAULT_SESSION_TTL = int(_env_ttl)
    except ValueError:
        logging.warning(
            "PORTAL_SESSION_TTL inválido (%s); usando valor por defecto %s",
            _env_ttl,
            DEFAULT_SESSION_TTL,
        )

# Ruta para persistir sesiones en disco
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SESSIONS_FILE = REPO_ROOT / "config" / "sessions.json"


def _serialize_sessions() -> Dict[str, dict]:
    """
    Convierte el diccionario interno en un dict serializable a JSON.
    La clave se guarda como "ip" y "mac" en el payload.
    """
    payload: Dict[str, dict] = {}
    for (ip, mac), sess in _sessions.items():
        payload_key = f"{ip}|{mac or ''}"
        payload[payload_key] = {
            "username": sess.username,
            "ip": sess.ip,
            "mac": sess.mac,
            "login_time": sess.login_time,
            "expires_at": sess.expires_at,
        }
    return payload


def _deserialize_sessions(data: Dict[str, dict]) -> Dict[SessionKey, "Session"]:
    """
    Reconstruye sesiones desde un dict cargado de JSON.
    Descarta entradas incompletas.
    """
    restored: Dict[SessionKey, Session] = {}
    now = time.time()

    for raw_key, raw_sess in data.items():
        if "|" not in raw_key:
            logging.warning("Clave de sesión inválida en JSON: %s", raw_key)
            continue
        ip, mac = raw_key.split("|", 1)
        mac = mac or None

        try:
            username = raw_sess["username"]
            login_time = float(raw_sess["login_time"])
            expires_at = raw_sess.get("expires_at")
            expires_at = float(expires_at) if expires_at is not None else None
        except Exception as exc:  # noqa: BLE001
            logging.warning("Entrada de sesión inválida en JSON (%s): %s", raw_key, exc)
            continue

        session = Session(
            username=username,
            ip=ip,
            mac=mac.lower() if mac else None,
            login_time=login_time,
            expires_at=expires_at,
        )

        # Filtra expiradas al cargar
        if session.is_expired(now):
            continue

        restored[_make_key(ip, mac)] = session

    return restored


def _save_to_disk(path: Path = DEFAULT_SESSIONS_FILE) -> None:
    """
    Persiste las sesiones actuales en disco (JSON). Ignora errores de E/S.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import json

        with path.open("w", encoding="utf-8") as f:
            json.dump(_serialize_sessions(), f, ensure_ascii=True, indent=2)
    except Exception as exc:  # noqa: BLE001
        logging.error("No se pudieron guardar las sesiones en %s: %s", path, exc)


def _load_from_disk(path: Path = DEFAULT_SESSIONS_FILE) -> None:
    """
    Carga sesiones desde disco, descartando las expiradas.
    """
    if not path.exists():
        return

    try:
        import json

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001
        logging.error("No se pudieron cargar sesiones desde %s: %s", path, exc)
        return

    restored = _deserialize_sessions(data)
    with _lock:
        _sessions.clear()
        _sessions.update(restored)
        logging.info("Sesiones restauradas desde disco: %d activas", len(_sessions))
        # Reaplicar reglas de firewall para sesiones vigentes
        for sess in _sessions.values():
            if sess.mac:
                firewall_dynamic.permitir_ip_mac(sess.ip, sess.mac)
            else:
                firewall_dynamic.permitir_ip(sess.ip)

        if _sessions:
            logging.info("Reglas de firewall re-aplicadas para sesiones activas tras carga en disco.")


def _make_key(ip: str, mac: Optional[str] = None) -> SessionKey:
    """
    Construye la clave interna para el diccionario de sesiones.

    - Normaliza la MAC a minúsculas si se proporciona.
    """
    mac_norm = mac.lower() if mac is not None else None
    return (ip, mac_norm)


def crear_sesion(
    username: str,
    ip: str,
    mac: Optional[str] = None,
    ttl: Optional[int] = None,
) -> Session:
    """
    Crea (o reemplaza) una sesión para (ip, mac) y la devuelve.

    Parámetros:
    - username: usuario autenticado.
    - ip: IP del cliente.
    - mac: MAC del cliente (opcional).
    - ttl: tiempo de vida en segundos; si es None, usa DEFAULT_SESSION_TTL.
           Si ttl <= 0, la sesión no expira (expires_at = None).
    """
    if ttl is None:
        ttl = DEFAULT_SESSION_TTL

    now = time.time()
    if ttl > 0:
        expires_at: Optional[float] = now + ttl
    else:
        expires_at = None

    key = _make_key(ip, mac)
    session = Session(
        username=username,
        ip=ip,
        mac=mac.lower() if mac is not None else None,
        login_time=now,
        expires_at=expires_at,
    )

    with _lock:
        _sessions[key] = session
        logging.info(
            "Creada/actualizada sesión para %s (usuario=%s, ttl=%s)",
            key,
            username,
            ttl,
        )
        _save_to_disk()

        # Permitir a la IP/mac navegar (si hay mac, usar ip+mac)
        if session.mac:
            firewall_dynamic.permitir_ip_mac(session.ip, session.mac)
            logging.info("Regla de firewall añadida para permitir navegación a %s (MAC %s)", session.ip, session.mac)
        else:
            firewall_dynamic.permitir_ip(session.ip)
            logging.info("Regla de firewall añadida para permitir navegación a %s", session.ip)



    return session


def obtener_sesion(ip: str, mac: Optional[str] = None) -> Optional[Session]:
    """
    Devuelve la sesión asociada a (ip, mac) o None si no existe o está expirada.

    Si la sesión está expirada se elimina automáticamente.
    """
    key = _make_key(ip, mac)
    now = time.time()

    with _lock:
        session = _sessions.get(key)
        if session is None:
            return None

        if session.is_expired(now):
            logging.info("Sesión expirada para %s; eliminando", key)
            _sessions.pop(key, None)
            _save_to_disk()
            if session.mac:
                firewall_dynamic.denegar_ip_mac(session.ip, session.mac)
            else:
                firewall_dynamic.denegar_ip(session.ip)

            logging.info("Regla de firewall eliminada (sesión expirada) para %s", ip)

            return None
        

        return session


def eliminar_sesion(ip: str, mac: Optional[str] = None) -> bool:
    """
    Elimina la sesión asociada a (ip, mac).

    Devuelve:
    - True si existía una sesión y se eliminó.
    - False si no había sesión para esa clave.
    """
    key = _make_key(ip, mac)
    with _lock:
        existed = key in _sessions
        if existed:
            _sessions.pop(key, None)
            logging.info("Sesión eliminada para %s", key)
            _save_to_disk()

            # Eliminar regla de navegación (si existía MAC, usarla)
            if mac := key[1]:
                firewall_dynamic.denegar_ip_mac(ip, mac)
                logging.info("Regla de firewall eliminada para %s (MAC %s)", ip, mac)
            else:
                firewall_dynamic.denegar_ip(ip)
                logging.info("Regla de firewall eliminada para %s", ip)


        return existed


def eliminar_sesiones_por_ip(ip: str) -> int:
    """
    Elimina todas las sesiones cuyo campo IP coincide, independientemente de la MAC.

    Útil como fallback si no se puede resolver la MAC en el logout.
    Devuelve cuántas sesiones fueron eliminadas.
    """
    # Refrescar desde disco por si otra instancia del portal creó la sesión
    _load_from_disk()

    removed_sessions = []
    with _lock:
        for key, sess in list(_sessions.items()):
            if sess.ip == ip:
                removed_sessions.append((key, sess))
                _sessions.pop(key, None)
        if removed_sessions:
            _save_to_disk()

    for key, sess in removed_sessions:
        if sess.mac:
            firewall_dynamic.denegar_ip_mac(sess.ip, sess.mac)
            logging.info("Regla de firewall eliminada para %s (MAC %s)", sess.ip, sess.mac)
        else:
            firewall_dynamic.denegar_ip(sess.ip)
            logging.info("Regla de firewall eliminada para %s", sess.ip)

    if removed_sessions:
        logging.info("Sesiones eliminadas por IP %s: %d", ip, len(removed_sessions))
    return len(removed_sessions)


def limpiar_sesiones_expiradas() -> int:
    """
    Elimina todas las sesiones expiradas y devuelve cuántas se eliminaron.

    Esta función no es estrictamente necesaria para el issue,
    pero puede ser útil para tareas de mantenimiento.
    """
    now = time.time()
    removed = 0

    with _lock:
        keys_to_delete = [
            key for key, sess in _sessions.items() if sess.is_expired(now)
        ]
        for key in keys_to_delete:
            sess = _sessions.pop(key, None)
            if not sess:
                continue
            if sess.mac:
                firewall_dynamic.denegar_ip_mac(sess.ip, sess.mac)
            else:
                firewall_dynamic.denegar_ip(sess.ip)

            removed += 1
        if removed:
            _save_to_disk()

    if removed:
        logging.info("Limpieza de sesiones: %d sesiones expiradas eliminadas", removed)
    return removed


def obtener_todas_las_sesiones() -> Dict[SessionKey, Session]:
    """
    Devuelve una copia del diccionario de sesiones actuales.

    Útil para depuración o para mostrar el estado interno.
    """
    with _lock:
        return dict(_sessions)

# Restauramos sesiones (si existen en disco) al importar el módulo
_load_from_disk()

if __name__ == "__main__":
    # Restaura sesiones previas antes de iniciar pruebas manuales
    _load_from_disk()

    # Pruebas rápidas desde la línea de comandos:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    print("Creando sesión para 10.0.2.15 (usuario=admin)...")
    s1 = crear_sesion("admin", "10.0.2.15", mac="AA:BB:CC:DD:EE:FF", ttl=5)
    print("Sesión creada:", s1)

    print("Obteniendo sesión inmediatamente...")
    s2 = obtener_sesion("10.0.2.15", mac="aa:bb:cc:dd:ee:ff")
    print("Resultado:", s2)

    print("Esperando a que expire (6 segundos)...")
    time.sleep(6)
    s3 = obtener_sesion("10.0.2.15", mac="aa:bb:cc:dd:ee:ff")
    print("Después de la expiración, obtener_sesion ->", s3)
