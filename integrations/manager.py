"""
Integration manager - coordinates pushing to multiple weather services.
"""
import os
from typing import List, Dict, Any
from datetime import datetime, timezone
from .base import WeatherServiceBase, WeatherData, logger
from .weathercloud import WeathercloudService
from .wunderground import WundergroundService


class IntegrationManager:
    """Manages multiple weather service integrations."""

    def __init__(self):
        self.services: List[WeatherServiceBase] = []
        self._load_services()

    def _load_services(self):
        """Load all configured services."""
        # Load .env manually (no dependency on python-dotenv)
        env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ.setdefault(key.strip(), value.strip())

        # Weathercloud
        if os.getenv("WEATHERCLOUD_ID"):
            self.services.append(WeathercloudService())
            logger.info("Loaded: Weathercloud")

        # Weather Underground
        if os.getenv("WUNDERGROUND_ID"):
            self.services.append(WundergroundService())
            logger.info("Loaded: Weather Underground")

    def push_all(self, data: WeatherData) -> Dict[str, bool]:
        """
        Push data to all enabled services.
        Returns dict of {service_name: success_bool}
        """
        results = {}
        for service in self.services:
            if service.enabled:
                results[service.name] = service.push(data)
        return results

    def push_from_db_record(self, record: Dict[str, Any]) -> Dict[str, bool]:
        """
        Push data from a database record (medicion table format).
        """
        data = WeatherData(
            timestamp=str(record.get('fecha_medicion', '')),
            temp_c=record.get('temp_c'),
            humidity=record.get('humidity'),
            wind_speed_ms=record.get('wind_speed_ms'),
            wind_dir=record.get('wind_dir'),
            gust_ms=record.get('gust_ms'),
            rain_mm=record.get('rain_mm'),
            light_wm2=record.get('light_wm2'),
            uvi=record.get('uvi'),
        )
        return self.push_all(data)


# Singleton instance
_manager = None


def get_manager() -> IntegrationManager:
    """Get or create the singleton integration manager."""
    global _manager
    if _manager is None:
        _manager = IntegrationManager()
    return _manager


def push_weather_data(record: Dict[str, Any]) -> Dict[str, bool]:
    """Convenience function to push a DB record to all services."""
    return get_manager().push_from_db_record(record)
