import unittest

from vedic_app.data import CITIES, CITY_LOOKUP


class CityDataTests(unittest.TestCase):
    def test_detailed_bulgarian_and_curated_world_lists_are_combined(self):
        self.assertEqual(2769, len(CITIES))
        self.assertIn("София", CITY_LOOKUP)
        self.assertIn("London, United Kingdom", CITY_LOOKUP)
        self.assertIn("Paris, France", CITY_LOOKUP)
        self.assertIn("Tokyo, Japan", CITY_LOOKUP)

    def test_world_city_records_have_stable_timezones_and_unique_names(self):
        names = [city["name"] for city in CITIES]
        self.assertEqual(len(names), len(set(names)))

        london = CITY_LOOKUP["London, United Kingdom"]
        self.assertEqual("Europe/London", london["timezone"])
        self.assertEqual("GB", london["country_code"])
        self.assertTrue(london["is_capital"])

        world_cities = [city for city in CITIES if city.get("source") == "GeoNames"]
        self.assertTrue(world_cities)
        self.assertFalse(any(city["country_code"] == "BG" for city in world_cities))
        self.assertTrue(
            all(city["is_capital"] or city["population"] >= 250_000 for city in world_cities)
        )


if __name__ == "__main__":
    unittest.main()
