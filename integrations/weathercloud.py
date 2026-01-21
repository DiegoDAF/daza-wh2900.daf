"""
Weathercloud integration.
API docs: https://weathercloud.net/en/faq (request via email)
Rate limit: 10 minutes (free), 1 minute (Pro/Premium)

URL format: http://api.weathercloud.net/set/wid/{ID}/key/{KEY}/temp/{T}/hum/{H}/...
Values: temp, dew, bar, solarrad are multiplied by 10
"""
import os
import requests
from typing import Optional
from .base import WeatherServiceBase, WeatherData, logger


class WeathercloudService(WeatherServiceBase):
    """Weathercloud.net integration."""

    name = "weathercloud"
    base_url = "http://api.weathercloud.net/set"
    min_interval_seconds = 600  # 10 minutes for free accounts

    def __init__(self, wid: Optional[str] = None, key: Optional[str] = None, enabled: bool = True):
        super().__init__(enabled)
        self.wid = wid or os.getenv("WEATHERCLOUD_ID")
        self.key = key or os.getenv("WEATHERCLOUD_KEY")

        if not self.wid or not self.key:
            logger.warning(f"[{self.name}] Missing credentials, disabling")
            self.enabled = False

    def build_url(self, data: WeatherData) -> str:
        """
        Build Weathercloud API URL.

        Parameter reference:
        - temp: temperature in tenths of °C (multiply by 10)
        - hum: humidity %
        - wspd: wind speed in tenths of m/s (multiply by 10)
        - wdir: wind direction 0-359
        - wspdhi: wind gust in tenths of m/s
        - rain: rain today in tenths of mm (multiply by 10)
        - solarrad: solar radiation in tenths of W/m² (multiply by 10)
        - uvi: UV index (0-15)
        """
        parts = [
            f"{self.base_url}",
            f"wid/{self.wid}",
            f"key/{self.key}",
        ]

        # Add available parameters (multiply by 10 where needed)
        if data.temp_c is not None:
            parts.append(f"temp/{int(data.temp_c * 10)}")

        if data.humidity is not None:
            parts.append(f"hum/{int(data.humidity)}")

        if data.wind_speed_ms is not None:
            parts.append(f"wspd/{int(data.wind_speed_ms * 10)}")

        if data.wind_dir is not None:
            parts.append(f"wdir/{int(data.wind_dir)}")

        if data.gust_ms is not None:
            parts.append(f"wspdhi/{int(data.gust_ms * 10)}")

        if data.rain_mm is not None:
            parts.append(f"rain/{int(data.rain_mm * 10)}")

        if data.light_wm2 is not None:
            parts.append(f"solarrad/{int(data.light_wm2 * 10)}")

        if data.uvi is not None:
            parts.append(f"uvi/{int(data.uvi)}")

        # Software identifier (no spaces)
        parts.append("software/daza_wh2900_v1.0")

        return "/".join(parts)

    def push(self, data: WeatherData) -> bool:
        """Push weather data to Weathercloud."""
        if not self.can_push():
            logger.debug(f"[{self.name}] Skipping push (rate limit)")
            return False

        url = self.build_url(data)

        try:
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                self._save_push_state(status='ok')
                self.log_success(data)
                return True
            else:
                self._save_push_state(status='error', error=f"HTTP {response.status_code}: {response.text}")
                self.log_error(f"HTTP {response.status_code}: {response.text}")
                return False

        except requests.RequestException as e:
            self._save_push_state(status='error', error=str(e))
            self.log_error(str(e))
            return False


# Convenience function for quick testing
def push_to_weathercloud(data: WeatherData) -> bool:
    """One-shot push to Weathercloud."""
    service = WeathercloudService()
    return service.push(data)


if __name__ == "__main__":
    # Test with sample data
    from dotenv import load_dotenv
    load_dotenv()

    test_data = WeatherData(
        timestamp="2026-01-21T16:00:00Z",
        temp_c=25.5,
        humidity=45,
        wind_speed_ms=3.2,
        wind_dir=180,
        gust_ms=5.1,
        rain_mm=0.0,
        light_wm2=850.0,
        uvi=7
    )

    service = WeathercloudService()
    print(f"URL: {service.build_url(test_data)}")
    # Uncomment to actually push:
    # service.push(test_data)
