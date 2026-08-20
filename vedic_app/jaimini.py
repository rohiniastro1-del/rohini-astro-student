from __future__ import annotations

import logging
from decimal import Decimal
from datetime import datetime
from typing import Callable

from vedic_app.chara_dasha import build_chara_dasha_rao
from vedic_app.chart import build_sign_sequence
from vedic_app.data import PLANET_NAMES_BG


LOGGER = logging.getLogger(__name__)

ChartPayloadBuilder = Callable[..., dict[str, object]]

CHARA_PLANET_KEYS = (
    "Sun",
    "Moon",
    "Mars",
    "Mercury",
    "Jupiter",
    "Venus",
    "Saturn",
)

CHARA_KARAKA_DEFINITIONS = (
    {"code": "Ат", "name": "Атмакарака"},
    {"code": "Амк", "name": "Аматякарака"},
    {"code": "Бк", "name": "Бхатрикарака"},
    {"code": "Мк", "name": "Матрукарака"},
    {"code": "Пк", "name": "Путракарака"},
    {"code": "Гк", "name": "Гнатикарака"},
    {"code": "Дк", "name": "Даракарака"},
)

SIGN_RULERS = {
    0: "Mars",
    1: "Venus",
    2: "Mercury",
    3: "Moon",
    4: "Sun",
    5: "Mercury",
    6: "Venus",
    7: "Mars",
    8: "Jupiter",
    9: "Saturn",
    10: "Saturn",
    11: "Jupiter",
}

PLANET_TIEBREAK_ORDER = {
    "Sun": 0,
    "Moon": 1,
    "Mars": 2,
    "Mercury": 3,
    "Jupiter": 4,
    "Venus": 5,
    "Saturn": 6,
}


def _planet_degree_in_sign(row: dict[str, object]) -> Decimal:
    return Decimal(str(row["degree_in_sign"]))


def _log_full_tie_if_needed(rows_by_key: dict[str, dict[str, object]]) -> None:
    grouped: dict[Decimal, list[str]] = {}
    for planet_key in CHARA_PLANET_KEYS:
        grouped.setdefault(_planet_degree_in_sign(rows_by_key[planet_key]), []).append(planet_key)

    for degree_value, planet_keys in grouped.items():
        if len(planet_keys) > 1:
            LOGGER.debug(
                "Пълно равенство при определяне на чара караките на %s в рамките на знака. "
                "Приложен е технически tie-break за стабилност.",
                degree_value,
            )


def calculate_chara_karakas(rows_by_key: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    for planet_key in CHARA_PLANET_KEYS:
        if planet_key not in rows_by_key:
            raise ValueError(f"Липсва планета {planet_key} за определяне на чара караките.")

    _log_full_tie_if_needed(rows_by_key)

    ranked_rows = sorted(
        (rows_by_key[planet_key] for planet_key in CHARA_PLANET_KEYS),
        key=lambda row: (
            -_planet_degree_in_sign(row),
            PLANET_TIEBREAK_ORDER[row["key"]],
        ),
    )

    karakas: list[dict[str, object]] = []
    for definition, row in zip(CHARA_KARAKA_DEFINITIONS, ranked_rows):
        karakas.append(
            {
                "code": definition["code"],
                "name": definition["name"],
                "planet_key": row["key"],
                "planet_name": PLANET_NAMES_BG[row["key"]],
                "sign_index": row["sign_index"],
                "sign_number": row["sign_number"],
                "sign_name": row["sign_name"],
                "house": row["house"],
                "degree_in_sign": row["degree_in_sign"],
                "degree_dms": row["degree_dms"],
                "chart_code": definition["code"],
            }
        )

    return karakas


def _inclusive_sign_distance(start_sign_index: int, end_sign_index: int) -> int:
    return ((end_sign_index - start_sign_index) % 12) + 1


def _build_arudha_row(
    code: str,
    name: str,
    sign_index: int,
    asc_sign_index: int,
) -> dict[str, object]:
    return {
        "code": code,
        "name": name,
        "sign_index": sign_index,
        "sign_number": sign_index + 1,
        "house": ((sign_index - asc_sign_index) % 12) + 1,
        "chart_code": code,
    }


def calculate_arudhas(
    rows_by_key: dict[str, dict[str, object]],
    asc_sign_index: int,
) -> list[dict[str, object]]:
    sign_sequence = build_sign_sequence(asc_sign_index + 1)
    arudhas: list[dict[str, object]] = []

    a1_sign_index = None

    for house_number in range(1, 13):
        house_sign_index = sign_sequence[house_number] - 1
        ruler_key = SIGN_RULERS[house_sign_index]
        if ruler_key not in rows_by_key:
            raise ValueError(f"Липсва управителят {ruler_key} за арудха на дом {house_number}.")

        ruler_sign_index = rows_by_key[ruler_key]["sign_index"]
        distance = _inclusive_sign_distance(house_sign_index, ruler_sign_index)
        arudha_sign_index = (ruler_sign_index + distance - 1) % 12

        if house_number == 1:
            a1_sign_index = arudha_sign_index

        arudhas.append(
            _build_arudha_row(
                f"А{house_number}",
                f"Арудха на {house_number}. дом",
                arudha_sign_index,
                asc_sign_index,
            )
        )

    if a1_sign_index is None:
        raise ValueError("Не може да се определи А1 за джаймини блока.")

    return [
        _build_arudha_row("Ал", "Арудха Лагна", a1_sign_index, asc_sign_index),
        *arudhas,
    ]


def _build_jaimini_points(
    chara_karakas: list[dict[str, object]],
    arudhas: list[dict[str, object]],
) -> list[dict[str, object]]:
    return [
        *[
            {
                "chart_code": row["chart_code"],
                "house": row["house"],
                "sign_number": row["sign_number"],
            }
            for row in chara_karakas
        ],
        *[
            {
                "chart_code": row["chart_code"],
                "house": row["house"],
                "sign_number": row["sign_number"],
            }
            for row in arudhas
            if row["code"] != "А1"
        ],
    ]


def build_jaimini_bundle(
    *,
    build_chart_payload: ChartPayloadBuilder,
    natal_chart_payload: dict[str, object],
    rows_by_key: dict[str, dict[str, object]],
    asc_sign_index: int,
    birth_dt: datetime,
) -> dict[str, object]:
    chara_karakas = calculate_chara_karakas(rows_by_key)
    arudhas = calculate_arudhas(rows_by_key, asc_sign_index)
    chara_dasha = build_chara_dasha_rao(rows_by_key, asc_sign_index, birth_dt)
    jaimini_points = _build_jaimini_points(chara_karakas, arudhas)

    jaimini_chart_payload = build_chart_payload(
        "Дж",
        "Чара караки и арудхи",
        asc_sign_index,
        jaimini_points,
        "house",
        "sign_number",
        aria_title="Джаймини: чара караки и арудхи",
    )

    return {
        "title": "Джаймини",
        "rashi_card_title": "Раши",
        "rashi_description": "Наталната Раши карта е показана тук без промяна, за да служи за пряко сравнение.",
        "rashi_chart_payload": natal_chart_payload,
        "jaimini_card_title": "Чара караки и арудхи",
        "jaimini_description": "В тази карта са нанесени само чара караките и арудхите върху наталната Раши схема.",
        "jaimini_chart_payload": jaimini_chart_payload,
        "chara_karakas": chara_karakas,
        "arudhas": arudhas,
        "chara_dasha": chara_dasha,
    }
