"""
Target CurlPost - envía datos a un webhook genérico via POST.
"""
import os
import json
import requests
from typing import Dict
from .base import Target, TargetResult, WeatherRecord, logger


class CurlPostTarget(Target):
    """Target que envía datos via HTTP POST a un webhook."""

    target_type = "curlpost"

    def __init__(self, name: str, config: Dict[str, str]):
        super().__init__(name, config)
        self.url = config.get('url', '')
        self.method = config.get('method', 'POST').upper()

        # API key desde env o config
        api_key_env = config.get('api_key_env', '')
        self.api_key = os.getenv(api_key_env) if api_key_env else config.get('api_key', '')

        if not self.url:
            logger.warning(f"[{self.name}] URL no configurada")
            self.active = False

    def _build_payload(self, r: WeatherRecord) -> Dict:
        """Construye el payload JSON para el webhook."""
        return {
            'timestamp': r.fecha_medicion.isoformat(),
            'filename': r.filename,
            'temp_c': r.temp_c,
            'humidity': r.humidity,
            'wind_dir': r.wind_dir,
            'wind_speed_ms': r.wind_speed_ms,
            'gust_ms': r.gust_ms,
            'rain_mm': r.rain_mm,
            'light_wm2': r.light_wm2,
            'uvi': r.uvi,
            'rssi': r.rssi,
            'packet_type': r.packet_type,
        }

    def send(self, records: list[WeatherRecord]) -> TargetResult:
        """Envía los registros al webhook."""
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

        # Buscar el registro más reciente con datos
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

        payload = self._build_payload(best_record)
        headers = {'Content-Type': 'application/json'}

        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        try:
            if self.method == 'POST':
                response = requests.post(
                    self.url,
                    json=payload,
                    headers=headers,
                    timeout=30
                )
            else:
                response = requests.get(
                    self.url,
                    params=payload,
                    headers=headers,
                    timeout=30
                )

            if response.status_code in (200, 201, 202, 204):
                msg = f"HTTP {response.status_code}"
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
