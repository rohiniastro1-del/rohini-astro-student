import unittest
from pathlib import Path

from app import app, parse_jhd_to_form_values
from vedic_app.astro import _dms_to_decimal, default_form_values


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

    def test_opened_jhd_coordinates_keep_seconds(self) -> None:
        content = "\n".join(
            [
                "12", "10", "1980", "16.2411111111", "-2.000000",
                "-25.6288888889", "43.0811111111", "0.000000", "0", "Reference",
            ]
        )
        values = parse_jhd_to_form_values(content)

        self.assertEqual(values["latitudeSeconds"], "52")
        self.assertEqual(values["longitudeSeconds"], "44")


if __name__ == "__main__":
    unittest.main()
