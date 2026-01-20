#!/usr/bin/env python3
"""
WH2900 Listener - Guarda cada captura en un JSON separado
Uso: rtl_433 ... | python3 wh2900_listener.py
"""
import sys
import json
import os
from datetime import datetime

CAPTURE_DIR = "/var/log/wh2900"

def main():
    os.makedirs(CAPTURE_DIR, exist_ok=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            data = json.loads(line)

            # Generar nombre de archivo con timestamp
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"{CAPTURE_DIR}/wh2900_{ts}.json"

            # Guardar JSON
            with open(filename, 'w') as f:
                json.dump(data, f)

            # Log a stdout para monitoreo
            pkt_data = data.get('rows', [{}])[0].get('data', '')[:20]
            rssi = data.get('rssi', '?')
            print(f"{ts} rssi={rssi} data={pkt_data}...")
            sys.stdout.flush()

        except json.JSONDecodeError:
            pass  # Ignorar lineas que no son JSON
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
