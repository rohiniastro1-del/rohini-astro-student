from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from typing import Callable

from vedic_app.data import SIGN_NAMES_BG, navamsha_sign_index


EPSILON = Decimal("1e-9")
THIRTY_DEGREES = Decimal("30")
LEO_SIGN_INDEX = 4
CANCER_SIGN_INDEX = 3
ODD_SIGN_INDEXES = {0, 2, 4, 6, 8, 10}

DEFAULT_DIVISIONAL_CHART_CODE = "D9"

DivisionalBundle = dict[str, object]
ChartPayloadBuilder = Callable[..., dict[str, object]]
DivisionalCalculator = Callable[[int, float], int]


def _is_odd_sign(sign_index: int) -> bool:
    return sign_index in ODD_SIGN_INDEXES


def _normalize_degree_in_sign(longitude_within_sign_degrees: float) -> Decimal:
    value = Decimal(str(longitude_within_sign_degrees))
    if value < 0:
        return Decimal("0")
    if value >= THIRTY_DEGREES:
        return THIRTY_DEGREES - EPSILON
    return value


def _part_index(longitude_within_sign_degrees: float, divisions: int) -> int:
    normalized = _normalize_degree_in_sign(longitude_within_sign_degrees)
    raw_index = ((normalized * Decimal(divisions)) / THIRTY_DEGREES) + EPSILON
    part_index = int(raw_index.to_integral_value(rounding=ROUND_FLOOR))
    if part_index < 0:
        return 0
    if part_index >= divisions:
        return divisions - 1
    return part_index


def _offset_sign(sign_index: int, offset: int) -> int:
    return (sign_index + offset) % 12


def calculate_d2(sign_index: int, longitude_within_sign_degrees: float) -> int:
    part = _part_index(longitude_within_sign_degrees, 2)
    if _is_odd_sign(sign_index):
        return LEO_SIGN_INDEX if part == 0 else CANCER_SIGN_INDEX
    return CANCER_SIGN_INDEX if part == 0 else LEO_SIGN_INDEX


def calculate_d3(sign_index: int, longitude_within_sign_degrees: float) -> int:
    offsets = (0, 4, 8)
    return _offset_sign(sign_index, offsets[_part_index(longitude_within_sign_degrees, 3)])


def calculate_d4(sign_index: int, longitude_within_sign_degrees: float) -> int:
    offsets = (0, 3, 6, 9)
    return _offset_sign(sign_index, offsets[_part_index(longitude_within_sign_degrees, 4)])


def calculate_d7(sign_index: int, longitude_within_sign_degrees: float) -> int:
    start_sign = sign_index if _is_odd_sign(sign_index) else _offset_sign(sign_index, 6)
    return _offset_sign(start_sign, _part_index(longitude_within_sign_degrees, 7))


def calculate_d9(sign_index: int, longitude_within_sign_degrees: float) -> int:
    return navamsha_sign_index(sign_index, longitude_within_sign_degrees)


def calculate_d10(sign_index: int, longitude_within_sign_degrees: float) -> int:
    start_sign = sign_index if _is_odd_sign(sign_index) else _offset_sign(sign_index, 8)
    return _offset_sign(start_sign, _part_index(longitude_within_sign_degrees, 10))


def calculate_d12(sign_index: int, longitude_within_sign_degrees: float) -> int:
    return _offset_sign(sign_index, _part_index(longitude_within_sign_degrees, 12))


def calculate_d24(sign_index: int, longitude_within_sign_degrees: float) -> int:
    start_sign = LEO_SIGN_INDEX if _is_odd_sign(sign_index) else CANCER_SIGN_INDEX
    return _offset_sign(start_sign, _part_index(longitude_within_sign_degrees, 24))


DIVISIONAL_CHARTS: dict[str, dict[str, object]] = {
    "D2": {
        "id": "D2",
        "label": "D-2",
        "name": "Hora",
        "subtitle": "Хора",
        "description": "Хора дели всеки знак на две равни части по 15°.",
        "calculator": calculate_d2,
    },
    "D3": {
        "id": "D3",
        "label": "D-3",
        "name": "Drekkana",
        "subtitle": "Дрекана",
        "description": "Дрекана дели всеки знак на три части по 10°.",
        "calculator": calculate_d3,
    },
    "D4": {
        "id": "D4",
        "label": "D-4",
        "name": "Chaturthamsha",
        "subtitle": "Чатуртамша",
        "description": "Чатуртамша дели всеки знак на четири части по 7°30′.",
        "calculator": calculate_d4,
    },
    "D7": {
        "id": "D7",
        "label": "D-7",
        "name": "Saptamsha",
        "subtitle": "Саптамша",
        "description": "Саптамша дели всеки знак на 7 математически равни части.",
        "calculator": calculate_d7,
    },
    "D9": {
        "id": "D9",
        "label": "D-9",
        "name": "Navamsha",
        "subtitle": "Навамша",
        "description": "Навамша е построена по същата логика, която вече съществува в проекта.",
        "calculator": calculate_d9,
    },
    "D10": {
        "id": "D10",
        "label": "D-10",
        "name": "Dashamsha",
        "subtitle": "Дашамша",
        "description": "Дашамша дели всеки знак на десет части по 3°.",
        "calculator": calculate_d10,
    },
    "D12": {
        "id": "D12",
        "label": "D-12",
        "name": "Dvadashamsha",
        "subtitle": "Двадашамша",
        "description": "Двадашамша дели всеки знак на дванадесет части по 2°30′.",
        "calculator": calculate_d12,
    },
    "D24": {
        "id": "D24",
        "label": "D-24",
        "name": "Chaturvimshamsha",
        "subtitle": "Чатурвимшамша",
        "description": "Чатурвимшамша дели всеки знак на двадесет и четири части по 1°15′.",
        "calculator": calculate_d24,
    },
}

DIVISIONAL_CHART_BUILDERS: dict[str, DivisionalCalculator] = {
    code: definition["calculator"]
    for code, definition in DIVISIONAL_CHARTS.items()
}

DIVISIONAL_CHART_OPTIONS = [
    {"code": code, "label": definition.get("selector_label", f"{definition['id']} {definition['name']}")}
    for code, definition in DIVISIONAL_CHARTS.items()
]


def _amsha_size_label(divisions: int) -> str:
    total_arcseconds = (
        (THIRTY_DEGREES * Decimal("3600")) / Decimal(divisions)
    ).to_integral_value(rounding=ROUND_HALF_UP)
    total = int(total_arcseconds)
    degrees, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{degrees:02d}°{minutes:02d}′{seconds:02d}″"


def calculate_amsha_details(
    chart_type: str,
    sign_index: int,
    longitude_within_sign_degrees: float,
) -> dict[str, object] | None:
    definition = DIVISIONAL_CHARTS.get(chart_type)
    if definition is None:
        return None

    degree = _normalize_degree_in_sign(longitude_within_sign_degrees)
    divisions = int(chart_type.removeprefix("D"))
    part_index = _part_index(longitude_within_sign_degrees, divisions)
    part_width = THIRTY_DEGREES / Decimal(divisions)
    lower_bound = Decimal(part_index) * part_width
    upper_bound = lower_bound + part_width
    destination = definition["calculator"](sign_index, longitude_within_sign_degrees)
    size_label = _amsha_size_label(divisions)

    progress = ((degree - lower_bound) * Decimal("100")) / (upper_bound - lower_bound)
    percentage = int(progress.to_integral_value(rounding=ROUND_FLOOR))
    return {
        "number": part_index + 1,
        "sign_index": destination,
        "sign_number": destination + 1,
        "sign_name": SIGN_NAMES_BG[destination],
        "percentage": max(0, min(99, percentage)),
        "size_label": size_label,
    }


def _build_amsha_rows(
    definition: dict[str, object],
    points: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for point in points:
        details = calculate_amsha_details(
            str(definition["id"]),
            int(point["sign_index"]),
            float(point["degree_in_sign"]),
        )
        if details is None:
            continue
        rows.append(
            {
                "key": str(point["key"]),
                "name": str(point["name"]),
                "label": str(point["label"]),
                "degree_dms": str(point["degree_dms"]),
                "amsha_number": details["number"],
                "amsha_sign_number": details["sign_number"],
                "amsha_sign_name": details["sign_name"],
                "percentage": details["percentage"],
            }
        )
    return rows


def calculate_divisional_placement(
    chart_type: str,
    sign_index: int,
    longitude_within_sign_degrees: float,
) -> int | None:
    definition = DIVISIONAL_CHARTS.get(chart_type)
    if definition is None:
        return None
    calculator = definition["calculator"]
    return calculator(sign_index, longitude_within_sign_degrees)


def _blank_chart_payload(title: str, subtitle: str, aria_title: str) -> dict[str, object]:
    return {
        "title": title,
        "subtitle": subtitle,
        "aria_title": aria_title,
        "houses": [
            {"house": house_number, "sign_number": "", "items": []}
            for house_number in range(1, 13)
        ],
    }


def _build_payload_for_chart(
    definition: dict[str, object],
    *,
    build_chart_payload: ChartPayloadBuilder,
    points: list[dict[str, object]],
) -> dict[str, object]:
    ascendant = next((point for point in points if point["key"] == "Ascendant"), None)
    if ascendant is None:
        raise ValueError("Missing Ascendant point for divisional chart calculation.")

    asc_sign_index = calculate_divisional_placement(
        definition["id"],
        ascendant["sign_index"],
        ascendant["degree_in_sign"],
    )
    if asc_sign_index is None:
        raise ValueError(f"Unsupported divisional chart: {definition['id']}")

    divisional_points: list[dict[str, object]] = []
    for point in points:
        divisional_sign_index = calculate_divisional_placement(
            definition["id"],
            point["sign_index"],
            point["degree_in_sign"],
        )
        if divisional_sign_index is None:
            raise ValueError(f"Unsupported divisional chart: {definition['id']}")

        divisional_point = dict(point)
        divisional_point["divisional_sign_index"] = divisional_sign_index
        divisional_point["divisional_sign_number"] = divisional_sign_index + 1
        divisional_point["divisional_sign_name"] = SIGN_NAMES_BG[divisional_sign_index]
        divisional_point["divisional_house"] = ((divisional_sign_index - asc_sign_index) % 12) + 1
        divisional_points.append(divisional_point)

    return build_chart_payload(
        definition["label"],
        definition["subtitle"],
        asc_sign_index,
        divisional_points,
        "divisional_house",
        "divisional_sign_number",
        aria_title=f"{definition['label']} ({definition['name']})",
    )


def _unsupported_bundle(code: str) -> DivisionalBundle:
    label = code.replace("D", "D-")
    return {
        "code": code,
        "selector_label": code,
        "card_title": f"{label} (Неподдържана)",
        "description": f"{code} още не е налична в този калкулатор.",
        "implemented": False,
        "note": f"Няма регистриран calculator за {code}.",
        "payload": _blank_chart_payload(label, "Неподдържана карта", aria_title=f"{label} (Unsupported)"),
    }


def build_divisional_chart_bundle(
    code: str,
    *,
    build_chart_payload: ChartPayloadBuilder,
    points: list[dict[str, object]],
    asc_nav_sign: int | None = None,
) -> DivisionalBundle:
    del asc_nav_sign
    definition = DIVISIONAL_CHARTS.get(code)
    if definition is None:
        return _unsupported_bundle(code)

    payload = _build_payload_for_chart(
        definition,
        build_chart_payload=build_chart_payload,
        points=points,
    )
    return {
        "code": definition["id"],
        "selector_label": definition.get("selector_label", f"{definition['id']} {definition['name']}"),
        "card_title": f"{definition['label']} ({definition['name']})",
        "amsha_title": f"{definition['label']} • {definition['subtitle']}",
        "description": definition["description"],
        "implemented": True,
        "note": "",
        "payload": payload,
        "amsha_size_label": calculate_amsha_details(
            str(definition["id"]),
            int(points[0]["sign_index"]),
            float(points[0]["degree_in_sign"]),
        )["size_label"],
        "amsha_rows": _build_amsha_rows(definition, points),
    }


def build_divisional_chart_registry(
    *,
    build_chart_payload: ChartPayloadBuilder,
    points: list[dict[str, object]],
    asc_nav_sign: int | None = None,
) -> dict[str, DivisionalBundle]:
    return {
        option["code"]: build_divisional_chart_bundle(
            option["code"],
            build_chart_payload=build_chart_payload,
            points=points,
            asc_nav_sign=asc_nav_sign,
        )
        for option in DIVISIONAL_CHART_OPTIONS
    }
