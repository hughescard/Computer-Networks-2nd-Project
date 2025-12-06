#!/usr/bin/env python3
"""
firewall_dynamic.py
--------------------
Este módulo añade y elimina reglas de iptables dinámicamente
cuando un usuario inicia o cierra sesión en el portal cautivo.
"""

import subprocess
import logging
import shutil
import os

IPTABLES = shutil.which("iptables") or "/sbin/iptables"

# Parámetros para las reglas dinámicas (ajustables vía variables de entorno)
LAN_INTERFACE = os.getenv("PORTAL_LAN_IF", "enp0s8")
# Puerto que intercepta el portal (HTTP claro típico)
CAPTIVE_HTTP_PORT = os.getenv("CAPTIVE_HTTP_PORT", "80")


def _ensure_binary() -> bool:
    if not IPTABLES:
        logging.error("[FIREWALL] No se encontró el binario de iptables en PATH.")
        return False
    return True

def _run(cmd: list[str]) -> bool:
    """Ejecuta un comando y devuelve True/False según éxito."""
    if not _ensure_binary():
        return False
    try:
        subprocess.run(cmd, check=True)
        logging.info("[FIREWALL] Ejecutado: %s", " ".join(cmd))
        return True
    except subprocess.CalledProcessError as exc:
        logging.error("[FIREWALL] Error al ejecutar '%s': %s",
                      " ".join(cmd), exc)
        return False


def permitir_ip(ip: str) -> bool:
    """
    permite por IP (sin MAC).
    """
    return permitir_ip_mac(ip, None)


def permitir_ip_mac(ip: str, mac: str | None) -> bool:
    """
    Permite a una IP (y opcionalmente MAC) reenviar tráfico hacia Internet
    y evita que sus peticiones HTTP sean redirigidas al portal cautivo.
    Si mac es None se usa solo IP (como antes). Si mac está presente
    se añade un match de MAC para endurecer la regla.
    """
    base_forward = [IPTABLES, "-I", "FORWARD", "1", "-s", ip]
    base_bypass = [
        IPTABLES,
        "-t",
        "nat",
        "-I",
        "PREROUTING",
        "1",
        "-i",
        LAN_INTERFACE,
        "-s",
        ip,
        "-p",
        "tcp",
        "--dport",
        CAPTIVE_HTTP_PORT,
    ]

    if mac:
        # Añadir match por MAC (solo tiene sentido en paquetes entrantes por interfaz LAN)
        base_forward += ["-m", "mac", "--mac-source", mac]
        base_bypass += ["-m", "mac", "--mac-source", mac]

    allow_forward = base_forward + ["-j", "ACCEPT"]
    bypass_redirect = base_bypass + ["-j", "RETURN"]

    ok_forward = _run(allow_forward)
    ok_bypass = _run(bypass_redirect)
    return ok_forward and ok_bypass



def denegar_ip(ip: str) -> bool:
    """
    Eliminar reglas por IP.
    """
    return denegar_ip_mac(ip, None)


def denegar_ip_mac(ip: str, mac: str | None) -> bool:
    """
    Elimina las reglas que permiten navegar a la IP (FORWARD)
    y su bypass de redirección HTTP (PREROUTING nat).
    Si mac es None, elimina reglas que no usan match mac.
    Si mac está presente, intenta eliminar las reglas con match mac.
    """
    remove_forward = [IPTABLES, "-D", "FORWARD", "-s", ip]
    remove_bypass = [
        IPTABLES,
        "-t",
        "nat",
        "-D",
        "PREROUTING",
        "-i",
        LAN_INTERFACE,
        "-s",
        ip,
        "-p",
        "tcp",
        "--dport",
        CAPTIVE_HTTP_PORT,
    ]

    if mac:
        remove_forward += ["-m", "mac", "--mac-source", mac, "-j", "ACCEPT"]
        remove_bypass += ["-m", "mac", "--mac-source", mac, "-j", "RETURN"]
    else:
        # agregar objetivos para que el -D tenga el mismo formato que -A/ -I creó
        remove_forward += ["-j", "ACCEPT"]
        remove_bypass += ["-j", "RETURN"]

    ok_forward = _run(remove_forward)
    ok_bypass = _run(remove_bypass)
    return ok_forward and ok_bypass



def listar_reglas() -> None:
    """Imprime las reglas actuales (para debug)."""
    subprocess.run([IPTABLES, "-L", "FORWARD", "-n", "-v"])
    subprocess.run([IPTABLES, "-t", "nat", "-L", "PREROUTING", "-n", "-v"])
