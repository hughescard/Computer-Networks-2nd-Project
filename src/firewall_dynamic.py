#!/usr/bin/env python3
"""
firewall_dynamic.py
--------------------
Este módulo añade y elimina reglas de iptables dinámicamente
cuando un usuario inicia o cierra sesión en el portal cautivo.
"""

import subprocess
import logging

IPTABLES = "/usr/sbin/iptables"   # O usa `command -v iptables`

def _run(cmd: list[str]) -> bool:
    """Ejecuta un comando y devuelve True/False según éxito."""
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
    Permite a una IP reenviar tráfico hacia Internet.
    Se inserta al inicio de FORWARD para prioridad.
    """
    cmd = [IPTABLES, "-I", "FORWARD", "1", "-s", ip, "-j", "ACCEPT"]
    return _run(cmd)


def denegar_ip(ip: str) -> bool:
    """
    Elimina la regla de FORWARD que permite a la IP navegar.
    """
    cmd = [IPTABLES, "-D", "FORWARD", "-s", ip, "-j", "ACCEPT"]
    return _run(cmd)


def listar_reglas() -> None:
    """Imprime las reglas actuales (para debug)."""
    subprocess.run([IPTABLES, "-L", "FORWARD", "-n", "-v"])
