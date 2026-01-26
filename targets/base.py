"""
Clase base para targets de wh2900.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import os

LOG_DIR = os.environ.get('WH2900_LOG_DIR', '/var/log/wh2900')
LOG_FORMAT = '%(asctime)s %(levelname)s %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """Crea un logger que escribe a archivo y stdout."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Handler a archivo
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(LOG_DIR, log_file))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (PermissionError, OSError):
        pass  # Sin permisos para escribir logs

    # Handler a stdout
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S'))
    logger.addHandler(stream_handler)

    return logger


# Logger general
logger = setup_logger('wh2900', 'processor.log')


@dataclass
class WeatherRecord:
    """Datos meteorológicos decodificados de un paquete WH2900."""
    filepath: str
    filename: str
    fecha_medicion: datetime
    raw_json: Dict[str, Any]
    raw_data: str
    rssi: Optional[float] = None
    packet_type: Optional[int] = None
    temp_c: Optional[float] = None
    humidity: Optional[int] = None
    wind_dir: Optional[float] = None
    wind_speed_ms: Optional[float] = None
    gust_ms: Optional[float] = None
    rain_mm: Optional[float] = None
    light_wm2: Optional[float] = None
    uvi: Optional[int] = None


@dataclass
class TargetResult:
    """Resultado de enviar datos a un target."""
    success: bool
    target_name: str
    message: str = ""
    records_processed: int = 0


class Target(ABC):
    """Clase base abstracta para todos los targets."""

    name: str = "base"
    target_type: str = "base"

    def __init__(self, name: str, config: Dict[str, str]):
        self.name = name
        self.config = config
        self.active = config.get('active', 'true').lower() == 'true'
        # Logger específico para este target
        self._logger = setup_logger(f'wh2900.{name}', f'target_{name}.log')

    @abstractmethod
    def send(self, records: list[WeatherRecord]) -> TargetResult:
        """
        Envía los registros al target.
        Retorna TargetResult con el resultado.
        """
        pass

    def log_success(self, msg: str):
        self._logger.info(f"[{self.name}] {msg}")
        logger.info(f"[{self.name}] {msg}")

    def log_error(self, msg: str):
        self._logger.error(f"[{self.name}] {msg}")
        logger.error(f"[{self.name}] {msg}")

    def log_debug(self, msg: str):
        self._logger.debug(f"[{self.name}] {msg}")
