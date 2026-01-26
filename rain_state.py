"""
Módulo para calcular lluvia incremental a partir del acumulador total.

El sensor WH2900/Fineoffset-WH65B reporta rain_mm como acumulador total
desde que se instaló. Este módulo guarda el último valor y calcula
la diferencia para obtener lluvia reciente.
"""
import os
import json
from datetime import datetime, timezone
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class RainState:
    """Estado persistente de lluvia."""
    last_rain_mm: float
    last_update: str  # ISO format

    def to_dict(self) -> dict:
        return {
            'last_rain_mm': self.last_rain_mm,
            'last_update': self.last_update
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'RainState':
        return cls(
            last_rain_mm=d.get('last_rain_mm', 0.0),
            last_update=d.get('last_update', '')
        )


class RainCalculator:
    """Calcula lluvia incremental a partir del acumulador total."""

    def __init__(self, state_file: str = '/var/log/wh2900/rain_state.json'):
        self.state_file = state_file
        self._state: Optional[RainState] = None

    def _load_state(self) -> Optional[RainState]:
        """Carga el estado desde el archivo."""
        if self._state is not None:
            return self._state

        if not os.path.exists(self.state_file):
            return None

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                self._state = RainState.from_dict(data)
                return self._state
        except (json.JSONDecodeError, IOError):
            return None

    def _save_state(self, state: RainState):
        """Guarda el estado al archivo."""
        self._state = state
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)
        except (IOError, PermissionError) as e:
            print(f"Warning: no se pudo guardar rain_state: {e}")

    def calculate_rain_delta(self, current_rain_mm: float) -> Tuple[float, bool]:
        """
        Calcula la lluvia incremental.

        Args:
            current_rain_mm: Valor actual del acumulador total

        Returns:
            Tuple[float, bool]: (delta_mm, is_valid)
            - delta_mm: Lluvia desde la última lectura
            - is_valid: True si el delta es confiable
        """
        state = self._load_state()
        now = datetime.now(timezone.utc).isoformat()

        if state is None:
            # Primera ejecución: guardar baseline, no hay delta válido
            self._save_state(RainState(
                last_rain_mm=current_rain_mm,
                last_update=now
            ))
            return 0.0, False

        delta = current_rain_mm - state.last_rain_mm

        # Actualizar estado
        self._save_state(RainState(
            last_rain_mm=current_rain_mm,
            last_update=now
        ))

        if delta < 0:
            # El contador se reinició (cambio de batería, reset, etc.)
            # Retornar 0 y marcar como no válido
            return 0.0, False

        if delta > 100:
            # Delta muy grande (>100mm) - probablemente error de lectura
            # Retornar 0 y marcar como no válido
            return 0.0, False

        return delta, True

    def get_last_rain_mm(self) -> Optional[float]:
        """Retorna el último valor de rain_mm guardado."""
        state = self._load_state()
        return state.last_rain_mm if state else None
