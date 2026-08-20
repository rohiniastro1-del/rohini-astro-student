"""Собствена реализация на Вимшоттари даша.

Модулът пресмята периодите на Вимшоттари даша, като използва сидеричните
дължини от модерната астрономическа основа на Рохини Астро и средната
тропическа година като граница на периодите.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from vedic_app.data import PLANET_LABELS_BG


TROPICAL_YEAR_DAYS = 365.24219

PLANET_KEYS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
PLANET_LABEL = {index: PLANET_LABELS_BG[key] for index, key in enumerate(PLANET_KEYS)}

ONE_STAR = 360.0 / 27.0

# Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury
VIMSHOTTARI_SEQUENCE = (8, 5, 0, 1, 2, 7, 4, 6, 3)
VIMSHOTTARI_YEARS = {8: 7, 5: 20, 0: 6, 1: 10, 2: 7, 7: 18, 4: 16, 6: 19, 3: 17}


def _years_to_timedelta(years: float) -> timedelta:
    return timedelta(seconds=float(years) * float(TROPICAL_YEAR_DAYS) * 86400)


def _format_dt(value: datetime) -> str:
    if value.microsecond >= 500000:
        value = value.replace(microsecond=0) + timedelta(seconds=1)
    else:
        value = value.replace(microsecond=0)
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _nakshatra_index(longitude: float) -> int:
    return int(longitude / ONE_STAR)


def _nakshatra_fraction(longitude: float) -> float:
    nak = _nakshatra_index(longitude)
    return (longitude - nak * ONE_STAR) / ONE_STAR


def _vimshottari_lord(nak: int) -> int:
    return VIMSHOTTARI_SEQUENCE[nak % 9]


def _graha_dasha_top(birth_dt: datetime, moon_longitude: float, sequence: tuple, years: dict,
                     nak_to_lord, cycles: int = 1) -> list[tuple[int, datetime, datetime]]:
    nak = _nakshatra_index(moon_longitude)
    fraction = _nakshatra_fraction(moon_longitude)
    md_lord = nak_to_lord(nak)
    md_years = years[md_lord]
    elapsed = md_years * fraction
    cursor = birth_dt - _years_to_timedelta(elapsed)

    start_index = sequence.index(md_lord)
    order = sequence[start_index:] + sequence[:start_index]
    rows = []
    for _ in range(cycles):
        for lord in order:
            end = cursor + _years_to_timedelta(years[lord])
            rows.append((lord, cursor, end))
            cursor = end
    return rows


def _graha_dasha_children(path: list[int], parent_start: datetime, parent_end: datetime,
                          sequence: tuple, years: dict) -> list[tuple[int, datetime, datetime]]:
    parent_lord = path[-1]
    start_index = sequence.index(parent_lord)
    order = sequence[start_index:] + sequence[:start_index]
    span = parent_end - parent_start
    span_seconds = span.total_seconds()
    total = sum(years[lord] for lord in order)
    cursor = parent_start
    rows = []
    for index, lord in enumerate(order):
        if index == len(order) - 1:
            child_end = parent_end
        else:
            child_end = cursor + timedelta(seconds=span_seconds * years[lord] / total)
        rows.append((lord, cursor, child_end))
        cursor = child_end
    return rows


def _row(path: list[int], lord: int, start: datetime, end: datetime) -> dict:
    return {
        "path": [*path, lord],
        "label": PLANET_LABEL[lord],
        "start": start.isoformat(),
        "end": end.isoformat(),
        "start_label": _format_dt(start),
        "end_label": _format_dt(end),
    }


def build_dasha_rows(system: str, table_rows: list[dict], birth_dt: datetime,
                     path: list[int], parent_start: datetime | None,
                     parent_end: datetime | None) -> list[dict]:
    """Връща интерактивните редове на Вимшоттари даша за даденото ниво."""
    if system != "vimshottari":
        raise ValueError("Непозната даша.")

    moon_longitude = float(next(row["longitude"] for row in table_rows if row["key"] == "Moon"))
    if not path:
        entries = _graha_dasha_top(birth_dt, moon_longitude, VIMSHOTTARI_SEQUENCE,
                                   VIMSHOTTARI_YEARS, _vimshottari_lord)
    else:
        entries = _graha_dasha_children(path, parent_start, parent_end,
                                        VIMSHOTTARI_SEQUENCE, VIMSHOTTARI_YEARS)
    return [_row(path, lord, start, end) for lord, start, end in entries]
