"""Utilidades de zona horaria para America/Santiago."""
import datetime as dt
from functools import lru_cache

import pytz
from dateutil import tz

from ..config import settings

# Timezone objects cacheados
_SANTIAGO_TZ = pytz.timezone("America/Santiago")
_UTC_TZ = pytz.UTC


@lru_cache(maxsize=1)
def get_santiago_tz() -> pytz.BaseTzInfo:
    """Retorna el timezone de America/Santiago (cacheado)."""
    return _SANTIAGO_TZ


@lru_cache(maxsize=1)
def get_utc_tz() -> pytz.BaseTzInfo:
    """Retorna UTC (cacheado)."""
    return _UTC_TZ


def now_santiago() -> dt.datetime:
    """Retorna datetime.now en America/Santiago (aware)."""
    return dt.datetime.now(get_santiago_tz())


def now_utc() -> dt.datetime:
    """Retorna datetime.now en UTC (aware)."""
    return dt.datetime.now(_UTC_TZ)


def to_santiago(dt_value: dt.datetime) -> dt.datetime:
    """Convierte un datetime a America/Santiago.
    
    Si es naive, asume UTC.
    """
    if dt_value.tzinfo is None:
        dt_value = _UTC_TZ.localize(dt_value)
    return dt_value.astimezone(get_santiago_tz())


def to_utc(dt_value: dt.datetime) -> dt.datetime:
    """Convierte un datetime a UTC.
    
    Si es naive, asume UTC.
    """
    if dt_value.tzinfo is None:
        dt_value = _UTC_TZ.localize(dt_value)
    return dt_value.astimezone(_UTC_TZ)


def santiago_date(dt_value: dt.datetime) -> dt.date:
    """Extrae la fecha en zona horaria de Santiago."""
    return to_santiago(dt_value).date()


def santiago_time(dt_value: dt.datetime) -> dt.time:
    """Extrae la hora en zona horaria de Santiago."""
    return to_santiago(dt_value).time()


def combine_santiago(date: dt.date, time: dt.time) -> dt.datetime:
    """Combina date + time en America/Santiago (aware)."""
    naive = dt.datetime.combine(date, time)
    return get_santiago_tz().localize(naive)


def format_santiago(dt_value: dt.datetime, fmt: str = "%d/%m/%Y %H:%M") -> str:
    """Formatea datetime en zona horaria de Santiago."""
    return to_santiago(dt_value).strftime(fmt)


def parse_santiago_datetime(date_str: str, time_str: str) -> dt.datetime:
    """Parsea fecha y hora en formato dd/mm/yyyy HH:MM a datetime aware en Santiago."""
    naive = dt.datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
    return get_santiago_tz().localize(naive)


def is_business_hours(dt_value: dt.datetime, start_hour: int = 9, end_hour: int = 19) -> bool:
    """Verifica si un datetime está en horario hábil (por defecto 9-19)."""
    santiago_dt = to_santiago(dt_value)
    return start_hour <= santiago_dt.hour < end_hour and santiago_dt.weekday() < 5  # Lun-Vie


def add_business_hours(dt_value: dt.datetime, hours: int) -> dt.datetime:
    """Suma horas hábiles (solo Lun-Vie 9-19) a un datetime."""
    current = to_santiago(dt_value)
    added = 0
    while added < hours:
        current += dt.timedelta(hours=1)
        if is_business_hours(current):
            added += 1
    return current