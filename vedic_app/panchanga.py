from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import swisseph as swe


WEEKDAY_LORDS = ("Луна", "Марс", "Меркурий", "Юпитер", "Венера", "Сатурн", "Слънце")
HORA_SEQUENCE = ("Сатурн", "Юпитер", "Марс", "Слънце", "Венера", "Меркурий", "Луна")


def _clamp_percent(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _jd_from_datetime(value: datetime) -> float:
    utc = value.astimezone(timezone.utc)
    hours = utc.hour + utc.minute / 60 + utc.second / 3600 + utc.microsecond / 3_600_000_000
    return swe.julday(utc.year, utc.month, utc.day, hours)


def _datetime_from_jd(jd: float) -> datetime:
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=jd - 2440587.5)


def _rise_or_set(local_date: date, tzinfo, latitude: float, longitude: float, rising: bool) -> datetime:
    local_midnight = datetime.combine(local_date, time.min, tzinfo=tzinfo)
    start_jd = _jd_from_datetime(local_midnight) - 0.05
    event_flag = swe.CALC_RISE if rising else swe.CALC_SET
    # Rohini uses the visible upper limb of the Sun at the apparent horizon.
    # This is the JHora reference option "tip of Sun's disk appears".  A
    # standard 20 C atmosphere reproduces the reference sunrise/set while the
    # modern Swiss ephemeris and Delta-T configuration remain authoritative.
    result, values = swe.rise_trans_true_hor(
        start_jd,
        swe.SUN,
        event_flag,
        (longitude, latitude, 0.0),
        0.0,
        20.0,
        0.0,
        swe.FLG_SWIEPH,
    )
    if result < 0:
        raise ValueError("Няма изчислим слънчев изгрев/залез за тази дата и място.")
    return _datetime_from_jd(values[0]).astimezone(tzinfo)


def _segment(moment: datetime, start: datetime, end: datetime, count: int) -> tuple[int, float, datetime, datetime]:
    duration = (end - start).total_seconds()
    position = max(0.0, min(duration - 1e-6, (moment - start).total_seconds()))
    width = duration / count
    index = min(count - 1, int(position / width))
    segment_start = start + timedelta(seconds=index * width)
    segment_end = start + timedelta(seconds=(index + 1) * width)
    elapsed = (moment - segment_start).total_seconds() / width * 100
    return index, _clamp_percent(elapsed), segment_start, segment_end


def build_panchanga(*, local_datetime: datetime, latitude: float, longitude: float) -> dict[str, object]:
    """Връща Вара и Хора (Satya Hora) по изгрев-до-изгрев ведически ден."""
    tzinfo = local_datetime.tzinfo
    civil_date = local_datetime.date()
    sunrise = _rise_or_set(civil_date, tzinfo, latitude, longitude, True)
    tomorrow_sunrise = _rise_or_set(civil_date + timedelta(days=1), tzinfo, latitude, longitude, True)
    yesterday_sunrise = _rise_or_set(civil_date - timedelta(days=1), tzinfo, latitude, longitude, True)

    if local_datetime < sunrise:
        vedic_start, vedic_end = yesterday_sunrise, sunrise
    else:
        vedic_start, vedic_end = sunrise, tomorrow_sunrise

    vara_elapsed = _clamp_percent(
        (local_datetime - vedic_start).total_seconds() / (vedic_end - vedic_start).total_seconds() * 100
    )
    vara_lord = WEEKDAY_LORDS[vedic_start.weekday()]

    # Satya Hora: изгрев-до-изгрев ведическият ден се дели на 24 хори.
    hora_index, hora_elapsed, hora_start, hora_end = _segment(local_datetime, vedic_start, vedic_end, 24)
    first_hora = HORA_SEQUENCE.index(vara_lord)
    hora_lord = HORA_SEQUENCE[(first_hora + hora_index) % 7]

    return {
        "calculation_standard": "Drik Panchanga / Swiss Ephemeris / Lahiri",
        "vara": {
            "lord": vara_lord,
            "elapsed_percent": vara_elapsed,
            "remaining_percent": _clamp_percent(100 - vara_elapsed),
        },
        "hora": {
            "lord": hora_lord,
            "elapsed_percent": hora_elapsed,
            "remaining_percent": _clamp_percent(100 - hora_elapsed),
            "start": hora_start,
            "end": hora_end,
        },
    }
