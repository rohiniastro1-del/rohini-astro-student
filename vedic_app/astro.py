from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path
from threading import RLock

import swisseph as swe
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo

from vedic_app.chart import build_sign_sequence, render_north_chart, render_transit_overlay_chart
from vedic_app.dasha import TROPICAL_YEAR_DAYS, build_vimshottari_dasha
from vedic_app.chara_dasha import build_chara_dasha_rao
from vedic_app.data import (
    CITY_LOOKUP,
    NAKSHATRA_NAMES_BG,
    NODE_MODE_LABELS,
    navamsha_sign_index,
    PLANET_LABELS_BG,
    PLANET_JYOTISH_NAMES_BG,
    PLANET_NAMES_BG,
    PLANET_ORDER,
    SIGN_NAMES_BG,
)
from vedic_app.divisional import (
    build_divisional_chart_registry,
    calculate_divisional_placement,
    DEFAULT_DIVISIONAL_CHART_CODE,
    DIVISIONAL_CHART_OPTIONS,
)
from vedic_app.jaimini import build_jaimini_bundle
from vedic_app.panchanga import build_panchanga
from vedic_app.strengths import build_ashtakavarga, build_relationship_table


NAKSHATRA_ARCSECONDS = Decimal("48000")

SWE_BODY_MAP = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}

OUTER_PLANET_KEYS = ("Uranus", "Neptune", "Pluto")


FIELD_NAMES = {
    "natal": {
        "date": "birthDate",
        "time": "birthTime",
        "city": "cityName",
        "latitude_degrees": "latitudeDegrees",
        "latitude_minutes": "latitudeMinutes",
        "latitude_seconds": "latitudeSeconds",
        "latitude_hemisphere": "latitudeHemisphere",
        "longitude_degrees": "longitudeDegrees",
        "longitude_minutes": "longitudeMinutes",
        "longitude_seconds": "longitudeSeconds",
        "longitude_hemisphere": "longitudeHemisphere",
        "timezone_mode": "timezoneMode",
        "manual_tz_sign": "manualTzSign",
        "manual_tz_hours": "manualTzHours",
        "manual_tz_minutes": "manualTzMinutes",
        "node_mode": "nodeMode",
    },
    "transit": {
        "date": "transitDate",
        "time": "transitTime",
        "city": "transitCityName",
        "latitude_degrees": "transitLatitudeDegrees",
        "latitude_minutes": "transitLatitudeMinutes",
        "latitude_seconds": "transitLatitudeSeconds",
        "latitude_hemisphere": "transitLatitudeHemisphere",
        "longitude_degrees": "transitLongitudeDegrees",
        "longitude_minutes": "transitLongitudeMinutes",
        "longitude_seconds": "transitLongitudeSeconds",
        "longitude_hemisphere": "transitLongitudeHemisphere",
        "timezone_mode": "transitTimezoneMode",
        "manual_tz_sign": "transitManualTzSign",
        "manual_tz_hours": "transitManualTzHours",
        "manual_tz_minutes": "transitManualTzMinutes",
        "node_mode": "transitNodeMode",
    },
}

TIMEZONE_FINDER = TimezoneFinder()
EPHEMERIS_FILE_PATTERNS = ("*.se1", "*.se2", "*.semo", "*.sepl")
CORE_DE441_FILES = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
SWE_LOCK = RLock()


class CalculationError(ValueError):
    """Raised when form data cannot be parsed or calculated."""


def _discover_ephemeris_directory() -> Path | None:
    base_dir = Path(__file__).resolve().parent
    candidate_dirs = (
        base_dir / "ephe",
        base_dir.parent / "ephe",
        base_dir.parent / ".ephe",
    )
    for candidate in candidate_dirs:
        if not candidate.is_dir():
            continue
        if any(candidate.glob(pattern) for pattern in EPHEMERIS_FILE_PATTERNS):
            return candidate
    return None


def _iter_ephemeris_files(directory: Path) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for pattern in EPHEMERIS_FILE_PATTERNS:
        for candidate in directory.glob(pattern):
            if candidate.is_file() and candidate not in seen:
                seen.add(candidate)
                files.append(candidate)
    return files


def _validate_de441_files(directory: Path) -> None:
    """Refuse an incomplete or older ephemeris set for every calculation."""
    missing = [name for name in CORE_DE441_FILES if not (directory / name).is_file()]
    invalid = []
    for name in CORE_DE441_FILES:
        path = directory / name
        if not path.is_file():
            continue
        header = path.read_bytes()[:220].decode("ascii", errors="ignore")
        if "SWISSEPH  3" not in header or "DE441" not in header:
            invalid.append(name)
    if missing or invalid:
        details = []
        if missing:
            details.append("липсват: " + ", ".join(missing))
        if invalid:
            details.append("не са DE441: " + ", ".join(invalid))
        raise RuntimeError("Невалиден комплект ефемериди на Рохини Астро — " + "; ".join(details))


def _is_ascii_safe_path(path: Path) -> bool:
    try:
        str(path).encode("ascii")
    except UnicodeEncodeError:
        return False
    return True


def _ephemeris_cache_candidates() -> list[Path]:
    candidates = [Path(tempfile.gettempdir())]
    if os.name == "nt":
        candidates.extend(
            [
                Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Temp",
                Path(r"C:\Temp"),
            ]
        )
    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        text = str(candidate)
        if text in seen:
            continue
        seen.add(text)
        unique_candidates.append(candidate)
    return unique_candidates


def _prepare_ascii_ephemeris_mirror(directory: Path) -> Path | None:
    ephemeris_files = _iter_ephemeris_files(directory)
    if not ephemeris_files:
        return None

    digest = hashlib.sha1(str(directory).encode("utf-8")).hexdigest()[:12]
    for root in _ephemeris_cache_candidates():
        if not _is_ascii_safe_path(root):
            continue
        target = root / "rohini_swe_ephe" / digest
        try:
            target.mkdir(parents=True, exist_ok=True)
            for source_file in ephemeris_files:
                target_file = target / source_file.name
                # Атомарно копиране: първо в .tmp, после rename, за да не остават
                # половинчати .se1 файлове при прекъснат старт.
                if (
                    not target_file.exists()
                    or target_file.stat().st_size != source_file.stat().st_size
                ):
                    tmp_file = target / (source_file.name + ".tmp")
                    shutil.copy2(source_file, tmp_file)
                    os.replace(tmp_file, target_file)
        except OSError:
            continue
        # Пълнота: всички файлове трябва да са налични и с точния размер.
        if all(
            (target / f.name).is_file() and (target / f.name).stat().st_size == f.stat().st_size
            for f in ephemeris_files
        ):
            return target
    return None


def _set_and_validate_ephemeris_path(directory: Path) -> bool:
    swe.set_ephe_path(str(directory))
    try:
        # Проверяваме Слънце, Луна и истинския възел, за да сме сигурни, че
        # са налични и sepl_18.se1, и semo_18.se1 (не само единият файл).
        for body in (swe.SUN, swe.MOON, swe.TRUE_NODE):
            _, retflags = swe.calc_ut(swe.julday(2000, 1, 1, 0.0), body, swe.FLG_SWIEPH)
            if not (retflags & swe.FLG_SWIEPH) or (retflags & swe.FLG_MOSEPH):
                return False
    except Exception:
        return False
    return True


def _requested_swieph_backend_warning(body_key: str, requested_flags: int, retflags: int) -> str | None:
    if not requested_flags & swe.FLG_SWIEPH:
        return None
    if retflags & swe.FLG_SWIEPH and not retflags & swe.FLG_MOSEPH:
        return None

    body_name = PLANET_NAMES_BG.get(body_key, body_key)
    if retflags & swe.FLG_MOSEPH:
        return (
            f"Предупреждение: за {body_name} е поискан Swiss Ephemeris (FLG_SWIEPH), "
            f"но swe.calc_ut() върна Moshier backend (FLG_MOSEPH, retflags={retflags}). "
            "Това е fallback, а не реално SWIEPH изчисление. Проверете пътя до ephe файловете "
            "и дали ASCII-safe копието е достъпно."
        )

    return (
        f"Предупреждение: за {body_name} е поискан Swiss Ephemeris (FLG_SWIEPH), "
        f"но swe.calc_ut() върна различен backend (retflags={retflags})."
    )


def _configure_ephemeris() -> str | None:
    directory = _discover_ephemeris_directory()
    if directory is None:
        raise RuntimeError("Липсват задължителните ефемеридни файлове DE441 на Рохини Астро.")
    _validate_de441_files(directory)

    if _set_and_validate_ephemeris_path(directory):
        return str(directory)

    # Windows: кирилицата в пътя кара Swiss Ephemeris да не намира .se1 файловете
    # и да пада тихо на Moshier. Затова ползваме ASCII-safe копие.
    mirror_directory = _prepare_ascii_ephemeris_mirror(directory)
    if mirror_directory is not None and _set_and_validate_ephemeris_path(mirror_directory):
        return str(mirror_directory)

    # Fail-fast: не продължаваме тихо с Moshier.
    raise RuntimeError(
        "Не успя да се зареди Swiss Ephemeris (SWIEPH) за Рохини Астро. "
        "Проверете ephe файловете и достъпа до ASCII-safe копието."
    )


EPHEMERIS_DIRECTORY = _configure_ephemeris()


def _ensure_swe_thread_context() -> None:
    """pyswisseph пази ephe пътя и айянамшата per-thread; Flask worker threads
    трябва да си ги зададат, иначе calc_ut() пада тихо на Moshier."""
    if EPHEMERIS_DIRECTORY:
        swe.set_ephe_path(EPHEMERIS_DIRECTORY)
    swe.set_sid_mode(swe.SIDM_LAHIRI)


def default_form_values() -> dict[str, str]:
    now_local = datetime.now(ZoneInfo("Europe/Sofia"))
    current_date = now_local.strftime("%Y-%m-%d")
    current_time = now_local.strftime("%H:%M:%S")
    values: dict[str, str] = {}
    values.update(
        _default_chart_form_values(
            "natal",
            "Велико Търново",
            date_value=current_date,
            time_value=current_time,
        )
    )
    values.update(
        _default_chart_form_values(
            "transit",
            "Велико Търново",
            date_value=current_date,
            time_value=current_time,
        )
    )
    values["showOuterPlanets"] = ""
    values["combustionOrbDegrees"] = "5"
    return values


def _angular_separation(first: float, second: float) -> float:
    """Smallest separation on the 360-degree circle (0..180)."""
    difference = abs(_normalize_degrees(first) - _normalize_degrees(second))
    return min(difference, 360.0 - difference)


COMBUSTIBLE_PLANET_KEYS = frozenset({
    "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
    "Uranus", "Neptune", "Pluto",
})


def _is_planet_combust(
    key: str,
    longitude: float,
    sun_longitude: float,
    orb: float,
) -> bool:
    """Use the inclusive circular interval on both sides of the Sun."""
    return key in COMBUSTIBLE_PLANET_KEYS and _angular_separation(longitude, sun_longitude) <= orb


PLANETARY_WAR_KEYS = frozenset({"Mercury", "Venus", "Mars", "Jupiter", "Saturn"})
ECLIPSE_MARKER_KEYS = frozenset({"Sun", "Moon"})

GANDANTA_WATER_SIGNS = (11, 3, 7)
GANDANTA_FIRE_SIGNS = (0, 4, 8)
GANDANTA_WATER_START = 26 + 40 / 60  # 26°40′00″
GANDANTA_FIRE_END = 3 + 20 / 60  # 3°20′00″


def is_gandanta(sidereal_longitude: float) -> bool:
    longitude = sidereal_longitude % 360.0
    sign = int(longitude // 30)
    degree = longitude % 30.0
    if sign in GANDANTA_WATER_SIGNS and degree >= GANDANTA_WATER_START:
        return True
    if sign in GANDANTA_FIRE_SIGNS and degree < GANDANTA_FIRE_END:
        return True
    return False


TARA_NAMES_BG = {
    1: "Джанма",
    2: "Сампат",
    3: "Випат",
    4: "Кшема",
    5: "Пратяк",
    6: "Садхака",
    7: "Найдхана",
    8: "Митра",
    9: "Парама Митра",
}


def navatara(janma_nakshatra_index: int, current_nakshatra_index: int) -> dict:
    count = ((current_nakshatra_index - janma_nakshatra_index + 27) % 27) + 1
    tara_number = ((count - 1) % 9) + 1
    navatara_cycle = ((count - 1) // 9) + 1
    return {
        "count": count,
        "tara_number": tara_number,
        "tara_name": TARA_NAMES_BG[tara_number],
        "navatara_cycle": navatara_cycle,
    }


def _apply_planetary_war(rows_by_key: dict[str, dict]) -> None:
    """Annotate classical planetary wars without changing row order."""
    for row in rows_by_key.values():
        row["is_planetary_war"] = False
        row["planetary_war_result"] = None
        row["planetary_war_opponents"] = []
        row["planetary_war_distance"] = None

    candidates = [rows_by_key[key] for key in PLANETARY_WAR_KEYS if key in rows_by_key]
    outcomes: dict[str, dict[str, list]] = {
        row["key"]: {"wins": [], "losses": [], "distances": []}
        for row in candidates
    }
    for index, first in enumerate(candidates):
        for second in candidates[index + 1:]:
            if int(first["sign_index"]) != int(second["sign_index"]):
                continue
            first_longitude = float(first["longitude"])
            second_longitude = float(second["longitude"])
            distance = abs(first_longitude - second_longitude)
            if distance >= 1.0 - 1e-12:
                continue
            winner, loser = (
                (first, second)
                if first_longitude < second_longitude
                else (second, first)
            )
            outcomes[winner["key"]]["wins"].append(loser["label"])
            outcomes[loser["key"]]["losses"].append(winner["label"])
            outcomes[winner["key"]]["distances"].append(distance)
            outcomes[loser["key"]]["distances"].append(distance)

    for row in candidates:
        outcome = outcomes[row["key"]]
        if not outcome["wins"] and not outcome["losses"]:
            continue
        row["is_planetary_war"] = True
        # With a rare three-planet cluster, losing any pair is the stronger affliction.
        row["planetary_war_result"] = "loser" if outcome["losses"] else "winner"
        row["planetary_war_opponents"] = outcome["losses"] + outcome["wins"]
        row["planetary_war_distance"] = min(outcome["distances"])


@lru_cache(maxsize=1024)
def _global_eclipses_around_julian_day(julian_day_number: int) -> tuple[tuple[str, float], ...]:
    """Return the nearest global solar/lunar eclipses around a UT day."""
    anchor = float(julian_day_number) + 0.5
    epsilon = 1e-6
    with SWE_LOCK:
        solar_before = swe.sol_eclipse_when_glob(
            anchor - epsilon, swe.FLG_SWIEPH, 0, True
        )[1][0]
        solar_after = swe.sol_eclipse_when_glob(
            anchor + epsilon, swe.FLG_SWIEPH, 0, False
        )[1][0]
        lunar_before = swe.lun_eclipse_when(
            anchor - epsilon, swe.FLG_SWIEPH, 0, True
        )[1][0]
        lunar_after = swe.lun_eclipse_when(
            anchor + epsilon, swe.FLG_SWIEPH, 0, False
        )[1][0]
    return (
        ("solar", float(solar_before)),
        ("solar", float(solar_after)),
        ("lunar", float(lunar_before)),
        ("lunar", float(lunar_after)),
    )


def _eclipse_marker_for_datetime(local_dt: datetime, jd_ut: float) -> dict | None:
    """Classify the chart's local calendar day relative to an eclipse."""
    candidates: list[tuple[int, float, str, datetime]] = []
    for kind, eclipse_jd in _global_eclipses_around_julian_day(int(jd_ut)):
        eclipse_local = _utc_datetime_from_jd(eclipse_jd).astimezone(local_dt.tzinfo)
        day_offset = (local_dt.date() - eclipse_local.date()).days
        candidates.append((abs(day_offset), abs(jd_ut - eclipse_jd), kind, eclipse_local))
    distance, _instant_distance, kind, eclipse_local = min(candidates)
    if distance > 7:
        return None
    state = "day" if distance == 0 else "near" if distance == 1 else "window"
    return {
        "state": state,
        "day_distance": distance,
        "kind": kind,
        "kind_label": "Слънчево" if kind == "solar" else "Лунно",
        "local_date": eclipse_local.strftime("%d.%m.%Y"),
    }


def _default_chart_form_values(
    prefix: str,
    city_name: str,
    date_value: str = "",
    time_value: str = "",
) -> dict[str, str]:
    city = CITY_LOOKUP[city_name]
    lat_deg, lat_min, lat_sec = decimal_to_dms(city["lat"])
    lon_deg, lon_min, lon_sec = decimal_to_dms(city["lon"])
    names = FIELD_NAMES[prefix]
    return {
        names["date"]: date_value,
        names["time"]: time_value,
        names["city"]: city_name,
        names["latitude_degrees"]: str(lat_deg),
        names["latitude_minutes"]: str(lat_min),
        names["latitude_seconds"]: str(lat_sec),
        names["latitude_hemisphere"]: "N",
        names["longitude_degrees"]: str(lon_deg),
        names["longitude_minutes"]: str(lon_min),
        names["longitude_seconds"]: str(lon_sec),
        names["longitude_hemisphere"]: "E",
        names["timezone_mode"]: "auto",
        names["manual_tz_sign"]: "+",
        names["manual_tz_hours"]: "2",
        names["manual_tz_minutes"]: "0",
        names["node_mode"]: "true",
    }


def decimal_to_degree_minutes(value: float) -> tuple[int, int]:
    absolute = abs(value)
    degrees = int(absolute)
    minutes = int(round((absolute - degrees) * 60))
    if minutes == 60:
        degrees += 1
        minutes = 0
    return degrees, minutes


def decimal_to_dms(value: float) -> tuple[int, int, int]:
    total_seconds = int(round(abs(value) * 3600))
    degrees, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return degrees, minutes, seconds


def _format_coordinate_label(latitude: float, longitude: float) -> str:
    lat_deg, lat_min, lat_sec = decimal_to_dms(latitude)
    lon_deg, lon_min, lon_sec = decimal_to_dms(longitude)
    lat_hemi = "N" if latitude >= 0 else "S"
    lon_hemi = "E" if longitude >= 0 else "W"
    return (
        f"{lat_deg:02d}° {lat_min:02d}' {lat_sec:02d}\" {lat_hemi}, "
        f"{lon_deg:02d}° {lon_min:02d}' {lon_sec:02d}\" {lon_hemi} "
        f"({latitude:.4f}°, {longitude:.4f}°)"
    )


def _field_name(prefix: str, key: str) -> str:
    return FIELD_NAMES[prefix][key]


def _get_form_value(form_data: dict[str, str], prefix: str, key: str) -> str:
    return form_data.get(_field_name(prefix, key), "").strip()


def _normalize_degrees(value: float) -> float:
    normalized = value % 360.0
    return 0.0 if normalized == 360.0 else normalized


def _to_decimal(value: float) -> Decimal:
    return Decimal(str(value))


def _round_to_arcseconds(value: float) -> int:
    """Закръгля дължина (градуси) до най-близката цяла дъгова секунда (round-half-up).

    Междинното квантуване до микро-дъгови секунди поглъща шума от
    floating-point представянето около полусекундните граници (напр.
    ``59.5 / 3600`` като float се умножава обратно до ``59.4999999999999972``,
    което иначе би закръглило надолу вместо нагоре).
    """
    arcseconds = (_to_decimal(value) * Decimal("3600")).quantize(Decimal("0.000001"))
    return int(arcseconds.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _degree_fraction_to_dms(value: float) -> tuple[int, int, int]:
    total_arcseconds = _round_to_arcseconds(value)
    max_arcseconds = 30 * 3600 - 1
    total_arcseconds = min(total_arcseconds, max_arcseconds)
    degrees, remainder = divmod(total_arcseconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return degrees, minutes, seconds


def _format_dms(value: float) -> str:
    degrees, minutes, seconds = _degree_fraction_to_dms(value)
    return f"{degrees:02d}° {minutes:02d}' {seconds:02d}\""


def _full_degree_dms(value: float) -> str:
    normalized = _normalize_degrees(value)
    total_arcseconds = _round_to_arcseconds(normalized)
    if total_arcseconds >= 360 * 3600:
        total_arcseconds = 0
    degrees, remainder = divmod(total_arcseconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{degrees:03d}° {minutes:02d}' {seconds:02d}\""


def _zodiac_details(longitude: float) -> dict[str, object]:
    normalized = _normalize_degrees(longitude)
    sign_index = int(normalized // 30)
    degree_in_sign = normalized - (sign_index * 30)
    total_arcseconds = _to_decimal(normalized) * Decimal("3600")
    nak_index = int((total_arcseconds // NAKSHATRA_ARCSECONDS).to_integral_value(rounding=ROUND_FLOOR))
    nak_offset = total_arcseconds % NAKSHATRA_ARCSECONDS
    pada = int((nak_offset / Decimal("12000")).to_integral_value(rounding=ROUND_FLOOR)) + 1
    nakshatra_degree = float(nak_offset / Decimal("3600"))
    return {
        "longitude": normalized,
        "sign_index": sign_index,
        "sign_number": sign_index + 1,
        "sign_name": SIGN_NAMES_BG[sign_index],
        "degree_in_sign": degree_in_sign,
        "degree_dms": _format_dms(degree_in_sign),
        "nakshatra": NAKSHATRA_NAMES_BG[nak_index],
        "nakshatra_degree_dms": _format_dms(nakshatra_degree),
        "pada": pada,
    }


def _navamsha_sign(sign_index: int, degree_in_sign: float) -> int:
    return navamsha_sign_index(sign_index, degree_in_sign)


def _dms_to_decimal(
    degrees_text: str,
    minutes_text: str,
    seconds_text: str,
    hemisphere: str,
    axis: str,
) -> float:
    try:
        degrees = int(degrees_text)
        minutes = int(minutes_text)
        seconds = int(seconds_text or "0")
    except ValueError as exc:
        raise CalculationError("Координатите трябва да са цели числа в градуси, минути и секунди.") from exc

    if minutes < 0 or minutes >= 60:
        raise CalculationError("Минутите в координатите трябва да са между 0 и 59.")
    if seconds < 0 or seconds >= 60:
        raise CalculationError("Секундите в координатите трябва да са между 0 и 59.")

    limit = 90 if axis == "lat" else 180
    if degrees < 0 or degrees > limit:
        axis_label = "ширина" if axis == "lat" else "дължина"
        raise CalculationError(f"Градусите по {axis_label} трябва да са между 0 и {limit}.")

    value = degrees + (minutes / 60) + (seconds / 3600)
    if hemisphere in {"S", "W"}:
        value *= -1
    return value


def _parse_manual_offset(sign_text: str, hours_text: str, minutes_text: str) -> int:
    try:
        hours = int(hours_text)
        minutes = int(minutes_text)
    except ValueError as exc:
        raise CalculationError("Ръчната часова зона трябва да е в цели часове и минути.") from exc

    if hours < 0 or hours > 14 or minutes < 0 or minutes >= 60:
        raise CalculationError("Ръчната часова зона е извън позволения диапазон.")

    total = hours * 60 + minutes
    return -total if sign_text == "-" else total


def _format_utc_offset(total_minutes: int) -> str:
    sign = "+" if total_minutes >= 0 else "-"
    absolute = abs(total_minutes)
    hours, minutes = divmod(absolute, 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def _local_roundtrip_matches(local_candidate: datetime, naive_local: datetime, tz_info: ZoneInfo) -> bool:
    roundtrip = local_candidate.astimezone(timezone.utc).astimezone(tz_info).replace(tzinfo=None)
    return roundtrip == naive_local


def _resolve_auto_local_datetime(
    naive_local: datetime,
    tz_info: ZoneInfo,
) -> tuple[datetime, str | None]:
    early = naive_local.replace(tzinfo=tz_info, fold=0)
    late = naive_local.replace(tzinfo=tz_info, fold=1)

    early_valid = _local_roundtrip_matches(early, naive_local, tz_info)
    late_valid = _local_roundtrip_matches(late, naive_local, tz_info)

    if early_valid and late_valid:
        if early.utcoffset() != late.utcoffset():
            return early, (
                "Часът попада в двусмислен момент около смяна на лятно/зимно време. "
                "Автоматично е избран по-ранният валиден локален час; при нужда коригирай зоната ръчно."
            )
        return early, None

    if early_valid:
        return early, None

    if late_valid:
        return late, (
            "Часът е разрешен по късния DST вариант; при нужда коригирай зоната ръчно."
        )

    raise CalculationError(
        "Автоматичното определяне на часовата зона попадна в невалиден локален час "
        "около смяна на лятно/зимно време. Задай часовата зона ръчно за тази карта."
    )


def _resolve_timezone(
    date_text: str,
    time_text: str,
    latitude: float,
    longitude: float,
    timezone_mode: str,
    manual_offset_minutes: int,
    preferred_timezone: str | None,
) -> tuple[datetime, datetime, dict[str, str]]:
    try:
        naive_local = datetime.fromisoformat(f"{date_text}T{time_text}")
    except ValueError as exc:
        raise CalculationError("Датата и часът трябва да са попълнени коректно.") from exc

    if timezone_mode == "manual":
        tz_info = timezone(timedelta(minutes=manual_offset_minutes))
        aware_local = naive_local.replace(tzinfo=tz_info)
        offset_label = _format_utc_offset(manual_offset_minutes)
        timezone_summary = {
            "mode": "Ръчно",
            "name": offset_label,
            "offset_label": offset_label,
            "source": "Ръчно въведена часова зона.",
        }
    else:
        timezone_name = TIMEZONE_FINDER.timezone_at(lat=latitude, lng=longitude) or preferred_timezone
        if not timezone_name:
            timezone_name = "Europe/Sofia"
        tz_info = ZoneInfo(timezone_name)
        aware_local, note = _resolve_auto_local_datetime(naive_local, tz_info)
        offset_minutes = int((aware_local.utcoffset() or timedelta()).total_seconds() // 60)
        timezone_summary = {
            "mode": "Автоматично",
            "name": timezone_name,
            "offset_label": _format_utc_offset(offset_minutes),
            "source": (
                "Часовата зона е определена по координати и историческите правила за датата."
                if not note
                else f"Часовата зона е определена по координати и историческите правила за датата. {note}"
            ),
        }

    aware_utc = aware_local.astimezone(timezone.utc)
    return aware_local, aware_utc, timezone_summary


def _julian_day(aware_utc: datetime) -> float:
    hour_fraction = (
        aware_utc.hour
        + (aware_utc.minute / 60)
        + (aware_utc.second / 3600)
        + (aware_utc.microsecond / 3_600_000_000)
    )
    return swe.julday(aware_utc.year, aware_utc.month, aware_utc.day, hour_fraction)


def _traditional_sidereal_ascendant(jd_ut: float, latitude: float, longitude: float) -> tuple[float, float]:
    # JHora-style lagna matches better when we take the tropical ascendant
    # and subtract the selected ayanamsha, instead of relying on direct
    # sidereal house output from Swiss Ephemeris.
    ayanamsha = swe.get_ayanamsa_ut(jd_ut)
    _, ascmc_tropical = swe.houses_ex(jd_ut, latitude, longitude, b"P", 0)
    asc_longitude = _normalize_degrees(ascmc_tropical[0] - ayanamsha)
    return asc_longitude, ayanamsha


def calculate_lagna_sign(form_data: dict[str, str], chart_code: str = "D1", prefix: str = "natal") -> int:
    """Връща 1-базиран знак на асцендента за D1, поддържана варга или Джаймини."""
    date_text = _get_form_value(form_data, prefix, "date")
    time_text = _get_form_value(form_data, prefix, "time")
    if not date_text or not time_text:
        raise CalculationError("Въведи дата и точен час.")

    city_name = _get_form_value(form_data, prefix, "city")
    city = CITY_LOOKUP.get(city_name) if city_name else None
    latitude = _dms_to_decimal(
        _get_form_value(form_data, prefix, "latitude_degrees"),
        _get_form_value(form_data, prefix, "latitude_minutes"),
        _get_form_value(form_data, prefix, "latitude_seconds") or "0",
        _get_form_value(form_data, prefix, "latitude_hemisphere") or "N",
        "lat",
    )
    longitude = _dms_to_decimal(
        _get_form_value(form_data, prefix, "longitude_degrees"),
        _get_form_value(form_data, prefix, "longitude_minutes"),
        _get_form_value(form_data, prefix, "longitude_seconds") or "0",
        _get_form_value(form_data, prefix, "longitude_hemisphere") or "E",
        "lon",
    )
    manual_offset_minutes = _parse_manual_offset(
        _get_form_value(form_data, prefix, "manual_tz_sign") or "+",
        _get_form_value(form_data, prefix, "manual_tz_hours") or "0",
        _get_form_value(form_data, prefix, "manual_tz_minutes") or "0",
    )
    timezone_mode = _get_form_value(form_data, prefix, "timezone_mode") or "auto"
    preferred_timezone = city["timezone"] if city else None
    _local_dt, utc_dt, _timezone_summary = _resolve_timezone(
        date_text, time_text, latitude, longitude, timezone_mode, manual_offset_minutes, preferred_timezone
    )
    with SWE_LOCK:
        _ensure_swe_thread_context()
        asc_longitude, _ayanamsha = _traditional_sidereal_ascendant(
            _julian_day(utc_dt), latitude, longitude
        )
    details = _zodiac_details(asc_longitude)
    normalized_code = str(chart_code or "D1").upper()
    if normalized_code in {"D1", "JAI"}:
        return int(details["sign_number"])
    destination = calculate_divisional_placement(
        normalized_code, int(details["sign_index"]), float(details["degree_in_sign"])
    )
    if destination is None:
        raise CalculationError(f"Неподдържана карта: {normalized_code}.")
    return destination + 1


def _planet_chart_code(key: str, retrograde: bool) -> str:
    label = PLANET_LABELS_BG[key]
    if key in OUTER_PLANET_KEYS:
        return label
    return f"({label})" if retrograde else label


def _ephemeris_source_summary(retflags: list[int]) -> dict[str, str]:
    if retflags and all(flag & swe.FLG_SWIEPH for flag in retflags):
        detail = "Използват се файловете на Swiss Ephemeris."
        if EPHEMERIS_DIRECTORY:
            detail = f"{detail} Път: {EPHEMERIS_DIRECTORY}"
        return {"label": "Swiss Ephemeris", "detail": detail}

    if any(flag & swe.FLG_MOSEPH for flag in retflags):
        detail = (
            "Поискан е Swiss Ephemeris (FLG_SWIEPH), но реалният backend е Moshier "
            "(FLG_MOSEPH). Това е fallback: Swiss Ephemeris файловете не са достъпни през "
            "активния път или backend-ът е отказал да ги използва."
        )
        if EPHEMERIS_DIRECTORY:
            detail = f"{detail} Активен път: {EPHEMERIS_DIRECTORY}"
        return {"label": "Moshier fallback", "detail": detail}

    if any(flag & swe.FLG_JPLEPH for flag in retflags):
        return {"label": "JPL ephemeris", "detail": "Използва се JPL ephemeris източник."}

    return {
        "label": "Неуточнен източник",
        "detail": "Източникът на епхемеридите не можа да бъде определен еднозначно.",
    }


def _build_chart_payload(
    title: str,
    subtitle: str,
    asc_sign_index: int,
    points: list[dict[str, object]],
    house_key: str,
    sign_key: str,
    aria_title: str | None = None,
) -> dict[str, object]:
    sign_sequence = build_sign_sequence(asc_sign_index + 1)
    houses = []
    for house_number in range(1, 13):
        sign_number = sign_sequence[house_number]
        items = [point["chart_code"] for point in points if point[house_key] == house_number]
        houses.append({"house": house_number, "sign_number": sign_number, "items": items})
    sign_items = {
        sign_number: [point["chart_code"] for point in points if point[sign_key] == sign_number]
        for sign_number in range(1, 13)
    }
    return {
        "title": title,
        "subtitle": subtitle,
        "aria_title": aria_title or title,
        "houses": houses,
        "sign_items": sign_items,
    }


def _calculate_chart(
    form_data: dict[str, str],
    prefix: str,
    d1_subtitle: str,
    include_d9: bool,
) -> dict[str, object]:
    try:
        combustion_orb = float(str(form_data.get("combustionOrbDegrees", "5")).replace(",", "."))
    except (TypeError, ValueError) as exc:
        raise CalculationError("Градусът на изгаряне трябва да бъде число.") from exc
    # Migrate the stale zero saved by early desktop builds.  The user-facing
    # default is 5 degrees; a zero value made valid conjunctions appear as if
    # combustion were broken.
    if combustion_orb <= 0.0:
        combustion_orb = 5.0
        form_data["combustionOrbDegrees"] = "5"
    if combustion_orb > 30.0:
        raise CalculationError("Градусът на изгаряне трябва да бъде между 0° и 30°.")
    date_text = _get_form_value(form_data, prefix, "date")
    time_text = _get_form_value(form_data, prefix, "time")
    if not date_text or not time_text:
        chart_label = "рождената" if prefix == "natal" else "транзитната"
        raise CalculationError(f"Въведи дата и точен час за {chart_label} карта.")

    city_name = _get_form_value(form_data, prefix, "city")
    city = CITY_LOOKUP.get(city_name) if city_name else None

    latitude = _dms_to_decimal(
        _get_form_value(form_data, prefix, "latitude_degrees"),
        _get_form_value(form_data, prefix, "latitude_minutes"),
        _get_form_value(form_data, prefix, "latitude_seconds") or "0",
        _get_form_value(form_data, prefix, "latitude_hemisphere") or "N",
        "lat",
    )
    longitude = _dms_to_decimal(
        _get_form_value(form_data, prefix, "longitude_degrees"),
        _get_form_value(form_data, prefix, "longitude_minutes"),
        _get_form_value(form_data, prefix, "longitude_seconds") or "0",
        _get_form_value(form_data, prefix, "longitude_hemisphere") or "E",
        "lon",
    )
    manual_offset_minutes = _parse_manual_offset(
        _get_form_value(form_data, prefix, "manual_tz_sign") or "+",
        _get_form_value(form_data, prefix, "manual_tz_hours") or "0",
        _get_form_value(form_data, prefix, "manual_tz_minutes") or "0",
    )

    timezone_mode = _get_form_value(form_data, prefix, "timezone_mode") or "auto"
    preferred_timezone = city["timezone"] if city else None
    local_dt, utc_dt, timezone_summary = _resolve_timezone(
        date_text,
        time_text,
        latitude,
        longitude,
        timezone_mode,
        manual_offset_minutes,
        preferred_timezone,
    )

    with SWE_LOCK:
        _ensure_swe_thread_context()
        jd_ut = _julian_day(utc_dt)
        # JHora-style longitude tables match Swiss Ephemeris best when using
        # true geocentric positions instead of apparent positions.
        flags = swe.FLG_SIDEREAL | swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_TRUEPOS
        node_mode = _get_form_value(form_data, prefix, "node_mode") or "true"
        node_id = swe.TRUE_NODE if node_mode == "true" else swe.MEAN_NODE

        asc_longitude, ayanamsha = _traditional_sidereal_ascendant(jd_ut, latitude, longitude)
        asc_details = _zodiac_details(asc_longitude)
        asc_nav_sign = _navamsha_sign(asc_details["sign_index"], asc_details["degree_in_sign"])

        points: list[dict[str, object]] = []
        rows_by_key: dict[str, dict[str, object]] = {}
        ephemeris_flags: list[int] = []
        ephemeris_warnings: list[str] = []

        asc_row = {
            "key": "Ascendant",
            "name": PLANET_NAMES_BG["Ascendant"],
            "label": PLANET_LABELS_BG["Ascendant"],
            "retrograde": False,
            "speed": 0.0,
            "declination": 0.0,
            "ecliptic_latitude": 0.0,
            **asc_details,
        }
        asc_row["house"] = 1
        asc_row["nav_house"] = 1
        asc_row["nav_sign_name"] = SIGN_NAMES_BG[asc_nav_sign]
        asc_row["chart_code"] = PLANET_LABELS_BG["Ascendant"]
        points.append(asc_row)
        rows_by_key["Ascendant"] = asc_row

        for key in [
            "Sun",
            "Moon",
            "Mercury",
            "Venus",
            "Mars",
            "Jupiter",
            "Saturn",
            *OUTER_PLANET_KEYS,
        ]:
            values, retflags = swe.calc_ut(jd_ut, SWE_BODY_MAP[key], flags)
            equatorial_values, _ = swe.calc_ut(
                jd_ut,
                SWE_BODY_MAP[key],
                swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_TRUEPOS | swe.FLG_EQUATORIAL,
            )
            ephemeris_flags.append(retflags)
            backend_warning = _requested_swieph_backend_warning(key, flags, retflags)
            if backend_warning is not None:
                ephemeris_warnings.append(backend_warning)
            longitude_value = _normalize_degrees(values[0])
            speed = values[3]
            details = _zodiac_details(longitude_value)
            nav_sign_index = _navamsha_sign(details["sign_index"], details["degree_in_sign"])
            row = {
                "key": key,
                "name": PLANET_NAMES_BG[key],
                "label": PLANET_LABELS_BG[key],
                "retrograde": speed < 0,
                "speed": speed,
                "declination": equatorial_values[1],
                "ecliptic_latitude": values[1],
                **details,
            }
            row["house"] = ((row["sign_index"] - asc_details["sign_index"]) % 12) + 1
            row["nav_house"] = ((nav_sign_index - asc_nav_sign) % 12) + 1
            row["nav_sign_name"] = SIGN_NAMES_BG[nav_sign_index]
            row["chart_code"] = _planet_chart_code(key, row["retrograde"])
            points.append(row)
            rows_by_key[key] = row

        rahu_values, rahu_retflags = swe.calc_ut(jd_ut, node_id, flags)
        ephemeris_flags.append(rahu_retflags)
        backend_warning = _requested_swieph_backend_warning("Rahu", flags, rahu_retflags)
        if backend_warning is not None:
            ephemeris_warnings.append(backend_warning)
        rahu_longitude = _normalize_degrees(rahu_values[0])
        rahu_speed = rahu_values[3]
        rahu_details = _zodiac_details(rahu_longitude)
        rahu_nav_sign = _navamsha_sign(rahu_details["sign_index"], rahu_details["degree_in_sign"])
        rahu_row = {
            "key": "Rahu",
            "name": PLANET_NAMES_BG["Rahu"],
            "label": PLANET_LABELS_BG["Rahu"],
            "retrograde": rahu_speed < 0,
            "speed": rahu_speed,
            "declination": 0.0,
            "ecliptic_latitude": rahu_values[1],
            **rahu_details,
        }
        rahu_row["house"] = ((rahu_row["sign_index"] - asc_details["sign_index"]) % 12) + 1
        rahu_row["nav_house"] = ((rahu_nav_sign - asc_nav_sign) % 12) + 1
        rahu_row["nav_sign_name"] = SIGN_NAMES_BG[rahu_nav_sign]
        rahu_row["chart_code"] = _planet_chart_code("Rahu", rahu_row["retrograde"])
        points.append(rahu_row)
        rows_by_key["Rahu"] = rahu_row

        ketu_longitude = _normalize_degrees(rahu_longitude + 180)
        ketu_details = _zodiac_details(ketu_longitude)
        ketu_nav_sign = _navamsha_sign(ketu_details["sign_index"], ketu_details["degree_in_sign"])
        ketu_row = {
            "key": "Ketu",
            "name": PLANET_NAMES_BG["Ketu"],
            "label": PLANET_LABELS_BG["Ketu"],
            "retrograde": rahu_row["retrograde"],
            "speed": rahu_speed,
            "declination": 0.0,
            "ecliptic_latitude": -rahu_values[1],
            **ketu_details,
        }
        ketu_row["house"] = ((ketu_row["sign_index"] - asc_details["sign_index"]) % 12) + 1
        ketu_row["nav_house"] = ((ketu_nav_sign - asc_nav_sign) % 12) + 1
        ketu_row["nav_sign_name"] = SIGN_NAMES_BG[ketu_nav_sign]
        ketu_row["chart_code"] = _planet_chart_code("Ketu", ketu_row["retrograde"])
        points.append(ketu_row)
        rows_by_key["Ketu"] = ketu_row

        sun_longitude = float(rows_by_key["Sun"]["longitude"])
        for row in rows_by_key.values():
            distance = _angular_separation(float(row["longitude"]), sun_longitude)
            row["combustion_distance"] = distance
            row["is_combust"] = _is_planet_combust(
                row["key"], float(row["longitude"]), sun_longitude, combustion_orb
            )
            row["is_gandanta"] = is_gandanta(float(row["longitude"]))
        _apply_planetary_war(rows_by_key)

    order_index = {key: index for index, key in enumerate(PLANET_ORDER)}
    points_by_order = sorted(points, key=lambda point: order_index[point["key"]])

    d1_title = "\u0422\u0420" if prefix == "transit" else "D-1"
    d1_aria_title = "D-1 (\u0422\u0440\u0430\u043d\u0437\u0438\u0442\u0438)" if prefix == "transit" else "D-1"
    d1_chart = _build_chart_payload(
        d1_title,
        d1_subtitle,
        asc_details["sign_index"],
        points_by_order,
        "house",
        "sign_number",
        aria_title=d1_aria_title,
    )
    d1_chart["item_degrees"] = {
        str(point["chart_code"]): int(float(point["degree_in_sign"]))
        for point in points_by_order
    }
    divisional_charts = None
    selected_divisional_chart = None
    selected_divisional_chart_svg = None
    d9_chart = None
    d9_chart_svg = None
    if include_d9:
        divisional_charts = build_divisional_chart_registry(
            build_chart_payload=_build_chart_payload,
            points=points_by_order,
            asc_nav_sign=asc_nav_sign,
        )
        selected_divisional_chart = divisional_charts[DEFAULT_DIVISIONAL_CHART_CODE]
        selected_divisional_chart_svg = render_north_chart(selected_divisional_chart["payload"])
        d9_chart = divisional_charts["D9"]["payload"]
        d9_chart_svg = render_north_chart(d9_chart)

    eclipse_marker = _eclipse_marker_for_datetime(local_dt, jd_ut)
    table_rows = []
    for row in sorted(rows_by_key.values(), key=lambda item: order_index[item["key"]]):
        table_rows.append(
            {
                "name": row["name"],
                "key": row["key"],
                "label": row["label"],
                "jyotish_name": PLANET_JYOTISH_NAMES_BG.get(row["key"]),
                "sign_name": row["sign_name"],
                "sign_number": row["sign_number"],
                "degree_dms": row["degree_dms"],
                "absolute_degree_dms": _full_degree_dms(row["longitude"]),
                "longitude": float(row["longitude"]),
                "nakshatra": row["nakshatra"],
                "nakshatra_degree_dms": row["nakshatra_degree_dms"],
                "pada": row["pada"],
                "retrograde": row["retrograde"],
                "house": row["house"],
                "nav_sign_name": row["nav_sign_name"],
                "nav_sign_number": navamsha_sign_index(row["sign_index"], row["degree_in_sign"]) + 1,
                "is_combust": row["is_combust"],
                "combustion_distance": row["combustion_distance"],
                "is_gandanta": row["is_gandanta"],
                "is_planetary_war": row["is_planetary_war"],
                "planetary_war_result": row["planetary_war_result"],
                "planetary_war_opponents": row["planetary_war_opponents"],
                "planetary_war_distance": row["planetary_war_distance"],
                "eclipse_marker": eclipse_marker if row["key"] in ECLIPSE_MARKER_KEYS else None,
            }
        )

    ephemeris_source = _ephemeris_source_summary(ephemeris_flags)

    # ВРЕМЕННА диагностика — да се премахне след сверката.
    _diag_astro = {
        "jd_ut": jd_ut,
        "ayanamsha": float(ayanamsha),
        "node_mode": node_mode,
        "node_id": node_id,
        "flags": flags,
        "retflags": list(ephemeris_flags),
        "rahu_retflags": rahu_retflags,
        "swe_version": swe.version,
        "delta_t": swe.deltat_ex(jd_ut, swe.FLG_SWIEPH),
        "ephemeris_dir": EPHEMERIS_DIRECTORY,
    }

    return {
        "_diag_astro": _diag_astro,
        "local_birth_label": local_dt.strftime("%d.%m.%Y %H:%M:%S"),
        "utc_birth_label": utc_dt.strftime("%d.%m.%Y %H:%M:%S UTC"),
        "timezone": timezone_summary,
        "location_label": city_name or "Ръчно въведено място",
        "coordinates_label": _format_coordinate_label(latitude, longitude),
        "ayanamsha_label": _full_degree_dms(ayanamsha),
        "node_mode_label": NODE_MODE_LABELS[node_mode],
        "ephemeris_source": ephemeris_source,
        "ephemeris_warnings": ephemeris_warnings,
        "lagna": {
            "sign_name": asc_details["sign_name"],
            "sign_number": asc_details["sign_number"],
            "degree_dms": asc_details["degree_dms"],
            "nakshatra": asc_details["nakshatra"],
            "pada": asc_details["pada"],
            "nav_sign_name": SIGN_NAMES_BG[asc_nav_sign],
        },
        "d1_chart_data": d1_chart,
        "d1_chart_svg": render_north_chart(d1_chart, show_degrees=True),
        "d9_chart_data": d9_chart if include_d9 else None,
        "d9_chart_svg": d9_chart_svg,
        "divisional_chart_options": DIVISIONAL_CHART_OPTIONS if include_d9 else [],
        "divisional_charts": divisional_charts if include_d9 else {},
        "selected_divisional_code": DEFAULT_DIVISIONAL_CHART_CODE if include_d9 else None,
        "selected_divisional_chart": selected_divisional_chart if include_d9 else None,
        "selected_divisional_chart_svg": selected_divisional_chart_svg if include_d9 else None,
        "table_rows": table_rows,
        "raw_rows": rows_by_key,
        "asc_sign_index": asc_details["sign_index"],
        "moon_longitude": rows_by_key["Moon"]["longitude"],
        "local_datetime": local_dt,
        "utc_datetime": utc_dt,
        "julian_day_ut": jd_ut,
        "latitude": latitude,
        "longitude": longitude,
    }


_NATAL_TARA_KEYS = (
    "Ascendant",
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
)


def _build_nava_tara_table(rows_by_key: dict[str, dict]) -> list[dict]:
    """Нава Тара за Асцендента и 9-те класически грахи спрямо рождената Луна."""
    moon_row = rows_by_key.get("Moon")
    if moon_row is None or not moon_row.get("nakshatra"):
        return []
    janma_nakshatra_index = NAKSHATRA_NAMES_BG.index(moon_row["nakshatra"]) + 1

    rows = []
    for key in _NATAL_TARA_KEYS:
        row = rows_by_key.get(key)
        if row is None or not row.get("nakshatra"):
            continue
        current_nakshatra_index = NAKSHATRA_NAMES_BG.index(row["nakshatra"]) + 1
        nava = navatara(janma_nakshatra_index, current_nakshatra_index)
        rows.append(
            {
                "key": key,
                "label": PLANET_NAMES_BG[key],
                "nakshatra": row["nakshatra"],
                "tara_number": nava["tara_number"],
                "tara_name": nava["tara_name"],
                "position": nava["count"],
                "cycle": nava["navatara_cycle"],
            }
        )
    return rows


def calculate_reading(form_data: dict[str, str], build_mode: str = "natal") -> dict[str, object]:
    natal = _calculate_chart(form_data, "natal", "Раши", include_d9=True)

    with SWE_LOCK:
        _ensure_swe_thread_context()
        natal["panchanga"] = build_panchanga(
            local_datetime=natal["local_datetime"],
            latitude=natal["latitude"],
            longitude=natal["longitude"],
        )

    dasha_year_days = float(TROPICAL_YEAR_DAYS)
    relationships = build_relationship_table(natal["raw_rows"])
    ashtakavarga = build_ashtakavarga(natal["raw_rows"])
    nava_tara = _build_nava_tara_table(natal["raw_rows"])

    dasha = build_vimshottari_dasha(natal["moon_longitude"], natal["local_datetime"])
    chara_dasha = build_chara_dasha_rao(
        natal["raw_rows"],
        natal["asc_sign_index"],
        natal["local_datetime"],
        Decimal(str(dasha_year_days)),
    )

    jaimini = build_jaimini_bundle(
        build_chart_payload=_build_chart_payload,
        natal_chart_payload=natal["d1_chart_data"],
        rows_by_key=natal["raw_rows"],
        asc_sign_index=natal["asc_sign_index"],
        birth_dt=natal["local_datetime"],
    )
    jaimini["rashi_chart_svg"] = render_north_chart(jaimini["rashi_chart_payload"])
    jaimini["jaimini_chart_svg"] = render_north_chart(jaimini["jaimini_chart_payload"])


    transit_date = _get_form_value(form_data, "transit", "date")
    transit_time = _get_form_value(form_data, "transit", "time")
    if build_mode == "transit" and (bool(transit_date) ^ bool(transit_time)):
        raise CalculationError("За транзитната карта попълни и дата, и час, или остави и двете празни.")

    transit = None
    if build_mode == "transit":
        if not transit_date or not transit_time:
            raise CalculationError("За транзитната карта попълни дата, час и място, а след това натисни бутона за транзити.")
        transit = _calculate_chart(form_data, "transit", "Транзити", include_d9=True)
        with SWE_LOCK:
            _ensure_swe_thread_context()
            transit["panchanga"] = build_panchanga(
                local_datetime=transit["local_datetime"],
                latitude=transit["latitude"],
                longitude=transit["longitude"],
            )

    transit_overlay_svg = None
    if transit is not None:
        transit_overlay_svg = render_transit_overlay_chart(
            natal["d1_chart_data"],
            transit["d1_chart_data"],
            show_outer_planets=True,
        )

    return {
        "diag_astro": natal.get("_diag_astro"),
        "local_birth_label": natal["local_birth_label"],
        "utc_birth_label": natal["utc_birth_label"],
        "timezone": natal["timezone"],
        "location_label": natal["location_label"],
        "coordinates_label": natal["coordinates_label"],
        "ayanamsha_label": natal["ayanamsha_label"],
        "node_mode_label": natal["node_mode_label"],
        "ephemeris_source": natal["ephemeris_source"],
        "ephemeris_warnings": natal["ephemeris_warnings"],
        "lagna": natal["lagna"],
        "d1_chart_data": natal["d1_chart_data"],
        "d1_chart_svg": natal["d1_chart_svg"],
        "d9_chart_data": natal["d9_chart_data"],
        "d9_chart_svg": natal["d9_chart_svg"],
        "divisional_chart_options": natal["divisional_chart_options"],
        "divisional_charts": natal["divisional_charts"],
        "selected_divisional_code": natal["selected_divisional_code"],
        "selected_divisional_chart": natal["selected_divisional_chart"],
        "selected_divisional_chart_svg": natal["selected_divisional_chart_svg"],
        "table_rows": natal["table_rows"],
        "raw_rows": natal["raw_rows"],
        "local_datetime": natal["local_datetime"],
        "moon_longitude": natal["moon_longitude"],
        "asc_sign_index": natal["asc_sign_index"],
        "panchanga": natal["panchanga"],
        "relationships": relationships,
        "ashtakavarga": ashtakavarga,
        "nava_tara": nava_tara,
        "dasha": dasha,
        "chara_dasha": chara_dasha,
        "jaimini": jaimini,
        "dasha_year_days": dasha_year_days,
        "latitude": natal["latitude"],
        "longitude": natal["longitude"],
        "transit": transit,
        "transit_overlay_svg": transit_overlay_svg,
    }


def _utc_datetime_from_jd(jd_ut: float) -> datetime:
    year, month, day, hour_value = swe.revjul(jd_ut, swe.GREG_CAL)
    hour = int(hour_value)
    minute_value = (hour_value - hour) * 60.0
    minute = int(minute_value)
    second_value = (minute_value - minute) * 60.0
    second = int(second_value)
    microsecond = int(round((second_value - second) * 1_000_000))
    if microsecond >= 1_000_000:
        second += 1
        microsecond = 0
    base = datetime(year, month, day, tzinfo=timezone.utc)
    return base + timedelta(hours=hour, minutes=minute, seconds=second, microseconds=microsecond)
