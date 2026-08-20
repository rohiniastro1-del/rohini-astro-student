from __future__ import annotations

import json
import os
import re
import subprocess

import sys
import time
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent / ".packages"
if PACKAGE_DIR.exists():
    sys.path.insert(0, str(PACKAGE_DIR))

from flask import Flask, jsonify, render_template, request

from vedic_app.astro import (
    CalculationError,
    calculate_lagna_sign,
    calculate_reading,
    default_form_values,
)
from vedic_app.data import CITIES, CITY_LOOKUP, SIGN_NAMES_BG
from vedic_app.chara_dasha import calculate_antardasha_order
from vedic_app.dasha_systems import build_dasha_rows
from vedic_app.time_dynamics import TimeDynamicsError, shift_civil_datetime


app = Flask(__name__)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["TEMPLATES_AUTO_RELOAD"] = True

latest_calculator_view: dict[str, object] | None = None

OFFICIAL_SITE_URL = "https://rohiniastrobg.com/"
CONSULTATION_URL = "https://rohiniastrobg.com/astrologichni-uslugi/"
TRAINING_URL = "https://rohiniastrobg.com/obucheniya-astro-i-i-czin/"
SOURCE_CODE_URL = "https://github.com/rohiniastro1-del/rohini-astro-student"
LICENSE_URL = "https://github.com/rohiniastro1-del/rohini-astro-student/blob/main/LICENSE"


def apply_global_node_mode(form_values: dict[str, str]) -> None:
    """Прилага глобалния режим на възлите (Rahu/Ketu) от cookie-то."""
    saved_node_mode = request.cookies.get("rohini_node_mode", "")
    if saved_node_mode in ("mean", "true"):
        form_values["nodeMode"] = saved_node_mode
        form_values["transitNodeMode"] = saved_node_mode


DASHA_SYSTEMS = {
    "vimshottari": {"title": "Вимшоттари", "max_level": 5},
    "rao": {"title": "Чара даша по К. Н. Рао", "max_level": 5},
}


def build_chart_export_data(results: dict[str, object]) -> dict[str, object]:
    """Prepare only charts and classical graha degrees used by the PNG card."""
    charts = [
        {
            "code": "D1",
            "label": "D-1 (Раши)",
            "payload": results["d1_chart_data"],
        }
    ]
    charts.extend(
        {
            "code": code,
            "label": str(bundle["card_title"]),
            "payload": bundle["payload"],
        }
        for code, bundle in results.get("divisional_charts", {}).items()
        if bundle.get("implemented")
    )
    transit = results.get("transit")
    if isinstance(transit, dict) and transit.get("d1_chart_data"):
        charts.append(
            {
                "code": "TR",
                "label": "Транзити (D-1)",
                "payload": transit["d1_chart_data"],
            }
        )

    classical_labels = {"Ас", "Сл", "Лу", "Ма", "Ме", "Юп", "Ве", "Са", "Ра", "Ке"}
    degree_rows = [
        {
            "label": str(row["label"]),
            "name": str(row["name"]),
            "sign_name": str(row["sign_name"]),
            "degree_dms": str(row["degree_dms"]),
        }
        for row in results.get("table_rows", [])
        if row.get("label") in classical_labels
    ]
    return {
        "title": f"{results.get('local_birth_label', '')} • {results.get('location_label', '')}",
        "charts": charts,
        "degree_rows": degree_rows,
    }


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/__rohini_health")
def rohini_health() -> object:
    return jsonify({"ok": True})


@app.post("/api/time-dynamics/shift")
def time_dynamics_shift() -> object:
    payload = request.get_json(silent=True) or {}
    try:
        date_text, time_text = shift_civil_datetime(
            str(payload.get("date", "")),
            str(payload.get("time", "")),
            payload.get("amount", 0),
            str(payload.get("unit", "")),
            forward=bool(payload.get("forward", True)),
        )
    except TimeDynamicsError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "date": date_text, "time": time_text})


@app.post("/api/chart-context/lagna-boundaries")
def chart_context_lagna_boundaries() -> object:
    payload = request.get_json(silent=True) or {}
    form_data = default_form_values()
    supplied_form = payload.get("form")
    if isinstance(supplied_form, dict):
        form_data.update({str(key): str(value) for key, value in supplied_form.items()})
    prefix = "transit" if str(payload.get("prefix", "natal")) == "transit" else "natal"
    chart_code = str(payload.get("chart_code", "D1")).upper()
    date_key = "transitDate" if prefix == "transit" else "birthDate"
    time_key = "transitTime" if prefix == "transit" else "birthTime"

    try:
        current_sign = calculate_lagna_sign(form_data, chart_code, prefix)

        def sign_at_offset(offset_seconds: int) -> int:
            shifted_date, shifted_time = shift_civil_datetime(
                form_data[date_key], form_data[time_key], abs(offset_seconds), "second",
                forward=offset_seconds >= 0,
            )
            moved = dict(form_data)
            moved[date_key] = shifted_date
            moved[time_key] = shifted_time
            return calculate_lagna_sign(moved, chart_code, prefix)

        def find_boundary(direction: int) -> int:
            low = 0
            high = 60
            maximum = 7 * 24 * 60 * 60
            while high < maximum and sign_at_offset(direction * high) == current_sign:
                low = high
                high *= 2
            high = min(high, maximum)
            if sign_at_offset(direction * high) == current_sign:
                raise CalculationError("Не е намерена смяна на лагна в следващите седем дни.")
            while high - low > 1:
                middle = (low + high) // 2
                if sign_at_offset(direction * middle) == current_sign:
                    low = middle
                else:
                    high = middle
            return high

        backward_seconds = find_boundary(-1)
        forward_seconds = find_boundary(1)
    except (CalculationError, TimeDynamicsError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    return jsonify({
        "ok": True,
        "sign_number": current_sign,
        "sign_name": SIGN_NAMES_BG[current_sign - 1],
        "backward_seconds": backward_seconds,
        "forward_seconds": forward_seconds,
    })


def _rao_dasha_rows(results: dict[str, object], path: list[int]) -> list[dict[str, object]]:
    periods = results["chara_dasha"]["md_periods"]
    if not path:
        source = periods
        return [{
            "path": [int(row["sign_index"])], "label": row["sign_name"],
            "start": row["start"].isoformat(), "end": row["end"].isoformat(),
            "start_label": row["start"].strftime("%Y-%m-%d %H:%M:%S"),
            "end_label": row["end"].strftime("%Y-%m-%d %H:%M:%S"),
        } for row in source]
    parent = next(row for row in periods if int(row["sign_index"]) == path[0])
    if len(path) == 1:
        source = parent["antardashas"]
        return [{
            "path": [path[0], int(row["sign_index"])], "label": row["sign_name"],
            "start": row["start"].isoformat(), "end": row["end"].isoformat(),
            "start_label": row["start"].strftime("%Y-%m-%d %H:%M:%S"),
            "end_label": row["end"].strftime("%Y-%m-%d %H:%M:%S"),
        } for row in source]
    ad = next(row for row in parent["antardashas"] if int(row["sign_index"]) == path[1])
    start, end = ad["start"], ad["end"]
    for level in range(2, len(path)):
        order, _step = calculate_antardasha_order(path[level - 1])
        index = order.index(path[level])
        total = (end - start).total_seconds()
        start = start + timedelta(seconds=round(total * index / 12))
        end = start + timedelta(seconds=round(total * (index + 1) / 12))

    order, _step = calculate_antardasha_order(path[-1])
    span = (end - start).total_seconds()
    rows = []
    for index, sign_index in enumerate(order):
        child_start = start + timedelta(seconds=round(span * index / 12))
        child_end = start + timedelta(seconds=round(span * (index + 1) / 12))
        rows.append({
            "path": [*path, sign_index], "label": SIGN_NAMES_BG[sign_index],
            "start": child_start.isoformat(), "end": child_end.isoformat(),
            "start_label": child_start.strftime("%Y-%m-%d %H:%M:%S"),
            "end_label": child_end.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return rows


def _parse_dasha_boundary(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, list) and len(value) == 4:
        year, month, day = int(value[0]), int(value[1]), int(value[2])
        seconds = int(round(float(value[3]) * 3600))
        return datetime(year, month, day) + timedelta(seconds=seconds)
    return datetime.fromisoformat(str(value).replace(" ", "T"))


def _own_dasha_rows(results: dict[str, object], system: str, payload: dict[str, object]) -> list[dict[str, object]]:
    birth_dt = results["local_datetime"]
    path = [int(value) for value in payload.get("path", [])]
    parent_start = _parse_dasha_boundary(payload.get("start"))
    parent_end = _parse_dasha_boundary(payload.get("end"))
    return build_dasha_rows(system, results["table_rows"], birth_dt, path, parent_start, parent_end)


@app.post("/api/dashas")
def dasha_periods() -> object:
    payload = request.get_json(silent=True) or {}
    system = str(payload.get("system", ""))
    definition = DASHA_SYSTEMS.get(system)
    if definition is None:
        return jsonify({"ok": False, "error": "Непозната даша."}), 400
    path = [int(value) for value in payload.get("path", [])]
    if len(path) >= int(definition["max_level"]):
        return jsonify({"ok": True, "rows": [], "title": definition["title"], "max_level": definition["max_level"]})
    form_data = default_form_values()
    supplied_form = payload.get("form")
    if isinstance(supplied_form, dict):
        form_data.update({str(key): str(value) for key, value in supplied_form.items()})
    try:
        results = calculate_reading(form_data, build_mode="natal")
        if system == "rao":
            rows = _rao_dasha_rows(results, path)
            year_days = results["dasha_year_days"]
        else:
            rows = _own_dasha_rows(results, system, payload)
            year_days = round(float(results["dasha_year_days"]), 9)
    except (CalculationError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "rows": rows, "title": definition["title"],
                    "max_level": definition["max_level"], "year_days": year_days})


@app.route("/", methods=["GET", "POST"])
def index() -> str:
    global latest_calculator_view
    form_values = default_form_values()
    if request.method == "GET":
        saved_combustion_orb = request.cookies.get("rohini_combustion_orb", "")
        try:
            saved_orb_number = float(saved_combustion_orb.replace(",", "."))
            # Older desktop builds could persist 0 here after a browser-side
            # state conflict.  Zero is not a useful combustion orb and would
            # silently hide every marker, so migrate that stale value back to
            # the documented 5-degree default.
            if 0.0 < saved_orb_number <= 30.0:
                form_values["combustionOrbDegrees"] = f"{saved_orb_number:g}"
        except (TypeError, ValueError):
            pass
        apply_global_node_mode(form_values)
    results = None
    error = None
    build_mode = "natal"

    if request.method == "GET" and request.args.get("restore") == "1" and latest_calculator_view:
        form_values = deepcopy(latest_calculator_view["form_values"])
        results = latest_calculator_view["results"]
        build_mode = str(latest_calculator_view["build_mode"])
    elif request.method == "GET":
        try:
            results = calculate_reading(form_values, build_mode="natal")
            latest_calculator_view = {
                "form_values": deepcopy(form_values),
                "results": results,
                "build_mode": "natal",
            }
        except CalculationError as exc:
            error = str(exc)
    elif request.method == "POST":
        form_values.update(request.form.to_dict())
        build_mode = request.form.get("buildMode", "natal")
        try:
            results = calculate_reading(form_values, build_mode=build_mode)
            latest_calculator_view = {
                "form_values": deepcopy(form_values),
                "results": results,
                "build_mode": build_mode,
            }
        except CalculationError as exc:
            error = str(exc)

    return render_template(
        "index.html",
        cities=CITIES,
        cities_json=json.dumps(CITIES, ensure_ascii=False),
        form_values=form_values,
        results=results,
        error=error,
        build_mode=build_mode,
        chart_export_data_json=json.dumps(
            build_chart_export_data(results) if results else {"title": "", "charts": [], "degree_rows": []},
            ensure_ascii=False,
        ),
        static_token=int(time.time()),
        OFFICIAL_SITE_URL=OFFICIAL_SITE_URL,
        CONSULTATION_URL=CONSULTATION_URL,
        TRAINING_URL=TRAINING_URL,
        SOURCE_CODE_URL=SOURCE_CODE_URL,
        LICENSE_URL=LICENSE_URL,
    )


APP_ROOT = Path(__file__).resolve().parent
HOROSCOPES_DIR = APP_ROOT / "Хороскопи"
HOROSCOPES_DIR.mkdir(parents=True, exist_ok=True)
LAST_FOLDER_STATE_PATH = APP_ROOT / ".rohini-horoscopes-last-folder.txt"
DIALOG_HELPER = APP_ROOT / "filedialog_helper.py"


def get_last_horoscope_folder() -> str:
    try:
        folder = LAST_FOLDER_STATE_PATH.read_text(encoding="utf-8").strip()
        if folder and Path(folder).is_dir():
            return folder
    except OSError:
        pass
    return str(HOROSCOPES_DIR)


def remember_horoscope_folder(path: str) -> None:
    try:
        LAST_FOLDER_STATE_PATH.write_text(str(Path(path).parent), encoding="utf-8")
    except OSError:
        pass


def run_native_file_dialog(mode: str, initial_dir: str, filename: str = "") -> str | None:
    helper_python = Path(sys.executable).with_name("python.exe")
    if not helper_python.exists():
        helper_python = Path(sys.executable)
    try:
        result = subprocess.run(
            [str(helper_python), str(DIALOG_HELPER), mode, initial_dir, filename],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            cwd=str(APP_ROOT),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        path = result.stdout.strip()
        return path or None
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None


def build_jhd_file(chart: dict, form_values: dict) -> tuple[str, str]:
    local_dt = chart["local_datetime"]
    latitude = float(chart["latitude"])
    longitude = float(chart["longitude"])
    offset_minutes = int((local_dt.utcoffset() or timedelta()).total_seconds() // 60)

    time_decimal = local_dt.hour + local_dt.minute / 60.0 + local_dt.second / 3600.0

    abs_minutes = abs(offset_minutes)
    tz_hours = abs_minutes // 60
    tz_minutes = abs_minutes % 60
    tz_jhd = tz_hours + tz_minutes / 100.0
    if offset_minutes >= 0:
        tz_jhd = -tz_jhd

    tz_decimal = -offset_minutes / 60.0
    jhd_longitude = -longitude

    city_name = str(form_values.get("cityName") or "").strip()
    city_entry = CITY_LOOKUP.get(city_name) if city_name else None
    country = str((city_entry or {}).get("country") or "") if city_entry else ""
    if not city_name:
        city_name = "Unknown"
    if not country:
        country = "Unknown"

    lines = [
        str(local_dt.month),
        str(local_dt.day),
        str(local_dt.year),
        f"{time_decimal:.10f}",
        f"{tz_jhd:.6f}",
        f"{jhd_longitude:.6f}",
        f"{latitude:.6f}",
        "0.000000",
        f"{tz_decimal:.6f}",
        f"{tz_decimal:.6f}",
        "0",
        "105",
        city_name,
        country,
        "1",
        "1013.250000",
        "20.000000",
        "0",
    ]
    content = "\n".join(lines) + "\n"

    safe_city = re.sub(r"[^0-9A-Za-zА-Яа-яёЁ\-_ ]+", "_", city_name).strip().replace(" ", "_") or "Карта"
    filename = f"{safe_city}_{local_dt.strftime('%Y-%m-%d')}.jhd"
    return content, filename


def parse_jhd_to_form_values(content: str) -> dict[str, str]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    tokens = lines if len(lines) > 1 else lines[0].split() if lines else []
    if len(tokens) < 7:
        raise CalculationError("Файлът не изглежда да е валиден .jhd файл.")

    month = int(tokens[0])
    day = int(tokens[1])
    year = int(tokens[2])
    time_decimal = float(tokens[3])
    tz_field5 = float(tokens[4])
    jhd_longitude = float(tokens[5])
    latitude = float(tokens[6])

    total_seconds = round(time_decimal * 3600)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    east = tz_field5 < 0
    abs_tz = abs(tz_field5)
    tz_hours = int(abs_tz)
    tz_minutes = round((abs_tz - tz_hours) * 100)

    longitude = -jhd_longitude

    place_name = ""
    for token in tokens[8:]:
        if not re.fullmatch(r"[+-]?[\d.]+", token):
            place_name = token
            break

    values = default_form_values()
    values["birthDate"] = f"{year:04d}-{month:02d}-{day:02d}"
    values["birthTime"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    values["cityName"] = place_name
    values["timezoneMode"] = "manual"
    values["manualTzSign"] = "+" if east else "-"
    values["manualTzHours"] = str(tz_hours)
    values["manualTzMinutes"] = str(tz_minutes)

    lat_abs = abs(latitude)
    lat_deg = int(lat_abs)
    lat_min = round((lat_abs - lat_deg) * 60)
    if lat_min == 60:
        lat_deg += 1
        lat_min = 0
    values["latitudeDegrees"] = str(lat_deg)
    values["latitudeMinutes"] = str(lat_min)
    values["latitudeHemisphere"] = "N" if latitude >= 0 else "S"

    lng_abs = abs(longitude)
    lng_deg = int(lng_abs)
    lng_min = round((lng_abs - lng_deg) * 60)
    if lng_min == 60:
        lng_deg += 1
        lng_min = 0
    values["longitudeDegrees"] = str(lng_deg)
    values["longitudeMinutes"] = str(lng_min)
    values["longitudeHemisphere"] = "E" if longitude >= 0 else "W"

    return values


@app.post("/api/save-chart")
def save_chart() -> object:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"ok": False, "error": "Няма данни за запазване."}), 400
    form_values = default_form_values()
    for key, value in payload.items():
        if value is not None:
            form_values[key] = str(value)
    try:
        results = calculate_reading(form_values, build_mode="natal")
    except CalculationError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    content, filename = build_jhd_file(results, form_values)
    target = run_native_file_dialog("save", get_last_horoscope_folder(), filename)
    if not target:
        return jsonify({"ok": False, "cancelled": True})
    try:
        Path(target).write_text(content, encoding="utf-8")
    except OSError as exc:
        return jsonify({"ok": False, "error": f"Не можах да запиша файла: {exc}"}), 500
    remember_horoscope_folder(target)
    return jsonify({"ok": True, "filename": Path(target).name, "path": target})


@app.post("/api/open-chart")
def open_chart() -> object:
    global latest_calculator_view
    target = run_native_file_dialog("open", get_last_horoscope_folder())
    if not target:
        return jsonify({"ok": False, "cancelled": True})
    try:
        content = Path(target).read_text(encoding="utf-8")
    except OSError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    remember_horoscope_folder(target)
    try:
        form_values = parse_jhd_to_form_values(content)
        apply_global_node_mode(form_values)
        results = calculate_reading(form_values, build_mode="natal")
    except (CalculationError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    latest_calculator_view = {
        "form_values": deepcopy(form_values),
        "results": results,
        "build_mode": "natal",
    }
    return jsonify({"ok": True, "name": Path(target).name})


if __name__ == "__main__":
    port = int(os.environ.get("ROHINI_ASTRO_PORT", "5051"))
    app.run(debug=False, use_reloader=True, threaded=True, port=port)
