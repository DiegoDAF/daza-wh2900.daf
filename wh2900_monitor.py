#!/usr/bin/env python3
"""
WH2900 Monitor - Verifica que las estaciones estén online en servicios externos.
Envía alerta por email si alguna está offline.

Uso: python3 wh2900_monitor.py [config.ini]
"""
import os
import sys
import configparser
import subprocess
import requests
from datetime import datetime, timedelta

# Configuración
ALERT_EMAIL = "clima@daf.ar"
STATE_FILE = "/var/log/wh2900/monitor_state.txt"
LOG_FILE = "/var/log/wh2900/monitor.log"


def log(msg: str):
    """Log a archivo y stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + "\n")
    except:
        pass


def send_alert(subject: str, body: str):
    """Envía alerta por email usando mutt (como usuario daf)."""
    try:
        # Ejecutar como usuario daf para usar su config de mutt
        proc = subprocess.run(
            ['sudo', '-u', 'daf', 'mutt', '-s', subject, ALERT_EMAIL],
            input=body.encode(),
            capture_output=True,
            timeout=30
        )
        if proc.returncode == 0:
            log(f"ALERT enviada: {subject}")
        else:
            log(f"ERROR enviando alert: {proc.stderr.decode()}")
    except Exception as e:
        log(f"ERROR enviando alert: {e}")


def check_weathercloud(device_id: str) -> tuple[bool, str]:
    """
    Verifica si la estación está online en Weathercloud.
    Retorna (online, mensaje)
    """
    # Usar la página del dispositivo y extraer epoch del meta tag
    url = f"https://app.weathercloud.net/d{device_id}"
    try:
        resp = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; WH2900-Monitor/1.0)'
        })
        if resp.status_code == 200:
            # Buscar meta tag epoch
            import re
            match = re.search(r'content="(\d+)".*?epoch', resp.text) or \
                    re.search(r'epoch.*?content="(\d+)"', resp.text)
            if match:
                epoch = int(match.group(1))
                last_update = datetime.fromtimestamp(epoch)
                age = datetime.now() - last_update
                if age < timedelta(minutes=30):
                    return True, f"Online, última actualización hace {int(age.total_seconds()/60)} min"
                else:
                    return False, f"OFFLINE, última actualización hace {int(age.total_seconds()/60)} min"
            return True, "Online (sin timestamp)"
        else:
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, f"Error: {e}"


def check_postgres(host: str, port: int, dbname: str, user: str) -> tuple[bool, str]:
    """
    Verifica si PostgreSQL está accesible.
    Retorna (online, mensaje)
    """
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            connect_timeout=10
        )
        cur = conn.cursor()
        cur.execute("SELECT 1")
        conn.close()
        return True, "Online"
    except Exception as e:
        return False, f"Error: {e}"


def check_pwsweather(station_id: str) -> tuple[bool, str]:
    """
    Verifica si la estación está online en PWSweather.
    Retorna (online, mensaje)
    """
    url = f"https://www.pwsweather.com/station/pws/{station_id}"
    try:
        resp = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; WH2900-Monitor/1.0)'
        })
        if resp.status_code == 200:
            # Buscar última actualización en el HTML
            import re
            # PWSweather muestra "Last Updated: ..." en la página
            if 'Last Updated' in resp.text or station_id in resp.text:
                return True, "Online (página accesible)"
            return False, "Estación no encontrada en página"
        else:
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, f"Error: {e}"


def check_wunderground(station_id: str) -> tuple[bool, str]:
    """
    Verifica si la estación está online en Weather Underground.
    Retorna (online, mensaje)
    """
    url = f"https://api.weather.com/v2/pws/observations/current?stationId={station_id}&format=json&units=m&apiKey=6532d6454b8aa370768e63d6ba5a832e"
    try:
        resp = requests.get(url, timeout=30, headers={
            'User-Agent': 'WH2900-Monitor/1.0'
        })
        if resp.status_code == 200:
            data = resp.json()
            if 'observations' in data and len(data['observations']) > 0:
                obs = data['observations'][0]
                obs_time = obs.get('obsTimeLocal', '')
                return True, f"Online, última obs: {obs_time}"
            return False, "Sin observaciones"
        elif resp.status_code == 204:
            return False, "Estación no encontrada o sin datos"
        else:
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, f"Error: {e}"


def load_state() -> dict:
    """Carga estado previo de alertas."""
    state = {}
    try:
        with open(STATE_FILE, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    state[key] = value
    except:
        pass
    return state


def save_state(state: dict):
    """Guarda estado de alertas."""
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            for key, value in state.items():
                f.write(f"{key}={value}\n")
    except:
        pass


def main():
    # Cargar .env
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

    # Cargar config INI para URLs de checkeo
    ini_path = os.path.join(os.path.dirname(__file__), 'wh2900.ini')
    config = configparser.ConfigParser()
    config.read(ini_path)

    weathercloud_url = config.get('target_weathercloud', 'check_url', fallback=None)
    wunderground_url = config.get('target_wunderground', 'check_url', fallback=None)
    pwsweather_url = config.get('target_pwsweather', 'check_url', fallback=None)

    # Extraer IDs de las URLs
    weathercloud_id = None
    wunderground_id = None
    pwsweather_id = None

    if weathercloud_url:
        import re
        match = re.search(r'/d(\d+)', weathercloud_url)
        if match:
            weathercloud_id = match.group(1)

    if wunderground_url:
        import re
        match = re.search(r'/pws/(\w+)', wunderground_url)
        if match:
            wunderground_id = match.group(1)

    if pwsweather_url:
        import re
        match = re.search(r'/pws/(\w+)', pwsweather_url)
        if match:
            pwsweather_id = match.group(1)

    # Cargar config de PostgreSQL
    db_host = config.get('target_db', 'host', fallback=None)
    db_port = config.getint('target_db', 'port', fallback=5432)
    db_name = config.get('target_db', 'dbname', fallback=None)
    db_user = config.get('target_db', 'user', fallback=None)
    db_active = config.getboolean('target_db', 'active', fallback=False)

    state = load_state()
    alerts = []

    # Check PostgreSQL
    if db_active and db_host:
        online, msg = check_postgres(db_host, db_port, db_name, db_user)
        log(f"PostgreSQL ({db_host}): {msg}")
        if not online:
            if state.get('postgres_alert') != 'sent':
                alerts.append(f"PostgreSQL OFFLINE ({db_host}): {msg}")
                state['postgres_alert'] = 'sent'
        else:
            state['postgres_alert'] = ''

    # Check Weathercloud
    if weathercloud_id:
        online, msg = check_weathercloud(weathercloud_id)
        log(f"Weathercloud: {msg}")
        if not online:
            if state.get('weathercloud_alert') != 'sent':
                alerts.append(f"Weathercloud OFFLINE: {msg}")
                state['weathercloud_alert'] = 'sent'
        else:
            state['weathercloud_alert'] = ''

    # Check Weather Underground
    if wunderground_id:
        online, msg = check_wunderground(wunderground_id)
        log(f"Wunderground: {msg}")
        if not online:
            if state.get('wunderground_alert') != 'sent':
                alerts.append(f"Weather Underground OFFLINE: {msg}")
                state['wunderground_alert'] = 'sent'
        else:
            state['wunderground_alert'] = ''

    # Check PWSweather
    if pwsweather_id:
        online, msg = check_pwsweather(pwsweather_id)
        log(f"PWSweather: {msg}")
        if not online:
            if state.get('pwsweather_alert') != 'sent':
                alerts.append(f"PWSweather OFFLINE: {msg}")
                state['pwsweather_alert'] = 'sent'
        else:
            state['pwsweather_alert'] = ''

    # Enviar alertas
    if alerts:
        body = "WH2900 Monitor - Alertas:\n\n" + "\n".join(alerts)
        body += f"\n\nTimestamp: {datetime.now()}"
        send_alert("WH2900 ALERTA - Estación offline", body)

    save_state(state)
    log("Monitor check completado")


if __name__ == "__main__":
    main()
