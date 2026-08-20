from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import logging

from vedic_app.dasha import SECONDS_PER_YEAR
from vedic_app.data import PLANET_NAMES_BG, SIGN_NAMES_BG


LOGGER = logging.getLogger(__name__)

DIRECT_MAHADASHA_SIGNS = {0, 4, 5, 6, 10, 11}
DIRECT_RULER_COUNT_SIGNS = {0, 1, 2, 6, 7, 8}
DIRECT_ANTARDASHA_SIGNS = {0, 4, 5, 6, 10, 11}

SINGLE_SIGN_RULERS = {
    0: "Mars",
    1: "Venus",
    2: "Mercury",
    3: "Moon",
    4: "Sun",
    5: "Mercury",
    6: "Venus",
    8: "Jupiter",
    9: "Saturn",
    11: "Jupiter",
}

DUAL_SIGN_RULERS = {
    7: ("Mars", "Ketu"),
    10: ("Saturn", "Rahu"),
}

DUAL_RULER_TIEBREAK_ORDER = {
    "Mars": 0,
    "Ketu": 1,
    "Saturn": 2,
    "Rahu": 3,
}

PLANET_KEYS_FOR_CONJUNCTION = (
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
    "Rahu",
    "Ketu",
)


def _step_label(step: int) -> str:
    return "Напред" if step > 0 else "Назад"


def _advance_sign(sign_index: int, step: int, offset: int) -> int:
    return (sign_index + (step * offset)) % 12


def _format_datetime(value: datetime) -> str:
    return value.strftime("%d.%m.%Y, %H:%M")


def _format_years_duration(years: int) -> str:
    return f"{years} г."


def _format_months_duration(months: int) -> str:
    return f"{months} мес."


def _years_to_timedelta(years: Decimal, year_days: Decimal | None = None) -> timedelta:
    seconds_per_year = SECONDS_PER_YEAR if year_days is None else year_days * Decimal("86400")
    seconds = int((years * seconds_per_year).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return timedelta(seconds=seconds)


def _inclusive_sign_distance(start_sign_index: int, end_sign_index: int, step: int) -> int:
    if step > 0:
        return ((end_sign_index - start_sign_index) % 12) + 1
    return ((start_sign_index - end_sign_index) % 12) + 1


def _conjunction_count(planet_key: str, rows_by_key: dict[str, dict[str, object]]) -> int:
    target_sign_index = rows_by_key[planet_key]["sign_index"]
    return sum(
        1
        for other_key in PLANET_KEYS_FOR_CONJUNCTION
        if other_key != planet_key and rows_by_key[other_key]["sign_index"] == target_sign_index
    )


def _planet_degree_in_sign(row: dict[str, object]) -> Decimal:
    return Decimal(str(row["degree_in_sign"]))


def _choose_dual_ruler(sign_index: int, rows_by_key: dict[str, dict[str, object]]) -> dict[str, object]:
    ruler_keys = DUAL_SIGN_RULERS[sign_index]
    first_key, second_key = ruler_keys
    first_row = rows_by_key[first_key]
    second_row = rows_by_key[second_key]

    if first_row["sign_index"] == sign_index and second_row["sign_index"] == sign_index:
        return {
            "ruler_key": first_key,
            "ruler_name": PLANET_NAMES_BG[first_key],
            "ruler_sign_index": sign_index,
            "force_twelve_years": True,
        }

    if first_row["sign_index"] == second_row["sign_index"]:
        return {
            "ruler_key": first_key,
            "ruler_name": PLANET_NAMES_BG[first_key],
            "ruler_sign_index": first_row["sign_index"],
            "force_twelve_years": False,
        }

    if first_row["sign_index"] == sign_index and second_row["sign_index"] != sign_index:
        return {
            "ruler_key": second_key,
            "ruler_name": PLANET_NAMES_BG[second_key],
            "ruler_sign_index": second_row["sign_index"],
            "force_twelve_years": False,
        }

    if second_row["sign_index"] == sign_index and first_row["sign_index"] != sign_index:
        return {
            "ruler_key": first_key,
            "ruler_name": PLANET_NAMES_BG[first_key],
            "ruler_sign_index": first_row["sign_index"],
            "force_twelve_years": False,
        }

    first_conjunctions = _conjunction_count(first_key, rows_by_key)
    second_conjunctions = _conjunction_count(second_key, rows_by_key)
    if first_conjunctions != second_conjunctions:
        chosen_key = first_key if first_conjunctions > second_conjunctions else second_key
        chosen_row = rows_by_key[chosen_key]
        return {
            "ruler_key": chosen_key,
            "ruler_name": PLANET_NAMES_BG[chosen_key],
            "ruler_sign_index": chosen_row["sign_index"],
            "force_twelve_years": False,
        }

    first_degree = _planet_degree_in_sign(first_row)
    second_degree = _planet_degree_in_sign(second_row)
    if first_degree != second_degree:
        chosen_key = first_key if first_degree > second_degree else second_key
        chosen_row = rows_by_key[chosen_key]
        return {
            "ruler_key": chosen_key,
            "ruler_name": PLANET_NAMES_BG[chosen_key],
            "ruler_sign_index": chosen_row["sign_index"],
            "force_twelve_years": False,
        }

    # Това е само техническа защита за стабилност на софтуера при пълно равенство.
    LOGGER.debug(
        "Пълно равенство при избор на двоен управител за %s. Използван е технически tie-break.",
        SIGN_NAMES_BG[sign_index],
    )
    chosen_key = min(ruler_keys, key=lambda key: DUAL_RULER_TIEBREAK_ORDER[key])
    chosen_row = rows_by_key[chosen_key]
    return {
        "ruler_key": chosen_key,
        "ruler_name": PLANET_NAMES_BG[chosen_key],
        "ruler_sign_index": chosen_row["sign_index"],
        "force_twelve_years": False,
    }


def choose_chara_dasha_ruler(sign_index: int, rows_by_key: dict[str, dict[str, object]]) -> dict[str, object]:
    if sign_index in DUAL_SIGN_RULERS:
        return _choose_dual_ruler(sign_index, rows_by_key)

    ruler_key = SINGLE_SIGN_RULERS[sign_index]
    ruler_row = rows_by_key[ruler_key]
    return {
        "ruler_key": ruler_key,
        "ruler_name": PLANET_NAMES_BG[ruler_key],
        "ruler_sign_index": ruler_row["sign_index"],
        "force_twelve_years": ruler_row["sign_index"] == sign_index,
    }


def calculate_mahadasha_years(sign_index: int, rows_by_key: dict[str, dict[str, object]]) -> int:
    ruler_info = choose_chara_dasha_ruler(sign_index, rows_by_key)
    if ruler_info["force_twelve_years"]:
        return 12

    step = 1 if sign_index in DIRECT_RULER_COUNT_SIGNS else -1
    count = _inclusive_sign_distance(sign_index, ruler_info["ruler_sign_index"], step)
    return count - 1


def calculate_mahadasha_order(asc_sign_index: int) -> tuple[list[int], int]:
    ninth_sign_index = (asc_sign_index + 8) % 12
    step = 1 if ninth_sign_index in DIRECT_MAHADASHA_SIGNS else -1
    return ([_advance_sign(asc_sign_index, step, offset) for offset in range(12)], step)


def calculate_antardasha_order(mahadasha_sign_index: int) -> tuple[list[int], int]:
    step = 1 if mahadasha_sign_index in DIRECT_ANTARDASHA_SIGNS else -1
    return ([_advance_sign(mahadasha_sign_index, step, offset) for offset in range(1, 13)], step)


def _build_antardashas(
    mahadasha_sign_index: int,
    mahadasha_years: int,
    start: datetime,
    year_days: Decimal | None = None,
) -> list[dict[str, object]]:
    order, step = calculate_antardasha_order(mahadasha_sign_index)
    seconds_per_year = SECONDS_PER_YEAR if year_days is None else year_days * Decimal("86400")
    total_seconds_decimal = Decimal(mahadasha_years) * seconds_per_year
    previous_cumulative_seconds = 0
    periods: list[dict[str, object]] = []

    for index, sign_index in enumerate(order, start=1):
        cumulative_seconds = int(
            ((total_seconds_decimal * Decimal(index)) / Decimal("12")).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )
        period_start = start + timedelta(seconds=previous_cumulative_seconds)
        period_end = start + timedelta(seconds=cumulative_seconds)
        periods.append(
            {
                "mahadasha_sign_name": SIGN_NAMES_BG[mahadasha_sign_index],
                "sign_index": sign_index,
                "sign_name": SIGN_NAMES_BG[sign_index],
                "start": period_start,
                "end": period_end,
                "start_label": _format_datetime(period_start),
                "end_label": _format_datetime(period_end),
                "duration_label": _format_months_duration(mahadasha_years),
                "direction_label": _step_label(step),
            }
        )
        previous_cumulative_seconds = cumulative_seconds

    return periods


def build_chara_dasha_rao(
    rows_by_key: dict[str, dict[str, object]],
    asc_sign_index: int,
    birth_dt: datetime,
    year_days: Decimal | None = None,
) -> dict[str, object]:
    order, step = calculate_mahadasha_order(asc_sign_index)
    periods: list[dict[str, object]] = []
    cursor = birth_dt

    for sign_index in order:
        years = calculate_mahadasha_years(sign_index, rows_by_key)
        ruler_info = choose_chara_dasha_ruler(sign_index, rows_by_key)
        period_end = cursor + _years_to_timedelta(Decimal(years), year_days)
        periods.append(
            {
                "sign_index": sign_index,
                "sign_name": SIGN_NAMES_BG[sign_index],
                "start": cursor,
                "end": period_end,
                "start_label": _format_datetime(cursor),
                "end_label": _format_datetime(period_end),
                "duration_years": years,
                "duration_label": _format_years_duration(years),
                "direction_label": _step_label(step),
                "ruler_key": ruler_info["ruler_key"],
                "ruler_name": ruler_info["ruler_name"],
                "antardashas": _build_antardashas(sign_index, years, cursor, year_days),
            }
        )
        cursor = period_end

    return {
        "calendar_note": (
            f"Датите са изчислени по средна тропическа соларна година = {year_days} дни."
            if year_days is not None
            else "Датите са изчислени по средна тропическа соларна година = 365.24219 дни."
        ),
        "md_periods": periods,
    }
