"""
Weather Underground PWS integration.
API docs: https://support.weather.com/s/article/PWS-Upload-Protocol
Rate limit: No specific limit documented, but recommended ~1 minute intervals

URL format: https://rtupdate.wunderground.com/weatherstation/updateweatherstation.php
Units: Imperial (Fahrenheit, mph, inches)
"""
import os
import requests
from urllib.parse import urlencode
from typing import Optional
from .base import WeatherServiceBase, WeatherData, logger


class WundergroundService(WeatherServiceBase):
    """Weather Underground PWS integration."""

    name = "wunderground"
    base_url = "https://rtupdate.wunderground.com/weatherstation/updateweatherstation.php"
    min_interval_seconds = 60  # 1 minute recommended

    def __init__(self, station_id: Optional[str] = None, station_key: Optional[str] = None, enabled: bool = True):
        super().__init__(enabled)
        self.station_id = station_id or os.getenv("WUNDERGROUND_ID")
        self.station_key = station_key or os.getenv("WUNDERGROUND_KEY")

        if not self.station_id or not self.station_key:
            logger.warning(f"[{self.name}] Missing credentials, disabling")
            self.enabled = False

    @staticmethod
    def celsius_to_fahrenheit(c: float) -> float:
        """Convert Celsius to Fahrenheit."""
        return (c * 9/5) + 32

    @staticmethod
    def ms_to_mph(ms: float) -> float:
        """Convert m/s to mph."""
        return ms * 2.23694

    @staticmethod
    def mm_to_inches(mm: float) -> float:
        """Convert mm to inches."""
        return mm * 0.0393701

    def build_url(self, data: WeatherData) -> str:
        """
        Build Weather Underground API URL.

        Parameter reference (all imperial units):
        - ID: station ID
        - PASSWORD: station key
        - action: updateraw
        - dateutc: now (or YYYY-MM-DD HH:MM:SS)
        - tempf: temperature in Fahrenheit
        - humidity: humidity %
        - winddir: wind direction 0-360
        - windspeedmph: wind speed in mph
        - windgustmph: wind gust in mph
        - rainin: rain in last hour (inches)
        - dailyrainin: daily rain total (inches)
        - solarradiation: solar radiation W/m2
        - UV: UV index
        - softwaretype: software identifier
        """
        params = {
            'ID': self.station_id,
            'PASSWORD': self.station_key,
            'action': 'updateraw',
            'dateutc': 'now',
        }

        # Temperature (convert C to F)
        if data.temp_c is not None:
            params['tempf'] = f"{self.celsius_to_fahrenheit(data.temp_c):.1f}"

        # Humidity (same unit)
        if data.humidity is not None:
            params['humidity'] = str(int(data.humidity))

        # Wind direction (same unit)
        if data.wind_dir is not None:
            params['winddir'] = str(int(data.wind_dir))

        # Wind speed (convert m/s to mph)
        if data.wind_speed_ms is not None:
            params['windspeedmph'] = f"{self.ms_to_mph(data.wind_speed_ms):.1f}"

        # Wind gust (convert m/s to mph)
        if data.gust_ms is not None:
            params['windgustmph'] = f"{self.ms_to_mph(data.gust_ms):.1f}"

        # Rain (convert mm to inches)
        if data.rain_mm is not None:
            params['rainin'] = f"{self.mm_to_inches(data.rain_mm):.3f}"
            params['dailyrainin'] = f"{self.mm_to_inches(data.rain_mm):.3f}"  # TODO: accumulate daily

        # Solar radiation (same unit - W/m2)
        if data.light_wm2 is not None:
            params['solarradiation'] = f"{data.light_wm2:.1f}"

        # UV index (same unit)
        if data.uvi is not None:
            params['UV'] = str(int(data.uvi))

        # Software identifier
        params['softwaretype'] = 'daza_wh2900_v1.0'

        return f"{self.base_url}?{urlencode(params)}"

    def push(self, data: WeatherData) -> bool:
        """Push weather data to Weather Underground."""
        if not self.can_push():
            logger.debug(f"[{self.name}] Skipping push (rate limit)")
            return False

        url = self.build_url(data)

        try:
            response = requests.get(url, timeout=30)

            # WU returns "success" on successful upload
            if response.status_code == 200 and 'success' in response.text.lower():
                self._save_push_state(status='ok')
                self.log_success(data)
                return True
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                self._save_push_state(status='error', error=error_msg)
                self.log_error(error_msg)
                return False

        except requests.RequestException as e:
            self._save_push_state(status='error', error=str(e))
            self.log_error(str(e))
            return False


# Convenience function for quick testing
def push_to_wunderground(data: WeatherData) -> bool:
    """One-shot push to Weather Underground."""
    service = WundergroundService()
    return service.push(data)


if __name__ == "__main__":
    # Test with sample data
    from dotenv import load_dotenv
    load_dotenv()

    test_data = WeatherData(
        timestamp="2026-01-21T18:00:00Z",
        temp_c=25.5,
        humidity=45,
        wind_speed_ms=3.2,
        wind_dir=180,
        gust_ms=5.1,
        rain_mm=0.0,
        light_wm2=850.0,
        uvi=7
    )

    service = WundergroundService()
    print(f"Enabled: {service.enabled}")
    if service.enabled:
        print(f"URL: {service.build_url(test_data)}")
        # Uncomment to actually push:
        # service.push(test_data)
