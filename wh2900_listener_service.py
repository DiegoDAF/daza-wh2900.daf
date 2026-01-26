#!/usr/bin/env python3
"""
WH2900 Listener Service - Captura datos RF via rtl_433 y guarda JSON individuales.
Diseñado para correr como servicio systemd con reinicio automático.
"""
import os
import sys
import json
import subprocess
from datetime import datetime

CAPTURE_DIR = "/var/log/wh2900"
RTL_433_CMD = [
    "rtl_433",
    "-d", "driver=Cariboulite",
    "-f", "433920000",
    "-s", "2000000",  # 2MHz sample rate - CRÍTICO para CaribouLite
    "-g", "55",
    "-M", "level",
    "-M", "time:utc",
    "-Y", "autolevel",
    "-Y", "magest",
    "-F", "json",  # Usar todos los decoders por defecto
]


def log(msg: str):
    """Log con timestamp."""
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}", flush=True)


def main():
    # Crear directorio si no existe
    os.makedirs(CAPTURE_DIR, exist_ok=True)

    log("Iniciando rtl_433 listener...")
    log(f"Comando: {' '.join(RTL_433_CMD)}")

    # Ejecutar rtl_433 y leer stdout línea por línea
    process = subprocess.Popen(
        RTL_433_CMD,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    log(f"rtl_433 iniciado con PID {process.pid}")

    try:
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            # Intentar parsear como JSON
            try:
                data = json.loads(line)

                # Generar nombre de archivo único
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Agregar microsegundos para evitar colisiones
                usec = datetime.now().strftime("%f")[:3]
                filename = f"wh2900_{timestamp}_{usec}.json"
                filepath = os.path.join(CAPTURE_DIR, filename)

                # Guardar JSON
                with open(filepath, 'w') as f:
                    json.dump(data, f)

                # Log breve
                rssi = data.get('rssi', 'N/A')
                bits = data.get('len', data.get('bits', 'N/A'))
                log(f"Captura: {filename} (RSSI: {rssi}, bits: {bits})")

            except json.JSONDecodeError:
                # No es JSON, probablemente mensaje de rtl_433
                if "Found" in line or "Tuned" in line or "Exact" in line:
                    log(f"rtl_433: {line}")

    except KeyboardInterrupt:
        log("Interrumpido por usuario")
    finally:
        process.terminate()
        process.wait()
        log("rtl_433 terminado")


if __name__ == "__main__":
    main()
