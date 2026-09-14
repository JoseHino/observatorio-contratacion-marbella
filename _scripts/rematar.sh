#!/usr/bin/env bash
# Espera a que terminen la descarga y la primera pasada de extraccion, y
# ejecuta el resto del pipeline de una vez.
set -u
cd "$(dirname "$0")/.."

esperar() {  # $1 = fichero de log, $2 = marca de fin
  until grep -q "$2" "$1" 2>/dev/null; do sleep 15; done
}

echo "[1/5] esperando a que termine la descarga..."
esperar _scripts/download.log "descarga terminada"
echo "      descarga completa: $(ls _raw/*.zip | wc -l) ficheros, $(du -sh _raw | cut -f1)"

echo "[2/5] esperando a que termine la extraccion en curso..."
esperar _scripts/extraccion.log "expedientes unicos"

echo "[3/5] extraccion completa (los ZIP ya barridos salen de cache)..."
python _scripts/extraer_marbella.py 2>&1 | tee _scripts/extraccion.log

echo "[4/5] agregando datos del observatorio..."
python _scripts/build_data.py 2>&1

echo "[5/5] empaquetando el HTML unico..."
python _scripts/empaquetar_html.py 2>&1

echo "== PIPELINE COMPLETO =="
