import sys
import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
PACKAGES_DIR = WORKSPACE / ".packages"
if PACKAGES_DIR.exists():
    sys.path.insert(0, str(PACKAGES_DIR))

from vedic_app.astro import calculate_reading, default_form_values


def build_payload() -> dict[str, str]:
    payload = default_form_values()
    payload.update(
        {
            "birthDate": "1980-12-10",
            "birthTime": "16:14:28",
            "cityName": "Велико Търново",
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
            "transitDate": "2026-07-15",
            "transitTime": "12:00:00",
            "transitCityName": "София",
            "transitLatitudeDegrees": "42",
            "transitLatitudeMinutes": "42",
            "transitLatitudeHemisphere": "N",
            "transitLongitudeDegrees": "23",
            "transitLongitudeMinutes": "19",
            "transitLongitudeHemisphere": "E",
            "transitNodeMode": "true",
        }
    )
    return payload


def rows_by_name(result: dict) -> dict[str, dict]:
    return {row["name"]: row for row in result["table_rows"]}


class TransitInputTests(unittest.TestCase):
    def test_foreign_transit_location_works_without_list_entry(self) -> None:
        foreign = build_payload()
        foreign.update(
            {
                "transitDate": "2026-07-15",
                "transitTime": "12:00:00",
                "transitCityName": "Лондон",
                "transitLatitudeDegrees": "51",
                "transitLatitudeMinutes": "30",
                "transitLatitudeHemisphere": "N",
                "transitLongitudeDegrees": "0",
                "transitLongitudeMinutes": "7",
                "transitLongitudeHemisphere": "W",
                "transitTimezoneMode": "auto",
                "transitNodeMode": "true",
            }
        )

        result = calculate_reading(foreign, build_mode="transit")["transit"]

        self.assertEqual(result["location_label"], "Лондон")
        self.assertEqual(result["timezone"]["name"], "Europe/London")
        self.assertEqual(result["timezone"]["offset_label"], "UTC+01:00")
        self.assertEqual(result["utc_birth_label"], "15.07.2026 11:00:00 UTC")

    def test_transit_matches_natal_when_inputs_are_identical(self) -> None:
        same = build_payload()
        same.update(
            {
                "birthDate": "2026-04-07",
                "birthTime": "19:30:54",
                "cityName": "Велико Търново",
                "latitudeDegrees": "43",
                "latitudeMinutes": "4",
                "latitudeHemisphere": "N",
                "longitudeDegrees": "25",
                "longitudeMinutes": "39",
                "longitudeHemisphere": "E",
                "timezoneMode": "manual",
                "manualTzSign": "+",
                "manualTzHours": "3",
                "manualTzMinutes": "0",
                "nodeMode": "true",
                "transitDate": "2026-04-07",
                "transitTime": "19:30:54",
                "transitCityName": "Велико Търново",
                "transitLatitudeDegrees": "43",
                "transitLatitudeMinutes": "4",
                "transitLatitudeHemisphere": "N",
                "transitLongitudeDegrees": "25",
                "transitLongitudeMinutes": "39",
                "transitLongitudeHemisphere": "E",
                "transitTimezoneMode": "manual",
                "transitManualTzSign": "+",
                "transitManualTzHours": "3",
                "transitManualTzMinutes": "0",
                "transitNodeMode": "true",
            }
        )

        result = calculate_reading(same, build_mode="transit")
        transit = result["transit"]

        self.assertIsNotNone(transit)
        self.assertEqual(result["utc_birth_label"], transit["utc_birth_label"])
        self.assertEqual(result["ayanamsha_label"], transit["ayanamsha_label"])
        self.assertEqual(result["node_mode_label"], transit["node_mode_label"])
        self.assertEqual(result["lagna"]["degree_dms"], transit["lagna"]["degree_dms"])
        self.assertEqual(
            [(row["name"], row["degree_dms"], row["sign_name"], row["retrograde"]) for row in result["table_rows"]],
            [(row["name"], row["degree_dms"], row["sign_name"], row["retrograde"]) for row in transit["table_rows"]],
        )

    def test_manual_transit_timezone_changes_positions(self) -> None:
        plus_three = build_payload()
        plus_three.update(
            {
                "transitTimezoneMode": "manual",
                "transitManualTzSign": "+",
                "transitManualTzHours": "3",
                "transitManualTzMinutes": "0",
            }
        )
        plus_two = build_payload()
        plus_two.update(
            {
                "transitTimezoneMode": "manual",
                "transitManualTzSign": "+",
                "transitManualTzHours": "2",
                "transitManualTzMinutes": "0",
            }
        )

        result_plus_three = calculate_reading(plus_three, build_mode="transit")["transit"]
        result_plus_two = calculate_reading(plus_two, build_mode="transit")["transit"]

        self.assertEqual(result_plus_three["utc_birth_label"], "15.07.2026 09:00:00 UTC")
        self.assertEqual(result_plus_two["utc_birth_label"], "15.07.2026 10:00:00 UTC")
        self.assertNotEqual(result_plus_three["lagna"]["degree_dms"], result_plus_two["lagna"]["degree_dms"])
        self.assertNotEqual(
            result_plus_three["table_rows"][1]["degree_dms"],
            result_plus_two["table_rows"][1]["degree_dms"],
        )

    def test_manual_transit_time_changes_positions(self) -> None:
        noon = build_payload()
        noon.update(
            {
                "transitTimezoneMode": "manual",
                "transitManualTzSign": "+",
                "transitManualTzHours": "3",
                "transitManualTzMinutes": "0",
                "transitTime": "12:00:00",
            }
        )
        half_past = build_payload()
        half_past.update(
            {
                "transitTimezoneMode": "manual",
                "transitManualTzSign": "+",
                "transitManualTzHours": "3",
                "transitManualTzMinutes": "0",
                "transitTime": "12:30:00",
            }
        )

        result_noon = calculate_reading(noon, build_mode="transit")["transit"]
        result_half_past = calculate_reading(half_past, build_mode="transit")["transit"]

        self.assertEqual(result_noon["utc_birth_label"], "15.07.2026 09:00:00 UTC")
        self.assertEqual(result_half_past["utc_birth_label"], "15.07.2026 09:30:00 UTC")
        self.assertNotEqual(result_noon["lagna"]["degree_dms"], result_half_past["lagna"]["degree_dms"])
        self.assertNotEqual(
            result_noon["table_rows"][2]["degree_dms"],
            result_half_past["table_rows"][2]["degree_dms"],
        )

    def test_true_nodes_can_be_direct_on_historical_date(self) -> None:
        historical = build_payload()
        historical.update(
            {
                "birthDate": "1908-12-10",
                "birthTime": "16:14:28",
                "cityName": "Gorna Oryahovitsa",
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
            }
        )

        result = calculate_reading(historical)
        node_rows = rows_by_name(result)

        self.assertEqual(node_rows["Раху"]["retrograde"], node_rows["Кету"]["retrograde"])
        self.assertFalse(node_rows["Раху"]["retrograde"])
        self.assertFalse(node_rows["Кету"]["retrograde"])

    def test_mean_nodes_stay_retrograde_on_same_historical_date(self) -> None:
        historical = build_payload()
        historical.update(
            {
                "birthDate": "1908-12-10",
                "birthTime": "16:14:28",
                "cityName": "Gorna Oryahovitsa",
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
                "nodeMode": "mean",
            }
        )

        result = calculate_reading(historical)
        node_rows = rows_by_name(result)

        self.assertEqual(node_rows["Раху"]["retrograde"], node_rows["Кету"]["retrograde"])
        self.assertTrue(node_rows["Раху"]["retrograde"])
        self.assertTrue(node_rows["Кету"]["retrograde"])


if __name__ == "__main__":
    unittest.main()
