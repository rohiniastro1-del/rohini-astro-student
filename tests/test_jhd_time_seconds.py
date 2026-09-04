import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app import app, build_jhd_file, parse_jhd_to_form_values, _jhd_time_microseconds
from vedic_app.astro import (
    CalculationError, _parse_manual_offset, _format_utc_offset,
    calculate_reading, default_form_values, calculate_lagna_sign,
)


# Literal header from the user's JHora file, not produced by our own exporter.
JHORA = "\n".join([
    "1", "22", "1906", "1.480000000000000", "6.314000",
    "97.519833", "32.523167", "0.000000", "6.523333", "6.523333",
    "0", "299", "Peaster", "Texas,^USA", "1", "1013.250000", "20.000000", "0",
])


class JhdTimeSecondsTests(unittest.TestCase):
    def test_literal_jhora_header(self):
        values = parse_jhd_to_form_values(JHORA)
        self.assertEqual(values["birthTime"], "01:48:00")
        self.assertEqual([values[k] for k in ("manualTzSign", "manualTzHours", "manualTzMinutes", "manualTzSeconds")], ["-", "6", "31", "24"])
        self.assertEqual([values[k] for k in ("latitudeDegrees", "latitudeMinutes", "latitudeSeconds")], ["32", "52", "19"])

    def test_calculated_utc_and_label(self):
        chart = calculate_reading(parse_jhd_to_form_values(JHORA))
        self.assertEqual(chart["local_datetime"].astimezone(timezone.utc), datetime(1906, 1, 22, 8, 19, 24, tzinfo=timezone.utc))
        self.assertEqual(chart["timezone"]["offset_label"], "UTC-06:31:24")

    def test_export_literal_time_and_zone(self):
        chart = {"local_datetime": datetime(1906, 1, 22, 1, 48, tzinfo=timezone(-timedelta(hours=6, minutes=31, seconds=24))), "latitude": 32, "longitude": -97}
        text, _ = build_jhd_file(chart, {})
        self.assertEqual(text.splitlines()[3], "1.480000000000")
        self.assertEqual(text.splitlines()[4], "6.314000000000")

    def test_subseconds_and_both_zone_signs_roundtrip(self):
        for offset in (235, -23484, 0, 7200):
            for time in ("00:00:00", "01:48:00", "16:14:28.422244", "23:59:59.999999"):
                with self.subTest(offset=offset, time=time):
                    local = datetime.fromisoformat("2000-01-02T" + time).replace(tzinfo=timezone(timedelta(seconds=offset)))
                    text, _ = build_jhd_file({"local_datetime": local, "latitude": 43, "longitude": 25}, {})
                    values = parse_jhd_to_form_values(text)
                    self.assertEqual(datetime.fromisoformat("2000-01-02T" + values["birthTime"]).time(), local.time())
                    parsed = _parse_manual_offset(values["manualTzSign"], values["manualTzHours"], values["manualTzMinutes"], values["manualTzSeconds"])
                    self.assertEqual(round(parsed * 60), offset)

    def test_missing_seconds_preserves_existing_offsets(self):
        self.assertEqual(_parse_manual_offset("+", "2", "30"), 150)
        self.assertEqual(_format_utc_offset(150), "UTC+02:30")
        values = default_form_values()
        self.assertEqual(values["manualTzSeconds"], "0")
        self.assertEqual(values["transitManualTzSeconds"], "0")

    def test_invalid_seconds_rejected(self):
        for seconds in ("-1", "60", "1.5", "abc"):
            with self.subTest(seconds=seconds), self.assertRaises(CalculationError):
                _parse_manual_offset("+", "2", "0", seconds)
        for value in ("NaN", "Infinity", "1.60", "-1"):
            with self.subTest(value=value), self.assertRaises(CalculationError):
                _jhd_time_microseconds(value)

    def test_explicit_legacy_time_does_not_change_jhora_default(self):
        self.assertEqual(parse_jhd_to_form_values(JHORA)["birthTime"], "01:48:00")
        self.assertEqual(parse_jhd_to_form_values(JHORA, legacy_decimal_time=True)["birthTime"], "01:28:48")

    def test_seconds_fields_and_save_payload(self):
        html = app.test_client().get("/").get_data(as_text=True)
        for name in ("manualTzSeconds", "transitManualTzSeconds"):
            self.assertIn(f'id="{name}"', html)
        js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('"manualTzMinutes", "manualTzSeconds"', js)

    def test_transit_and_lagna_use_same_seconds(self):
        values = parse_jhd_to_form_values(JHORA)
        for key, value in list(values.items()):
            if not key.startswith("transit"):
                transit_key = "transit" + key[0].upper() + key[1:]
                if key == "birthDate":
                    transit_key = "transitDate"
                elif key == "birthTime":
                    transit_key = "transitTime"
                if transit_key in values:
                    values[transit_key] = value
        result = calculate_reading(values, build_mode="transit")
        self.assertEqual(result["utc_birth_label"], result["transit"]["utc_birth_label"])
        self.assertEqual(result["lagna"], result["transit"]["lagna"])
        self.assertEqual(calculate_lagna_sign(values), result["lagna"]["sign_number"])


if __name__ == "__main__":
    unittest.main()
