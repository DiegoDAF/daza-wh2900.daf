#!/usr/bin/env python3
"""
WH2900 Processor - Procesa capturas JSON y las envía a múltiples targets.
Configuración via wh2900.ini

Uso: python3 wh2900_processor.py [config.ini]
"""
import os
import sys
import json
import glob
import configparser
from datetime import datetime, timezone
from typing import List, Dict, Optional

from targets import Target, WeatherRecord, TargetResult, get_target_class
from targets.base import logger


# Tipos de paquete conocidos
KNOWN_PACKET_TYPES = {0x13, 0x14, 0x15, 0x16, 0x17}


def decode_packet(data_hex: str) -> Optional[Dict]:
    """Decodifica un paquete WH2900."""
    if len(data_hex) < 16:
        return None

    try:
        b = bytes.fromhex(data_hex)
    except ValueError:
        return None

    if len(b) < 13:
        return None

    packet_type = b[3]

    # Alertar sobre tipos de paquete desconocidos
    if packet_type not in KNOWN_PACKET_TYPES:
        logger.warning(f"TIPO DESCONOCIDO 0x{packet_type:02X} ({packet_type}) - raw: {data_hex}")

    result = {
        'packet_type': packet_type,
        'wind_dir': (b[2] & 0x0F) * 22.5 if len(b) > 2 else None,
    }

    if len(b) >= 13:
        b10_11 = (b[10] << 8) | b[11]
        result['light_wm2'] = b10_11 / 29
        result['uvi'] = (b[12] >> 4) & 0x0F

    if packet_type == 0x13 and len(b) >= 10:
        result['temp_c'] = (b[4] - 10) / 10
        if b[5] >= 128:
            hum = b[5] - 117
        else:
            hum = b[5] + 32
        result['humidity'] = hum if 0 <= hum <= 100 else None
        result['wind_speed_ms'] = b[6] / 10
        result['gust_ms'] = b[7] / 10
        result['rain_mm'] = (b[9] & 0x0F) * 0.1

    if packet_type == 0x14 and len(b) >= 10:
        result['temp_c'] = (b[4] - 10) / 10
        result['wind_speed_ms'] = b[6] / 10
        result['gust_ms'] = b[7] / 10
        result['rain_mm'] = (b[9] & 0x0F) * 0.1

    if packet_type == 0x15 and len(b) >= 10:
        result['temp_c'] = (b[4] + 100) / 10
        hum = b[5] - 10
        result['humidity'] = hum if 0 <= hum <= 100 else None
        result['wind_speed_ms'] = b[6] / 10
        result['gust_ms'] = b[7] / 10
        result['rain_mm'] = (b[9] & 0x0F) * 0.1

    # Tipo 0x16 (22): mismo formato que 0x15
    if packet_type == 0x16 and len(b) >= 10:
        result['temp_c'] = (b[4] + 100) / 10
        hum = b[5] - 10
        result['humidity'] = hum if 0 <= hum <= 100 else None
        result['wind_speed_ms'] = b[6] / 10
        result['gust_ms'] = b[7] / 10
        result['rain_mm'] = (b[9] & 0x0F) * 0.1

    # Tipo 0x17 (23): mismo formato que 0x15/0x16
    if packet_type == 0x17 and len(b) >= 10:
        result['temp_c'] = (b[4] + 100) / 10
        hum = b[5] - 10
        result['humidity'] = hum if 0 <= hum <= 100 else None
        result['wind_speed_ms'] = b[6] / 10
        result['gust_ms'] = b[7] / 10
        result['rain_mm'] = (b[9] & 0x0F) * 0.1

    return result


def process_file(filepath: str) -> Optional[WeatherRecord]:
    """Procesa un archivo JSON y retorna WeatherRecord."""
    try:
        with open(filepath, 'r') as f:
            raw_json = json.load(f)

        filename = os.path.basename(filepath)
        time_str = raw_json.get('time', '')
        raw_data = raw_json.get('rows', [{}])[0].get('data', '')
        rssi = raw_json.get('rssi')

        fecha = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        fecha = fecha.replace(tzinfo=timezone.utc)

        decoded = decode_packet(raw_data) or {}

        return WeatherRecord(
            filepath=filepath,
            filename=filename,
            fecha_medicion=fecha,
            raw_json=raw_json,
            raw_data=raw_data,
            rssi=rssi,
            packet_type=decoded.get('packet_type'),
            temp_c=decoded.get('temp_c'),
            humidity=decoded.get('humidity'),
            wind_dir=decoded.get('wind_dir'),
            wind_speed_ms=decoded.get('wind_speed_ms'),
            gust_ms=decoded.get('gust_ms'),
            rain_mm=decoded.get('rain_mm'),
            light_wm2=decoded.get('light_wm2'),
            uvi=decoded.get('uvi'),
        )

    except Exception as e:
        logger.error(f"Error parsing {filepath}: {e}")
        return None


def load_targets(config: configparser.ConfigParser) -> List[Target]:
    """Carga targets desde la configuración."""
    targets = []

    for section in config.sections():
        if not section.startswith('target_'):
            continue

        target_config = dict(config[section])
        target_type = target_config.get('type', '')
        target_name = section.replace('target_', '')

        try:
            target_class = get_target_class(target_type)
            targets.append(target_class(target_name, target_config))
        except ValueError as e:
            logger.error(f"Error cargando target {target_name}: {e}")

    return targets


def should_delete_file(results: List[TargetResult], policy: str) -> bool:
    """Determina si se debe borrar el archivo según la política."""
    if policy == 'never':
        return False

    active_results = [r for r in results if r.records_processed > 0 or not r.success]

    if not active_results:
        return True  # ningún target activo procesó, OK borrar

    if policy == 'all':
        return all(r.success for r in active_results)
    elif policy == 'any':
        return any(r.success for r in active_results)

    return False


def main():
    # Buscar archivo de configuración
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = os.path.join(os.path.dirname(__file__), 'wh2900.ini')

    if not os.path.exists(config_path):
        logger.error(f"Archivo de configuración no encontrado: {config_path}")
        sys.exit(1)

    # Cargar configuración
    config = configparser.ConfigParser()
    config.read(config_path)

    capture_dir = config.get('general', 'capture_dir', fallback='/var/log/wh2900')
    delete_policy = config.get('general', 'delete_policy', fallback='all')

    # Cargar targets
    targets = load_targets(config)
    active_targets = [t for t in targets if t.active]

    if not active_targets:
        logger.error("No hay targets activos configurados")
        sys.exit(1)

    logger.info(f"Targets activos: {[t.name for t in active_targets]}")

    # Buscar archivos
    pattern = os.path.join(capture_dir, "wh2900_*.json")
    files = glob.glob(pattern)

    if not files:
        return

    logger.info(f"Procesando {len(files)} archivos...")

    # Procesar archivos
    records = []
    for f in files:
        record = process_file(f)
        if record:
            records.append(record)

    logger.info(f"Registros válidos: {len(records)}")

    if not records:
        return

    # Enviar a cada target
    all_results: List[TargetResult] = []
    for target in active_targets:
        result = target.send(records)
        all_results.append(result)
        status = "OK" if result.success else "FAIL"
        logger.info(f"  {target.name}: {status} - {result.message}")

    # Decidir si borrar archivos
    if should_delete_file(all_results, delete_policy):
        deleted = 0
        for record in records:
            try:
                os.remove(record.filepath)
                deleted += 1
            except OSError as e:
                logger.error(f"Error eliminando {record.filepath}: {e}")
        logger.info(f"Archivos eliminados: {deleted}")
    else:
        logger.warning(f"Archivos NO eliminados (política: {delete_policy}, algún target falló)")


if __name__ == "__main__":
    main()
