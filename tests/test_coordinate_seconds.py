import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import app as app_module
from app import app, build_jhd_file, parse_jhd_to_form_values
from vedic_app.astro import _dms_to_decimal, calculate_reading, default_form_values


class CoordinateSecondsTests(unittest.TestCase):
    def test_default_city_uses_degree_minute_second_fields(self) -> None:
        values = default_form_values()

        self.assertEqual(
            (values["latitudeDegrees"], values["latitudeMinutes"], values["latitudeSeconds"]),
            ("43", "4", "52"),
        )
        self.assertEqual(
            (values["longitudeDegrees"], values["longitudeMinutes"], values["longitudeSeconds"]),
            ("25", "37", "44"),
        )
        self.assertEqual(values["transitLatitudeSeconds"], "52")
        self.assertEqual(values["transitLongitudeSeconds"], "44")

    def test_seconds_are_used_in_coordinate_calculation(self) -> None:
        coordinate = _dms_to_decimal("43", "4", "52", "N", "lat")
        self.assertAlmostEqual(coordinate, 43 + 4 / 60 + 52 / 3600, places=12)

    def test_data_page_contains_seconds_for_natal_and_transit_coordinates(self) -> None:
        html = app.test_client().get("/").get_data(as_text=True)

        for field_id in (
            "latitudeSeconds",
            "longitudeSeconds",
            "transitLatitudeSeconds",
            "transitLongitudeSeconds",
        ):
            self.assertIn(f'id="{field_id}"', html)
        self.assertIn('aria-label="Градуси">°</span>', html)
        self.assertIn('aria-label="Минути">′</span>', html)
        self.assertIn('aria-label="Секунди">″</span>', html)

    def test_coordinate_fields_allow_the_full_geographic_ranges(self) -> None:
        html = app.test_client().get("/").get_data(as_text=True)
        self.assertIn('id="latitudeDegrees" min="0" max="90"', html)
        self.assertIn('id="longitudeDegrees" min="0" max="180"', html)
        self.assertIn('id="transitLatitudeDegrees" min="0" max="90"', html)
        self.assertIn('id="transitLongitudeDegrees" min="0" max="180"', html)

        stylesheet = (
            Path(__file__).resolve().parent.parent / "static" / "styles.css"
        ).read_text(encoding="utf-8")
        self.assertIn(
            '.has-desktop-workspace.is-data-panel-open .coordinate-block input[type="number"]',
            stylesheet,
        )
        self.assertIn("font: 600 12px/1.2", stylesheet)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr)) 60px", stylesheet)
        self.assertIn("appearance: textfield", stylesheet)
        self.assertIn("::-webkit-inner-spin-button", stylesheet)
        self.assertIn("-webkit-appearance: none", stylesheet)

    def test_opened_jhd_coordinates_keep_seconds(self) -> None:
        content = "\n".join(
            [
                "12", "10", "1980", "16.2411111111", "-2.000000",
                "-25.3773333333", "43.0486666667", "0.000000", "0", "Reference",
            ]
        )
        values = parse_jhd_to_form_values(content)

        self.assertEqual(values["latitudeSeconds"], "52")
        self.assertEqual(values["longitudeSeconds"], "44")

    def test_napoleon_jhora_coordinates_are_not_treated_as_decimal_degrees(self) -> None:
        content = "\n".join(
            [
                "4", "20", "1808", "1.000000", "-.090000",
                "-2.200000", "48.520000", "0.000000",
            ]
        )
        values = parse_jhd_to_form_values(content)

        self.assertEqual(
            (
                values["latitudeDegrees"],
                values["latitudeMinutes"],
                values["latitudeSeconds"],
                values["latitudeHemisphere"],
            ),
            ("48", "52", "0", "N"),
        )
        self.assertEqual(
            (
                values["longitudeDegrees"],
                values["longitudeMinutes"],
                values["longitudeSeconds"],
                values["longitudeHemisphere"],
            ),
            ("2", "20", "0", "E"),
        )
        self.assertEqual(
            (values["manualTzSign"], values["manualTzHours"], values["manualTzMinutes"]),
            ("+", "0", "9"),
        )

    def test_legacy_rohini_decimal_coordinates_remain_readable_when_unambiguous(self) -> None:
        content = "\n".join(
            [
                "12", "10", "1980", "16.2411111111", "-2.000000",
                "-25.6288888889", "43.0811111111", "0.000000", "0", "Reference",
            ]
        )
        values = parse_jhd_to_form_values(content)

        self.assertEqual(
            (
                values["latitudeDegrees"],
                values["latitudeMinutes"],
                values["latitudeSeconds"],
            ),
            ("43", "4", "52"),
        )
        self.assertEqual(
            (
                values["longitudeDegrees"],
                values["longitudeMinutes"],
                values["longitudeSeconds"],
            ),
            ("25", "37", "44"),
        )

    def test_saved_jhd_uses_jhora_coordinate_format(self) -> None:
        chart = {
            "local_datetime": datetime.fromisoformat("1980-12-10T16:14:28+02:00"),
            "latitude": 43 + 4 / 60 + 52 / 3600,
            "longitude": 25 + 37 / 60 + 44 / 3600,
        }
        content, _filename = build_jhd_file(chart, {"cityName": "Reference"})
        lines = content.splitlines()

        self.assertAlmostEqual(float(lines[5]), -25.3773333333, places=6)
        self.assertAlmostEqual(float(lines[6]), 43.0486666667, places=6)

        values = parse_jhd_to_form_values(content)
        self.assertEqual(
            (
                values["latitudeDegrees"],
                values["latitudeMinutes"],
                values["latitudeSeconds"],
            ),
            ("43", "4", "52"),
        )
        self.assertEqual(
            (
                values["longitudeDegrees"],
                values["longitudeMinutes"],
                values["longitudeSeconds"],
            ),
            ("25", "37", "44"),
        )

    def test_save_and_open_buttons_preserve_coordinates_and_chart(self) -> None:
        cases = (
            ("48", "52", "0", "N", "2", "20", "0", "E"),
            ("33", "51", "31", "S", "151", "12", "51", "W"),
        )

        for index, coordinates in enumerate(cases):
            with self.subTest(coordinates=coordinates), TemporaryDirectory() as folder:
                payload = default_form_values()
                payload.update(
                    {
                        "birthDate": "1980-12-10",
                        "birthTime": "16:14:28",
                        "cityName": "Round trip",
                        "timezoneMode": "manual",
                        "manualTzSign": "+",
                        "manualTzHours": "2",
                        "manualTzMinutes": "0",
                        "latitudeDegrees": coordinates[0],
                        "latitudeMinutes": coordinates[1],
                        "latitudeSeconds": coordinates[2],
                        "latitudeHemisphere": coordinates[3],
                        "longitudeDegrees": coordinates[4],
                        "longitudeMinutes": coordinates[5],
                        "longitudeSeconds": coordinates[6],
                        "longitudeHemisphere": coordinates[7],
                    }
                )
                expected = calculate_reading(payload, build_mode="natal")
                target = Path(folder) / f"round-trip-{index}.jhd"

                with (
                    patch.object(
                        app_module,
                        "run_native_file_dialog",
                        side_effect=[str(target), str(target)],
                    ),
                    patch.object(app_module, "remember_horoscope_folder"),
                ):
                    client = app.test_client()
                    saved = client.post("/api/save-chart", json=payload)
                    opened = client.post("/api/open-chart")

                self.assertEqual(saved.status_code, 200, saved.get_json())
                self.assertTrue(saved.get_json()["ok"])
                self.assertTrue(target.is_file())
                self.assertEqual(opened.status_code, 200, opened.get_json())
                self.assertTrue(opened.get_json()["ok"])

                restored = app_module.latest_calculator_view["form_values"]
                actual = app_module.latest_calculator_view["results"]
                for key in (
                    "latitudeDegrees",
                    "latitudeMinutes",
                    "latitudeSeconds",
                    "latitudeHemisphere",
                    "longitudeDegrees",
                    "longitudeMinutes",
                    "longitudeSeconds",
                    "longitudeHemisphere",
                ):
                    self.assertEqual(restored[key], payload[key], key)
                self.assertEqual(actual["d1_chart_data"], expected["d1_chart_data"])
                self.assertEqual(actual["table_rows"], expected["table_rows"])


if __name__ == "__main__":
    unittest.main()
