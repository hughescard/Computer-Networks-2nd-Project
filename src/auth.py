#!/usr/bin/env python3
"""
Módulo de autenticación del portal cautivo.

- Define el formato del archivo de usuarios (config/usuarios.txt).
- Carga usuarios/contraseñas en memoria.
- Proporciona una función para validar credenciales.

Formato del archivo config/usuarios.txt:

    # Comentarios empiezan con #
    # usuario:contraseña (sin espacios alrededor)
    admin:admin
    invitado:invitado123

- Líneas vacías y comentarios se ignoran.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict


# Rutas base: repo_root/config/usuarios.txt
SRC_DIR = Path(__file__).resolve().parent          # .../repo/src
REPO_ROOT = SRC_DIR.parent                         # .../repo
CONFIG_DIR = REPO_ROOT / "config"
DEFAULT_USERS_FILE = CONFIG_DIR / "usuarios.txt"


class UserLoadError(Exception):
    """Error al cargar el archivo de usuarios."""


UsersDict = Dict[str, str]


def load_users(path: str | Path = DEFAULT_USERS_FILE) -> UsersDict:
    """
    Carga el archivo de usuarios y devuelve un diccionario {usuario: contraseña}.

    Levanta UserLoadError si:
    - El archivo no existe o no se puede leer.
    - Alguna línea tiene formato inválido.
    - Hay usuarios duplicados.
    """
    path = Path(path)

    if not path.exists():
        raise UserLoadError(f"No se encontró el archivo de usuarios: {path}")
    if not path.is_file():
        raise UserLoadError(f"La ruta de usuarios no es un archivo regular: {path}")

    users: UsersDict = {}

    try:
        with path.open("r", encoding="utf-8") as file:
            for lineno, raw_line in enumerate(file, start=1):
                line = raw_line.strip()

                # Ignorar comentarios y líneas en blanco
                if not line or line.startswith("#"):
                    continue

                # Formato: usuario:contraseña
                if ":" not in line:
                    raise UserLoadError(
                        f"Formato inválido en línea {lineno}: falta ':'"
                    )

                username, password = line.split(":", 1)
                username = username.strip()
                password = password.strip()

                if not username or not password:
                    raise UserLoadError(
                        f"Formato inválido en línea {lineno}: "
                        "usuario y contraseña no pueden estar vacíos"
                    )

                if username in users:
                    raise UserLoadError(
                        f"Usuario duplicado '{username}' en línea {lineno}"
                    )

                users[username] = password

    except OSError as exc:
        raise UserLoadError(f"Error leyendo archivo de usuarios: {exc}") from exc

    logging.info("Cargados %d usuarios desde %s", len(users), path)
    return users


def authenticate(username: str, password: str, users: UsersDict) -> bool:
    """
    Devuelve True si (usuario, contraseña) son válidos según el diccionario cargado.
    """
    stored = users.get(username)
    return stored is not None and stored == password


if __name__ == "__main__":
    # Pequeña prueba manual: python3 src/auth.py
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    try:
        usuarios = load_users()
        print("Usuarios cargados:", usuarios)
        print("Prueba authenticate('admin', 'admin') ->",
              authenticate("admin", "admin", usuarios))
    except UserLoadError as err:
        logging.error("%s", err)
