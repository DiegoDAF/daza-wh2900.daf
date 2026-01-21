"""
Base class for weather service integrations.
Each service (Weathercloud, Weather Underground, etc.) extends this.
"""
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DB config (same as wh2900_to_postgres.py, password via ~/.pgpass)
DB_CONFIG = {
    'host': 'beta.tigris-trout.ts.net',
    'port': 55432,
    'dbname': 'clima',
    'user': 'clima',
}


@dataclass
class WeatherData:
    """Standardized weather data for all integrations."""
    timestamp: str
    temp_c: Optional[float] = None
    humidity: Optional[int] = None
    wind_speed_ms: Optional[float] = None
    wind_dir: Optional[float] = None
    gust_ms: Optional[float] = None
    rain_mm: Optional[float] = None
    light_wm2: Optional[float] = None
    uvi: Optional[int] = None
    pressure_hpa: Optional[float] = None  # Not available from WH2900 RF


class WeatherServiceBase(ABC):
    """Abstract base class for weather service integrations."""

    name: str = "base"
    min_interval_seconds: int = 600  # Default 10 minutes

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def _get_db_connection(self):
        """Get a database connection for state persistence."""
        import psycopg2
        return psycopg2.connect(**DB_CONFIG)

    def _load_last_push_time(self) -> Optional[datetime]:
        """Load last push time from database."""
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    select last_push_time from integration_state
                    where service_name = %s
                """, (self.name,))
                row = cur.fetchone()
                conn.close()
                return row[0] if row else None
        except Exception as e:
            logger.debug(f"[{self.name}] Error loading last push time: {e}")
            return None

    def _save_push_state(self, status: str = 'ok', error: str = None):
        """Save push state to database."""
        try:
            conn = self._get_db_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    insert into integration_state (service_name, last_push_time, last_status, last_error, push_count)
                    values (%s, now(), %s, %s, 1)
                    on conflict (service_name) do update set
                        last_push_time = now(),
                        last_status = excluded.last_status,
                        last_error = excluded.last_error,
                        push_count = integration_state.push_count + 1,
                        updated_at = now()
                """, (self.name, status, error))
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"[{self.name}] Error saving push state: {e}")

    @abstractmethod
    def build_url(self, data: WeatherData) -> str:
        """Build the API URL with weather data parameters."""
        pass

    @abstractmethod
    def push(self, data: WeatherData) -> bool:
        """Push weather data to the service. Returns True on success."""
        pass

    def can_push(self) -> bool:
        """Check if enough time has passed since last push."""
        if not self.enabled:
            return False
        last_push = self._load_last_push_time()
        if last_push is None:
            return True
        now = datetime.now(timezone.utc)
        # Ensure last_push is timezone-aware
        if last_push.tzinfo is None:
            last_push = last_push.replace(tzinfo=timezone.utc)
        elapsed = (now - last_push).total_seconds()
        return elapsed >= self.min_interval_seconds

    def log_success(self, data: WeatherData):
        logger.info(f"[{self.name}] Push OK: temp={data.temp_c}C, hum={data.humidity}%")

    def log_error(self, error: str):
        logger.error(f"[{self.name}] Push FAILED: {error}")
