#!/usr/bin/env bash
set -e

echo "== Portal cautivo – Configuración de entorno de desarrollo =="

# 1. Comprobaciones básicas
echo "[1/4] Comprobando herramientas básicas..."

for cmd in git bash iptables ip addr; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "  - ADVERTENCIA: no se encontró '$cmd' en el sistema."
    else
        echo "  - OK: $cmd"
    fi
done

# 2. Instalación de paquetes mínimos en sistemas basados en apt (opcional)
if command -v apt >/dev/null 2>&1; then
    echo "[2/4] Sistema basado en apt detectado. (Ubuntu/Debian)"
    echo "      (Si no tienes permisos de sudo, salta esta parte.)"
    read -p "¿Quieres intentar instalar paquetes básicos con sudo apt? [s/N]: " ans
    if [[ "$ans" == "s" || "$ans" == "S" ]]; then
        sudo apt update
        sudo apt install -y build-essential net-tools iproute2 iptables
    else
        echo "  - Saltando instalación automática de paquetes."
    fi
else
    echo "[2/4] No se detectó apt, omitiendo instalación de paquetes."
fi

# 3. Opcional: entorno Python si el servidor está en Python
if command -v python3 >/dev/null 2>&1; then
    echo "[3/4] Se encontró python3. Opcional: crear entorno virtual."
    read -p "¿Quieres crear/usar un entorno virtual .venv? [s/N]: " venv_ans
    if [[ "$venv_ans" == "s" || "$venv_ans" == "S" ]]; then
        python3 -m venv .venv
        # shellcheck disable=SC1091
        source .venv/bin/activate
        pip install --upgrade pip
        echo "  - Entorno virtual .venv preparado."
        echo "  - Recuerda: ejecuta 'source .venv/bin/activate' cuando trabajes."
    else
        echo "  - Saltando creación de entorno virtual."
    fi
else
    echo "[3/4] python3 no encontrado, asumiendo proyecto en C u otro lenguaje."
fi

echo "[4/4] Entorno de desarrollo listo (en lo que respecta al repo)."
echo "Revisa también docs/topologia.md y docs/firewall.md para el entorno de laboratorio."
