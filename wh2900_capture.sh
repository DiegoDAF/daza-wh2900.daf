#!/bin/bash
# WH2900 Capture Service - Escucha y guarda cada paquete en JSON separado
# Uso: bash wh2900_capture.sh

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
RESTART_LOG="/var/log/wh2900/restarts.log"

log() {
    echo "$(date -u +%Y-%m-%d_%H:%M:%S) - $1" >> "$RESTART_LOG"
    echo "$(date +%H:%M:%S) $1"
}

log "Iniciando WH2900 Capture Service"

while true; do
    log "Iniciando rtl_433..."

    rtl_433 -d "driver=Cariboulite" -f 433920000 -g 69 \
        -M level -M time:utc \
        -Y autolevel -Y magest \
        -X "n=wh2900,m=FSK_PCM,s=310,l=310,r=3000,preamble=5555516ea1,bits>=80" \
        -F json 2>/dev/null | python3 "$SCRIPT_DIR/wh2900_listener.py"

    log "rtl_433 terminado, reiniciando en 5s..."
    sleep 5
done
