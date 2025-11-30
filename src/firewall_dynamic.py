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
    Permite a una IP reenviar tráfico hacia Internet y evita que sus
    peticiones HTTP sean redirigidas al portal cautivo.
    Se insertan reglas al inicio de FORWARD y PREROUTING (nat) para prioridad.
    """
    allow_forward = [IPTABLES, "-I", "FORWARD", "1", "-s", ip, "-j", "ACCEPT"]
    bypass_redirect = [
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
        "-j",
        "RETURN",
    ]
    ok_forward = _run(allow_forward)
    ok_bypass = _run(bypass_redirect)
    return ok_forward and ok_bypass


def denegar_ip(ip: str) -> bool:
    """
    Elimina las reglas que permiten navegar a la IP (FORWARD)
    y su bypass de redirección HTTP (PREROUTING nat).
    """
    remove_forward = [IPTABLES, "-D", "FORWARD", "-s", ip, "-j", "ACCEPT"]
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
        "-j",
        "RETURN",
    ]
    ok_forward = _run(remove_forward)
    ok_bypass = _run(remove_bypass)
    return ok_forward and ok_bypass


def listar_reglas() -> None:
    """Imprime las reglas actuales (para debug)."""
    subprocess.run([IPTABLES, "-L", "FORWARD", "-n", "-v"])
