"""
Target HTTP Service - envía datos a servicios como Weathercloud, Weather Underground, Windguru.
"""
import os
import hashlib
import requests
from datetime import datetime, timezone
from typing import Dict, Optional
from .base import Target, TargetResult, WeatherRecord, logger


class HttpServiceTarget(Target):
    """Target que envía datos a servicios HTTP de clima."""

    target_type = "http_post"
    min_interval_seconds = 600  # 10 minutos por defecto

    def __init__(self, name: str, config: Dict[str, str]):
        super().__init__(name, config)
        self.service = config.get('service', 'weathercloud')
        self.last_push_time: Optional[datetime] = None

        # Cargar credenciales desde env
        self._load_env()
        id_env = config.get('id_env', '')
        key_env = config.get('key_env', '')
        self.service_id = os.getenv(id_env) if id_env else None
        self.service_key = os.getenv(key_env) if key_env else None

        if not self.service_id or not self.service_key:
            logger.warning(f"[{self.name}] Credenciales faltantes ({id_env}, {key_env})")
            self.active = False

    def _load_env(self):
        """Carga variables de entorno desde .env si existe."""
        env_paths = [
            os.path.join(os.path.dirname(__file__), '..', '.env'),
            os.path.join(os.path.dirname(__file__), '..', 'daza-wh2900.daf', '.env'),
        ]
        for env_path in env_paths:
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ.setdefault(key.strip(), value.strip())

    def _can_push(self) -> bool:
        """Verifica si pasó suficiente tiempo desde el último push."""
        if self.last_push_time is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self.last_push_time).total_seconds()
        return elapsed >= self.min_interval_seconds

    def _build_weathercloud_url(self, r: WeatherRecord) -> str:
        """Construye URL para Weathercloud API."""
        parts = [
            "http://api.weathercloud.net/set",
            f"wid/{self.service_id}",
            f"key/{self.service_key}",
        ]

        if r.temp_c is not None:
            parts.append(f"temp/{int(r.temp_c * 10)}")
        if r.humidity is not None:
            parts.append(f"hum/{int(r.humidity)}")
        if r.wind_speed_ms is not None:
            parts.append(f"wspd/{int(r.wind_speed_ms * 10)}")
        if r.wind_dir is not None:
            parts.append(f"wdir/{int(r.wind_dir)}")
        if r.gust_ms is not None:
            parts.append(f"wspdhi/{int(r.gust_ms * 10)}")
        if r.rain_mm is not None:
            parts.append(f"rain/{int(r.rain_mm * 10)}")
        if r.light_wm2 is not None:
            parts.append(f"solarrad/{int(r.light_wm2 * 10)}")
        if r.uvi is not None:
            parts.append(f"uvi/{int(r.uvi)}")

        parts.append("software/daza_wh2900_v1.1")
        return "/".join(parts)

    def _build_wunderground_url(self, r: WeatherRecord) -> str:
        """Construye URL para Weather Underground API."""
        base = "https://weatherstation.wunderground.com/weatherstation/updateweatherstation.php"
        params = [
            f"ID={self.service_id}",
            f"PASSWORD={self.service_key}",
            "action=updateraw",
            f"dateutc={r.fecha_medicion.strftime('%Y-%m-%d+%H:%M:%S')}",
        ]

        if r.temp_c is not None:
            temp_f = r.temp_c * 9/5 + 32
            params.append(f"tempf={temp_f:.1f}")
        if r.humidity is not None:
            params.append(f"humidity={r.humidity}")
        if r.wind_speed_ms is not None:
            wind_mph = r.wind_speed_ms * 2.237
            params.append(f"windspeedmph={wind_mph:.1f}")
        if r.wind_dir is not None:
            params.append(f"winddir={int(r.wind_dir)}")
        if r.gust_ms is not None:
            gust_mph = r.gust_ms * 2.237
            params.append(f"windgustmph={gust_mph:.1f}")
        if r.rain_mm is not None:
            rain_in = r.rain_mm / 25.4
            params.append(f"rainin={rain_in:.2f}")
        if r.uvi is not None:
            params.append(f"UV={r.uvi}")
        if r.light_wm2 is not None:
            params.append(f"solarradiation={r.light_wm2:.1f}")

        params.append("softwaretype=daza_wh2900_v1.1")
        return f"{base}?{'&'.join(params)}"

    def _build_pwsweather_url(self, r: WeatherRecord) -> str:
        """Construye URL para PWSweather API (protocolo compatible con WU)."""
        base = "http://www.pwsweather.com/pwsupdate/pwsupdate.php"
        params = [
            f"ID={self.service_id}",
            f"PASSWORD={self.service_key}",
            "action=updateraw",
            f"dateutc={r.fecha_medicion.strftime('%Y-%m-%d+%H:%M:%S')}",
        ]

        if r.temp_c is not None:
            temp_f = r.temp_c * 9/5 + 32
            params.append(f"tempf={temp_f:.1f}")
        if r.humidity is not None:
            params.append(f"humidity={r.humidity}")
        if r.wind_speed_ms is not None:
            wind_mph = r.wind_speed_ms * 2.237
            params.append(f"windspeedmph={wind_mph:.1f}")
        if r.wind_dir is not None:
            params.append(f"winddir={int(r.wind_dir)}")
        if r.gust_ms is not None:
            gust_mph = r.gust_ms * 2.237
            params.append(f"windgustmph={gust_mph:.1f}")
        if r.rain_mm is not None:
            rain_in = r.rain_mm / 25.4
            params.append(f"rainin={rain_in:.2f}")
        if r.uvi is not None:
            params.append(f"UV={r.uvi}")
        if r.light_wm2 is not None:
            params.append(f"solarradiation={r.light_wm2:.1f}")

        params.append("softwaretype=daza_wh2900_v1.1")
        return f"{base}?{'&'.join(params)}"

    def _build_windguru_url(self, r: WeatherRecord) -> str:
        """Construye URL para Windguru API con autenticación MD5."""
        base = "http://www.windguru.cz/upload/api.php"

        # Salt: timestamp actual
        salt = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')

        # Hash: MD5(salt + uid + password)
        uid = self.service_id  # UID de la estación
        password = self.service_key  # API password
        hash_input = f"{salt}{uid}{password}"
        hash_md5 = hashlib.md5(hash_input.encode()).hexdigest()

        params = [
            f"uid={uid}",
            f"salt={salt}",
            f"hash={hash_md5}",
        ]

        # Viento en knots (1 m/s = 1.94384 knots)
        if r.wind_speed_ms is not None:
            wind_knots = r.wind_speed_ms * 1.94384
            params.append(f"wind_avg={wind_knots:.1f}")
        if r.gust_ms is not None:
            gust_knots = r.gust_ms * 1.94384
            params.append(f"wind_max={gust_knots:.1f}")
        if r.wind_dir is not None:
            params.append(f"wind_direction={int(r.wind_dir)}")

        # Temperatura en Celsius
        if r.temp_c is not None:
            params.append(f"temperature={r.temp_c:.1f}")
        if r.humidity is not None:
            params.append(f"rh={r.humidity}")

        return f"{base}?{'&'.join(params)}"

    def send(self, records: list[WeatherRecord]) -> TargetResult:
        """Envía el registro más reciente al servicio HTTP."""
        if not self.active:
            return TargetResult(
                success=True,
                target_name=self.name,
                message="Target inactivo",
                records_processed=0
            )

        if not records:
            return TargetResult(
                success=True,
                target_name=self.name,
                message="Sin registros",
                records_processed=0
            )

        if not self._can_push():
            return TargetResult(
                success=True,
                target_name=self.name,
                message="Rate limit (esperando)",
                records_processed=0
            )

        # Buscar el registro más reciente con datos completos
        best_record = None
        for r in reversed(records):
            if r.temp_c is not None:
                best_record = r
                break

        if not best_record:
            return TargetResult(
                success=True,
                target_name=self.name,
                message="Sin datos de temperatura",
                records_processed=0
            )

        # Construir URL según el servicio
        if self.service == 'weathercloud':
            url = self._build_weathercloud_url(best_record)
        elif self.service == 'wunderground':
            url = self._build_wunderground_url(best_record)
        elif self.service == 'pwsweather':
            url = self._build_pwsweather_url(best_record)
        elif self.service == 'windguru':
            url = self._build_windguru_url(best_record)
        else:
            return TargetResult(
                success=False,
                target_name=self.name,
                message=f"Servicio desconocido: {self.service}"
            )

        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                self.last_push_time = datetime.now(timezone.utc)
                msg = f"temp={best_record.temp_c}°C, hum={best_record.humidity}%"
                self.log_success(msg)
                return TargetResult(
                    success=True,
                    target_name=self.name,
                    message=msg,
                    records_processed=1
                )
            else:
                msg = f"HTTP {response.status_code}: {response.text[:100]}"
                self.log_error(msg)
                return TargetResult(
                    success=False,
                    target_name=self.name,
                    message=msg
                )

        except requests.RequestException as e:
            self.log_error(str(e))
            return TargetResult(
                success=False,
                target_name=self.name,
                message=str(e)
            )
