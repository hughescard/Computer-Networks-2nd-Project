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
CONNTRACK = shutil.which("conntrack") or "/usr/sbin/conntrack"

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


def _rule_exists(check_cmd: list[str]) -> bool:
    """
    Devuelve True si la regla ya existe (usa iptables -C).
    check_cmd debe incluir la cadena de coincidencia completa sin el -C inicial.
    """
    if not _ensure_binary():
        return False
    cmd = [IPTABLES, "-C"] + check_cmd
    result = subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return result.returncode == 0


def _flush_conntrack(ip: str) -> None:
    """
    Elimina entradas de conntrack para la IP (evita que conexiones establecidas sigan vivas tras logout).
    Si no existe el binario `conntrack`, solo loguea una advertencia.
    """
    if not CONNTRACK or not os.path.exists(CONNTRACK):
        logging.warning("[FIREWALL] No se pudo limpiar conntrack (binario conntrack no encontrado)")
        return
    cmd = [CONNTRACK, "-D", "-s", ip]
    try:
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info("[FIREWALL] Limpiada tabla conntrack para origen %s", ip)
    except Exception as exc:  # noqa: BLE001
        logging.warning("[FIREWALL] Error limpiando conntrack para %s: %s", ip, exc)


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

    ok_forward = True
    ok_bypass = True

    if _rule_exists(allow_forward[1:]):  # quitar binario iptables
        logging.info("[FIREWALL] Regla FORWARD ya existía para %s", ip)
    else:
        ok_forward = _run(allow_forward)

    if _rule_exists(bypass_redirect[1:]):
        logging.info("[FIREWALL] Regla PREROUTING ya existía para %s", ip)
    else:
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

    # Elimina todas las ocurrencias de la regla (puede haber duplicados si hubo varias instancias)
    ok_forward = True
    ok_bypass = True

    removed_any = False
    while _run(remove_forward):
        removed_any = True
    if not removed_any:
        logging.info("[FIREWALL] No se encontró regla FORWARD para %s (mac=%s)", ip, mac)

    removed_any = False
    while _run(remove_bypass):
        removed_any = True
    if not removed_any:
        logging.info("[FIREWALL] No se encontró regla PREROUTING para %s (mac=%s)", ip, mac)

    _flush_conntrack(ip)

    return ok_forward and ok_bypass



def listar_reglas() -> None:
    """Imprime las reglas actuales (para debug)."""
    subprocess.run([IPTABLES, "-L", "FORWARD", "-n", "-v"])
    subprocess.run([IPTABLES, "-t", "nat", "-L", "PREROUTING", "-n", "-v"])
