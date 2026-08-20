from __future__ import annotations

import unittest

from vedic_app.astro import (
    _degree_fraction_to_dms,
    _format_dms,
    _full_degree_dms,
    calculate_reading,
    default_form_values,
)


def _reference_form() -> dict[str, str]:
    values = default_form_values()
    values.update(
        {
            "birthDate": "1980-12-10",
            "birthTime": "16:14:28",
            "cityName": "",
            "latitudeDegrees": "43",
            "latitudeMinutes": "8",
            "latitudeHemisphere": "N",
            "longitudeDegrees": "25",
            "longitudeMinutes": "42",
            "longitudeHemisphere": "E",
            "timezoneMode": "manual",
            "manualTzSign": "+",
            "manualTzHours": "2",
            "manualTzMinutes": "0",
            "nodeMode": "true",
            "transitNodeMode": "true",
        }
    )
    return values


class DmsRoundingTests(unittest.TestCase):
    def test_round_half_up_seconds(self):
        self.assertEqual(_degree_fraction_to_dms(20.867 / 3600), (0, 0, 21))
        self.assertEqual(_degree_fraction_to_dms(20.499 / 3600), (0, 0, 20))
        self.assertEqual(_degree_fraction_to_dms(20.500 / 3600), (0, 0, 21))

    def test_minute_carry(self):
        self.assertEqual(_degree_fraction_to_dms(59.499 / 3600), (0, 0, 59))
        # 59.50" се закръгля до 60" → 1 минута
        self.assertEqual(_degree_fraction_to_dms(59.500 / 3600), (0, 1, 0))

    def test_degree_carry(self):
        # 59'59.50" → следващ градус
        self.assertEqual(_degree_fraction_to_dms((59 * 60 + 59.5) / 3600), (1, 0, 0))

    def test_format_dms_rahu_value(self):
        # 18°27'20.867" Cancer → 18°27'21"
        value = 18 + 27 / 60 + 20.867 / 3600
        self.assertEqual(_format_dms(value), "18° 27' 21\"")

    def test_full_degree_dms_rahu_value(self):
        # 108°27'20.867" → 108°27'21"
        value = 108 + 27 / 60 + 20.867 / 3600
        self.assertEqual(_full_degree_dms(value), "108° 27' 21\"")


class DmsReferenceChartTests(unittest.TestCase):
    def test_reference_1980_rahu_ketu(self):
        result = calculate_reading(_reference_form(), build_mode="natal")
        rows = {row["key"]: row for row in result["table_rows"]}
        self.assertEqual(rows["Rahu"]["degree_dms"], "18° 27' 21\"")
        self.assertEqual(rows["Ketu"]["degree_dms"], "18° 27' 21\"")
        self.assertEqual(rows["Rahu"]["absolute_degree_dms"], "108° 27' 21\"")
        self.assertEqual(rows["Ketu"]["absolute_degree_dms"], "288° 27' 21\"")

    def test_reference_1980_sun_rounds_up(self):
        result = calculate_reading(_reference_form(), build_mode="natal")
        rows = {row["key"]: row for row in result["table_rows"]}
        # Sun 25°06'43.77" Scorpio → 25°06'44"
        self.assertEqual(rows["Sun"]["degree_dms"], "25° 06' 44\"")


if __name__ == "__main__":
    unittest.main()
