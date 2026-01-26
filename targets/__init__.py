"""
Módulo de targets para wh2900.
Cada target es un destino donde enviar los datos meteorológicos.
"""
from .base import Target, TargetResult, WeatherRecord

__all__ = [
    'Target',
    'TargetResult',
    'WeatherRecord',
    'get_target_class',
]


def get_target_class(target_type: str):
    """Retorna la clase de target según el tipo (import lazy)."""
    if target_type == 'postgres':
        from .postgres import PostgresTarget
        return PostgresTarget
    elif target_type == 'http_post':
        from .http_service import HttpServiceTarget
        return HttpServiceTarget
    elif target_type == 'curlpost':
        from .curlpost import CurlPostTarget
        return CurlPostTarget
    else:
        raise ValueError(f"Tipo de target desconocido: {target_type}")
