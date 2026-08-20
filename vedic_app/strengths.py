from __future__ import annotations

from vedic_app.data import PLANET_NAMES_BG, SIGN_NAMES_BG


CLASSICAL = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
RELATION_PLANETS = (*CLASSICAL, "Rahu", "Ketu")
ASHTAKA_SOURCES = (*CLASSICAL, "Ascendant")
ASHTAKA_SHORT_BG = {
    "Sun": "Сл",
    "Moon": "Лу",
    "Mars": "Ма",
    "Mercury": "Ме",
    "Jupiter": "Юп",
    "Venus": "Ве",
    "Saturn": "Са",
}

SIGN_LORDS = (
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter",
)

NATURAL_FRIENDS = {
    "Sun": {"Moon", "Mars", "Jupiter"},
    "Moon": {"Sun", "Mercury"},
    "Mars": {"Sun", "Moon", "Jupiter"},
    "Mercury": {"Sun", "Venus"},
    "Jupiter": {"Sun", "Moon", "Mars"},
    "Venus": {"Mercury", "Saturn"},
    "Saturn": {"Mercury", "Venus"},
    "Rahu": {"Venus", "Saturn"},
    "Ketu": {"Venus", "Mars"},
}
NATURAL_ENEMIES = {
    "Sun": {"Venus", "Saturn"},
    "Moon": set(),
    "Mars": {"Mercury"},
    "Mercury": {"Moon"},
    "Jupiter": {"Mercury", "Venus"},
    "Venus": {"Sun", "Moon"},
    "Saturn": {"Sun", "Moon", "Mars"},
    "Rahu": {"Sun", "Moon", "Mars"},
    "Ketu": {"Sun", "Moon", "Saturn"},
}

OWN_SIGNS = {
    "Sun": {4}, "Moon": {3}, "Mars": {0, 7}, "Mercury": {2, 5},
    "Jupiter": {8, 11}, "Venus": {1, 6}, "Saturn": {9, 10},
    "Rahu": {10}, "Ketu": set(),
}

MOOLATRIKONA = {
    "Sun": (4, 0.0, 20.0), "Moon": (1, 3.0, 30.0),
    "Mars": (0, 0.0, 12.0), "Mercury": (5, 15.0, 20.0),
    "Jupiter": (8, 0.0, 10.0), "Venus": (6, 0.0, 15.0),
    "Saturn": (10, 0.0, 20.0),
    "Rahu": (2, 0.0, 30.0), "Ketu": (8, 0.0, 30.0),
}
EXALTATION = {
    "Sun": (0, 10.0), "Moon": (1, 3.0), "Mars": (9, 28.0),
    "Mercury": (5, 15.0), "Jupiter": (3, 5.0), "Venus": (11, 27.0),
    "Saturn": (6, 20.0), "Rahu": (1, None), "Ketu": (7, None),
}
DEBILITATION = {
    "Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11,
    "Jupiter": 9, "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1,
}

RELATION_LABELS = {
    "great_friend": "Голям приятел", "friend": "Приятел",
    "neutral": "Неутрален", "enemy": "Враг", "great_enemy": "Голям враг",
}
SPECIAL_LABELS = {
    "exaltation": "Екзалтация", "moolatrikona": "Мулатрикона",
    "own": "Собствен знак", "debilitation": "Дебилитация",
}


def _natural_relation(planet: str, other: str) -> str:
    if other in NATURAL_FRIENDS[planet]:
        return "friend"
    if other in NATURAL_ENEMIES[planet]:
        return "enemy"
    return "neutral"


def _temporary_relation(planet_sign: int, other_sign: int) -> str:
    counted_house = ((other_sign - planet_sign) % 12) + 1
    return "friend" if counted_house in {2, 3, 4, 10, 11, 12} else "enemy"


def _compound_relation(natural: str, temporary: str) -> str:
    return {
        ("friend", "friend"): "great_friend",
        ("friend", "enemy"): "neutral",
        ("neutral", "friend"): "friend",
        ("neutral", "enemy"): "enemy",
        ("enemy", "friend"): "neutral",
        ("enemy", "enemy"): "great_enemy",
    }[(natural, temporary)]


def _special_status(planet: str, sign: int, degree: float) -> str | None:
    if EXALTATION[planet][0] == sign:
        return "exaltation"
    mt = MOOLATRIKONA.get(planet)
    if mt and sign == mt[0] and mt[1] <= degree < mt[2]:
        return "moolatrikona"
    if sign in OWN_SIGNS[planet]:
        return "own"
    if DEBILITATION[planet] == sign:
        return "debilitation"
    return None


def _status_degree_details(planet: str, special: str | None) -> tuple[str | None, str | None]:
    if special not in {"exaltation", "debilitation"}:
        return None, None
    exact_degree = EXALTATION[planet][1]
    if exact_degree is None:
        return None, None
    degree_label = f"{int(exact_degree)}°" if float(exact_degree).is_integer() else f"{exact_degree:g}°"
    direction = "up" if special == "exaltation" else "down"
    return degree_label, direction


def build_relationship_table(rows: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    result = []
    for planet in RELATION_PLANETS:
        row = rows[planet]
        sign = int(row["sign_index"])
        degree = float(row["degree_in_sign"])
        lord = SIGN_LORDS[sign]
        natural = _natural_relation(planet, lord)
        temporary = _temporary_relation(sign, int(rows[lord]["sign_index"]))
        compound = _compound_relation(natural, temporary)
        special = _special_status(planet, sign, degree)
        status_degree, status_direction = _status_degree_details(planet, special)
        natural_label = "–" if special else RELATION_LABELS[natural]
        temporary_label = "–" if special else (
            "Временен приятел" if temporary == "friend" else "Временен враг"
        )
        result.append({
            "key": planet,
            "planet": PLANET_NAMES_BG[planet],
            "sign": SIGN_NAMES_BG[sign],
            "dispositor": PLANET_NAMES_BG[lord],
            "natural": natural_label,
            "temporary": temporary_label,
            "relationship": RELATION_LABELS[compound],
            "status": SPECIAL_LABELS[special] if special else RELATION_LABELS[compound],
            "status_key": special or compound,
            "status_degree": status_degree,
            "status_direction": status_direction,
        })
    return result


# BPHS/Parashari Bhinna Ashtakavarga contribution places. These fixed rows
# deliberately contain neither the lunar nodes nor the outer planets.
BAV_RULES = {
    "Sun": {
        "Sun": (1,2,4,7,8,9,10,11), "Moon": (3,6,10,11), "Mars": (1,2,4,7,8,9,10,11),
        "Mercury": (3,5,6,9,10,11,12), "Jupiter": (5,6,9,11), "Venus": (6,7,12),
        "Saturn": (1,2,4,7,8,9,10,11), "Ascendant": (3,4,6,10,11,12),
    },
    "Moon": {
        "Sun": (3,6,7,8,10,11), "Moon": (1,3,6,7,10,11), "Mars": (2,3,5,6,9,10,11),
        "Mercury": (1,3,4,5,7,8,10,11), "Jupiter": (1,4,7,8,10,11,12),
        "Venus": (3,4,5,7,9,10,11), "Saturn": (3,5,6,11), "Ascendant": (3,6,10,11),
    },
    "Mars": {
        "Sun": (3,5,6,10,11), "Moon": (3,6,11), "Mars": (1,2,4,7,8,10,11),
        "Mercury": (3,5,6,11), "Jupiter": (6,10,11,12), "Venus": (6,8,11,12),
        "Saturn": (1,4,7,8,9,10,11), "Ascendant": (1,3,6,10,11),
    },
    "Mercury": {
        "Sun": (5,6,9,11,12), "Moon": (2,4,6,8,10,11), "Mars": (1,2,4,7,8,9,10,11),
        "Mercury": (1,3,5,6,9,10,11,12), "Jupiter": (6,8,11,12),
        "Venus": (1,2,3,4,5,8,9,11), "Saturn": (1,2,4,7,8,9,10,11),
        "Ascendant": (1,2,4,6,8,10,11),
    },
    "Jupiter": {
        "Sun": (1,2,3,4,7,8,9,10,11), "Moon": (2,5,7,9,11), "Mars": (1,2,4,7,8,10,11),
        "Mercury": (1,2,4,5,6,9,10,11), "Jupiter": (1,2,3,4,7,8,10,11),
        "Venus": (2,5,6,9,10,11), "Saturn": (3,5,6,12), "Ascendant": (1,2,4,5,6,7,9,10,11),
    },
    "Venus": {
        "Sun": (8,11,12), "Moon": (1,2,3,4,5,8,9,11,12), "Mars": (3,5,6,9,11,12),
        "Mercury": (3,5,6,9,11), "Jupiter": (5,8,9,10,11), "Venus": (1,2,3,4,5,8,9,10,11),
        "Saturn": (3,4,5,8,9,10,11), "Ascendant": (1,2,3,4,5,8,9,11),
    },
    "Saturn": {
        "Sun": (1,2,4,7,8,10,11), "Moon": (3,6,11), "Mars": (3,5,6,10,11,12),
        "Mercury": (6,8,9,10,11,12), "Jupiter": (5,6,11,12), "Venus": (6,11,12),
        "Saturn": (3,5,6,11), "Ascendant": (1,3,4,6,10,11),
    },
}


def build_ashtakavarga(rows: dict[str, dict[str, object]]) -> dict[str, object]:
    bav_rows = []
    sav = [0] * 12
    for target in CLASSICAL:
        bindus = [0] * 12
        for source in ASHTAKA_SOURCES:
            source_sign = int(rows[source]["sign_index"])
            for place in BAV_RULES[target][source]:
                bindus[(source_sign + place - 1) % 12] += 1
        for index, value in enumerate(bindus):
            sav[index] += value
        bav_rows.append({
            "key": target,
            "planet": PLANET_NAMES_BG[target],
            "short": ASHTAKA_SHORT_BG[target],
            "bindus": bindus,
            "total": sum(bindus),
        })
    return {
        "signs": [f"{name} ({index + 1})" for index, name in enumerate(SIGN_NAMES_BG)],
        "rows": bav_rows,
        "sav": sav,
        "sav_total": sum(sav),
    }
