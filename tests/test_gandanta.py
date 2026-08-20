import unittest

from vedic_app.astro import calculate_reading, default_form_values


class GandantaTests(unittest.TestCase):
    def _reading(self):
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
        return calculate_reading(form)

    def test_neptune_in_scorpio_gandanta_is_marked(self):
        rows = {row["key"]: row for row in self._reading()["table_rows"]}
        self.assertTrue(rows["Neptune"]["is_gandanta"])

    def test_sun_outside_gandanta_is_not_marked(self):
        rows = {row["key"]: row for row in self._reading()["table_rows"]}
        self.assertFalse(rows["Sun"]["is_gandanta"])

    def test_gandanta_field_is_present_for_every_graha(self):
        rows = self._reading()["table_rows"]
        grahas = {
            "Ascendant", "Sun", "Moon", "Mercury", "Venus", "Mars",
            "Jupiter", "Saturn", "Rahu", "Ketu", "Uranus", "Neptune", "Pluto",
        }
        for row in rows:
            if row["key"] in grahas:
                self.assertIn("is_gandanta", row)


if __name__ == "__main__":
    unittest.main()
