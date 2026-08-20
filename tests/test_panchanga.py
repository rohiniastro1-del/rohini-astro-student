import unittest

from vedic_app.astro import calculate_reading, default_form_values
from vedic_app.panchanga import HORA_SEQUENCE, WEEKDAY_LORDS


class PanchangaTests(unittest.TestCase):
    def _reading(self, build_mode="natal"):
        form = default_form_values()
        form.update(
            {
                "birthDate": "1980-12-10",
                "birthTime": "16:14:28",
                "cityName": "София",
                "transitDate": "2026-08-13",
                "transitTime": "19:09:04",
                "transitCityName": "София",
            }
        )
        return calculate_reading(form, build_mode=build_mode)

    def test_hidden_bundle_contains_vara_and_hora(self):
        panchanga = self._reading()["panchanga"]
        self.assertEqual({"vara", "hora"}, set(panchanga) - {"calculation_standard"})

    def test_vara_and_hora_lords_are_valid(self):
        panchanga = self._reading()["panchanga"]
        self.assertIn(panchanga["vara"]["lord"], WEEKDAY_LORDS)
        self.assertIn(panchanga["hora"]["lord"], HORA_SEQUENCE)

    def test_vara_and_hora_percentages_sum_to_hundred(self):
        panchanga = self._reading()["panchanga"]
        for key in ("vara", "hora"):
            self.assertAlmostEqual(
                100.0,
                panchanga[key]["elapsed_percent"] + panchanga[key]["remaining_percent"],
                places=2,
            )

    def test_transit_build_has_separate_panchanga_for_transit_moment(self):
        reading = self._reading(build_mode="transit")
        self.assertIn("panchanga", reading["transit"])
        self.assertNotEqual(reading["panchanga"]["vara"], reading["transit"]["panchanga"]["vara"])

    def test_reference_panchanga_hora_lord(self):
        form = default_form_values()
        form.update(
            {
                "birthDate": "1980-12-10",
                "birthTime": "16:14:28",
                "cityName": "Reference",
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
            }
        )
        panchanga = calculate_reading(form)["panchanga"]
        self.assertEqual("Луна", panchanga["hora"]["lord"])


if __name__ == "__main__":
    unittest.main()
