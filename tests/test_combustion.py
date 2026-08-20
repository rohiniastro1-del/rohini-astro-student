import sys
import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
PACKAGES_DIR = WORKSPACE / ".packages"
if PACKAGES_DIR.exists():
    sys.path.insert(0, str(PACKAGES_DIR))

from app import app
from vedic_app.astro import _angular_separation, _is_planet_combust, calculate_reading, default_form_values


class CombustionTests(unittest.TestCase):
    def test_separation_is_symmetric_across_zero_aries(self) -> None:
        self.assertAlmostEqual(_angular_separation(358.0, 2.0), 4.0)
        self.assertAlmostEqual(_angular_separation(2.0, 358.0), 4.0)

    def test_five_degree_orb_is_inclusive_on_both_sides(self) -> None:
        sun = 116.5
        self.assertTrue(_is_planet_combust("Venus", sun, sun, 5.0))
        self.assertTrue(_is_planet_combust("Venus", 116.0, sun, 5.0))
        self.assertTrue(_is_planet_combust("Venus", sun - 5.0, sun, 5.0))
        self.assertTrue(_is_planet_combust("Venus", sun + 5.0, sun, 5.0))
        self.assertFalse(_is_planet_combust("Venus", sun + 5.0001, sun, 5.0))
        self.assertFalse(_is_planet_combust("Sun", sun, sun, 5.0))

    def test_only_supported_planets_can_be_marked_combust(self) -> None:
        payload = default_form_values()
        payload["combustionOrbDegrees"] = "30"
        result = calculate_reading(payload)
        rows = {row["key"]: row for row in result["table_rows"]}
        allowed = {"Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
        for key, row in rows.items():
            if row["is_combust"]:
                self.assertIn(key, allowed)
                self.assertLessEqual(row["combustion_distance"], 30.0)
        self.assertFalse(rows["Sun"]["is_combust"])
        self.assertFalse(rows["Rahu"]["is_combust"])
        self.assertFalse(rows["Ketu"]["is_combust"])

    def test_saved_cookie_is_used_on_fresh_open(self) -> None:
        client = app.test_client()
        client.set_cookie("rohini_combustion_orb", "7.5")
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="combustionOrbDegrees"', response.get_data(as_text=True))
        self.assertIn('value="7.5"', response.get_data(as_text=True))

    def test_stale_browser_storage_cannot_override_the_active_orb(self) -> None:
        source = (WORKSPACE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn('localStorage.getItem("rohini.combustionOrbDegrees")', source)
        self.assertNotIn('localStorage.setItem("rohini.combustionOrbDegrees"', source)

    def test_stale_zero_orb_is_migrated_to_five_degrees(self) -> None:
        payload = default_form_values()
        payload["birthDate"] = "2027-08-14"
        payload["birthTime"] = "14:24:10"
        payload["combustionOrbDegrees"] = "0"
        rows = {row["key"]: row for row in calculate_reading(payload)["table_rows"]}
        self.assertEqual(payload["combustionOrbDegrees"], "5")
        self.assertTrue(rows["Mercury"]["is_combust"])
        self.assertTrue(rows["Venus"]["is_combust"])


if __name__ == "__main__":
    unittest.main()
