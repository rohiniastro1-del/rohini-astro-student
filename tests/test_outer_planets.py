import sys
import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
PACKAGES_DIR = WORKSPACE / ".packages"
if PACKAGES_DIR.exists():
    sys.path.insert(0, str(PACKAGES_DIR))

from app import app
from vedic_app.astro import calculate_reading, default_form_values
from vedic_app.data import PLANET_ORDER


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
        }
    )
    return payload


class OuterPlanetTests(unittest.TestCase):
    def test_outer_planets_follow_ketu_in_table_and_all_divisional_payloads(self) -> None:
        result = calculate_reading(build_payload())
        physical_keys = {"Ascendant", *PLANET_ORDER}
        physical_rows = [row for row in result["table_rows"] if row["key"] in physical_keys]
        self.assertEqual(
            [row["name"] for row in physical_rows[-4:]],
            ["Кету", "Уран", "Нептун", "Плутон"],
        )
        self.assertEqual(
            [row["jyotish_name"] for row in physical_rows[-3:]],
            ["Праджапати", "Варуна", "Яма"],
        )
        for bundle in result["divisional_charts"].values():
            items = [item for house in bundle["payload"]["houses"] for item in house["items"]]
            self.assertTrue({"Ур", "Не", "Пл"}.issubset(items))

    def test_desktop_degree_table_always_lists_outer_planets(self) -> None:
        client = app.test_client()
        response = client.post("/", data={**build_payload(), "buildMode": "natal"})
        html = response.get_data(as_text=True)
        table_start = html.index('class="desktop-position-table"')
        table_end = html.index("</table>", table_start)
        degree_table = html[table_start:table_end]

        self.assertEqual(response.status_code, 200)
        self.assertIn("Ур", degree_table)
        self.assertIn("Не", degree_table)
        self.assertIn("Пл", degree_table)

    def test_checkbox_is_in_data_settings_and_persists_on_post(self) -> None:
        client = app.test_client()
        response = client.post(
            "/",
            data={**build_payload(), "buildMode": "natal", "showOuterPlanets": "on"},
        )
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="showOuterPlanets"', html)
        self.assertRegex(html, r'<form[^>]+id="birthForm"[\s\S]*?id="showOuterPlanets"')
        self.assertIn("Показвай Уран, Нептун и Плутон във всички карти", html)
        self.assertIn("/Праджапати/", html)
        self.assertIn("/Варуна/", html)
        self.assertIn("/Яма/", html)
        self.assertRegex(html, r'id="showOuterPlanets"[\s\S]*?checked')


if __name__ == "__main__":
    unittest.main()
