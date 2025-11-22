#!/usr/bin/env bash
set -e

echo "== Portal cautivo – Commit asistido =="

echo "Tipos disponibles:"
echo "  feat  - nueva funcionalidad"
echo "  fix   - corrección de error"
echo "  docs  - documentación"
echo "  chore - tareas de mantenimiento/refactor"
echo "  test  - pruebas"

read -p "Tipo de commit (feat/fix/docs/chore/test): " type
read -p "Resumen breve (imperativo, sin punto final): " summary
read -p "Número de issue (solo número, ej: 21): " issue

# Sanitizar un poco
type="$(echo "$type" | tr '[:upper:]' '[:lower:]' | xargs)"
summary="$(echo "$summary" | xargs)"
issue="$(echo "$issue" | xargs)"

if [[ -z "$type" || -z "$summary" || -z "$issue" ]]; then
    echo "Error: tipo, resumen e issue son obligatorios."
    exit 1
fi

case "$type" in
    feat|fix|docs|chore|test)
        ;;
    *)
        echo "Error: tipo '$type' no válido. Usa feat/fix/docs/chore/test."
        exit 1
        ;;
esac

message="$type: $summary (#$issue)"

echo
echo "Mensaje de commit generado:"
echo "  $message"
echo

read -p "¿Confirmar y ejecutar 'git commit'? [s/N]: " confirm

if [[ "$confirm" == "s" || "$confirm" == "S" ]]; then
    git commit -m "$message"
else
    echo "Commit cancelado. Si quieres usar el mensaje, cópialo:"
    echo "$message"
fi
