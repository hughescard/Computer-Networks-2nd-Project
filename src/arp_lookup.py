#!/usr/bin/env python3
"""
arp_lookup.py

Funciones para obtener la MAC asociada a una IP desde el gateway (tabla ARP).
Intentos:
 - ip neigh show <IP>
 - /proc/net/arp
Devuelve la MAC en minúsculas o None si no se encuentra.
"""

from __future__ import annotations
import subprocess
import logging
import re
from typing import Optional

_IP_NEIGH_CMD = ["ip", "neigh", "show"]

MAC_RE = re.compile(r"([0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5})")

def _parse_ip_neigh_output(out: str, ip: str) -> Optional[str]:
    for line in out.splitlines():
        if ip in line:
            m = MAC_RE.search(line)
            if m:
                return m.group(1).lower()
    return None

def _parse_proc_arp(ip: str) -> Optional[str]:
    try:
        with open("/proc/net/arp", "r", encoding="utf-8") as f:
            lines = f.read().splitlines()[1:]  # saltar header
    except Exception:
        return None
    for ln in lines:
        parts = ln.split()
        if len(parts) >= 4 and parts[0] == ip:
            mac = parts[3]
            if MAC_RE.match(mac):
                return mac.lower()
    return None

def get_mac(ip: str) -> Optional[str]:
    """
    Devuelve la MAC asociada a `ip` consultando la tabla ARP.
    Si no la encuentra devuelve None.
    """
    try:
        # Primero ip neigh (rápido, moderno)
        proc = subprocess.run(_IP_NEIGH_CMD + [ip], capture_output=True, text=True, check=False)
        if proc.returncode == 0 and proc.stdout:
            mac = _parse_ip_neigh_output(proc.stdout, ip)
            if mac:
                return mac
    except Exception as exc:
        logging.debug("ip neigh fallo: %s", exc)

    # Fallback a /proc/net/arp
    try:
        mac = _parse_proc_arp(ip)
        if mac:
            return mac
    except Exception as exc:
        logging.debug("/proc/net/arp fallo: %s", exc)

    return None
