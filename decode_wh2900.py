#!/usr/bin/env python3
"""Decodificador de paquetes WH2900 capturados por rtl_433"""
import sys
import json
from datetime import datetime, timezone

def utc_to_local(utc_str):
    """Convierte tiempo UTC de rtl_433 a hora local"""
    utc_dt = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S")
    utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    local_dt = utc_dt.astimezone()
    return local_dt.strftime("%H:%M:%S")

def decode_packet(data_hex):
    """Decodifica un paquete WH2900 tipo 0x13"""
    b = bytes.fromhex(data_hex)

    if len(b) < 18:
        return None

    # Solo procesar paquetes tipo 0x13 (datos meteorológicos)
    if b[3] != 0x13:
        return None

    b10_11 = (b[10] << 8) | b[11]

    result = {
        'temp_c': (b[4] - 10) / 10,           # Confirmado ✓
        'humidity': b[5] - 117,                # Confirmado ✓
        'wind_dir': (b[2] & 0x0F) * 22.5,     # Confirmado ✓
        'wind_speed_ms': b[6] / 10,           # Variable, parece correcto
        'gust_ms': b[7] / 10,                 # Pendiente verificar
        'uvi': (b[12] >> 4) & 0x0F,           # Confirmado ✓
        'light_wm2': b10_11 / 29,             # Confirmado ✓ (decrece al atardecer)
        'rain_mm': (b[9] & 0x0F) * 0.1,       # Confirmado ✓ (nibble bajo, siempre 0)
        # Presión: no encontrada en paquetes tipo 0x13
    }

    return result

def main():
    print("Decodificador WH2900 - Esperando datos de stdin...")
    print("Uso: tail -f wh2900_capture.json | python3 decode_wh2900.py")
    print("-" * 60)

    for line in sys.stdin:
        try:
            j = json.loads(line.strip())
            data = j['rows'][0]['data']
            time_local = utc_to_local(j['time'])

            result = decode_packet(data)
            if result:
                print(f"{time_local} | "
                      f"T:{result['temp_c']:5.1f}°C | "
                      f"H:{result['humidity']:3d}% | "
                      f"W:{result['wind_dir']:5.1f}°/{result['wind_speed_ms']:4.1f}m/s | "
                      f"L:{result['light_wm2']:5.0f}W/m² | "
                      f"UV:{result['uvi']} | "
                      f"R:{result['rain_mm']:.1f}mm")
        except Exception as e:
            pass

if __name__ == "__main__":
    main()
