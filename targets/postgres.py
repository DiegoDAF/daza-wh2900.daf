"""
Target PostgreSQL - inserta datos en la base de datos.
"""
import psycopg2
from psycopg2.extras import Json
from typing import Dict
from .base import Target, TargetResult, WeatherRecord, logger


class PostgresTarget(Target):
    """Target que inserta datos en PostgreSQL."""

    target_type = "postgres"

    def __init__(self, name: str, config: Dict[str, str]):
        super().__init__(name, config)
        self.db_config = {
            'host': config.get('host', 'localhost'),
            'port': int(config.get('port', 5432)),
            'dbname': config.get('dbname', 'clima'),
            'user': config.get('user', 'clima'),
        }
        if config.get('password'):
            self.db_config['password'] = config['password']

    def send(self, records: list[WeatherRecord]) -> TargetResult:
        """Inserta registros en PostgreSQL."""
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

        try:
            conn = psycopg2.connect(**self.db_config)
        except Exception as e:
            self.log_error(f"Error conexión: {e}")
            return TargetResult(
                success=False,
                target_name=self.name,
                message=f"Error conexión: {e}"
            )

        inserted_medicion = 0
        inserted_dataraw = 0

        try:
            with conn.cursor() as cur:
                for r in records:
                    try:
                        # Insertar en dataraw (siempre)
                        cur.execute("""
                            insert into dataraw (filename, data)
                            values (%s, %s)
                            on conflict (filename) do nothing
                        """, (r.filename, Json(r.raw_json)))
                        if cur.rowcount > 0:
                            inserted_dataraw += 1

                        # Insertar en medicion (si tiene datos decodificados)
                        if r.packet_type is not None:
                            cur.execute("""
                                insert into medicion (
                                    filename, fecha_medicion, packet_type, temp_c, humidity,
                                    wind_dir, wind_speed_ms, gust_ms, light_wm2, uvi, rain_mm,
                                    rssi, raw_data
                                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                on conflict (filename) do nothing
                            """, (
                                r.filename, r.fecha_medicion, r.packet_type,
                                r.temp_c, r.humidity, r.wind_dir,
                                r.wind_speed_ms, r.gust_ms, r.light_wm2,
                                r.uvi, r.rain_mm, r.rssi, r.raw_data
                            ))
                            if cur.rowcount > 0:
                                inserted_medicion += 1

                        conn.commit()

                    except Exception as e:
                        conn.rollback()
                        self.log_error(f"Error insertando {r.filename}: {e}")

            conn.close()
            msg = f"medicion: {inserted_medicion}, dataraw: {inserted_dataraw}"
            self.log_success(msg)
            return TargetResult(
                success=True,
                target_name=self.name,
                message=msg,
                records_processed=inserted_medicion
            )

        except Exception as e:
            conn.close()
            self.log_error(f"Error general: {e}")
            return TargetResult(
                success=False,
                target_name=self.name,
                message=str(e)
            )
