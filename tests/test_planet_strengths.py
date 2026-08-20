import sys
import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
PACKAGES_DIR = WORKSPACE / ".packages"
if PACKAGES_DIR.exists():
    sys.path.insert(0, str(PACKAGES_DIR))

from app import app
from tests.test_outer_planets import build_payload
from vedic_app.astro import calculate_reading
from vedic_app.strengths import _special_status, _status_degree_details, build_ashtakavarga, build_relationship_table


class RelationshipTests(unittest.TestCase):
    def test_classical_exaltation_and_debilitation_exact_degrees(self) -> None:
        expected = {"Sun": "10°", "Moon": "3°", "Mars": "28°", "Mercury": "15°", "Jupiter": "5°", "Venus": "27°", "Saturn": "20°"}
        for planet, degree in expected.items():
            self.assertEqual(_status_degree_details(planet, "exaltation"), (degree, "up"))
            self.assertEqual(_status_degree_details(planet, "debilitation"), (degree, "down"))
        self.assertEqual(_status_degree_details("Rahu", "exaltation"), (None, None))
        self.assertEqual(_status_degree_details("Ketu", "debilitation"), (None, None))

    def test_rahu_and_ketu_dignities_follow_brihat_parashara_source(self) -> None:
        self.assertEqual(_special_status("Rahu", 1, 12.0), "exaltation")
        self.assertEqual(_special_status("Rahu", 7, 12.0), "debilitation")
        self.assertEqual(_special_status("Rahu", 2, 12.0), "moolatrikona")
        self.assertEqual(_special_status("Rahu", 10, 12.0), "own")

        self.assertEqual(_special_status("Ketu", 7, 12.0), "exaltation")
        self.assertEqual(_special_status("Ketu", 1, 12.0), "debilitation")
        self.assertEqual(_special_status("Ketu", 8, 12.0), "moolatrikona")
        self.assertNotEqual(_special_status("Ketu", 7, 12.0), "own")

    def test_special_dignities_hide_natural_and_temporary_relations(self) -> None:
        rows = {
            key: {"sign_index": 0, "degree_in_sign": 15.0}
            for key in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
        }
        rows["Rahu"] = {"sign_index": 1, "degree_in_sign": 12.0}
        relationship = next(row for row in build_relationship_table(rows) if row["key"] == "Rahu")
        self.assertEqual(relationship["status"], "Екзалтация")
        self.assertEqual(relationship["natural"], "–")
        self.assertEqual(relationship["temporary"], "–")
        self.assertIsNone(relationship["status_degree"])
        self.assertIsNone(relationship["status_direction"])

        rows["Jupiter"] = {"sign_index": 3, "degree_in_sign": 19.0}
        rows["Moon"] = {"sign_index": 7, "degree_in_sign": 19.0}
        relationships = {row["key"]: row for row in build_relationship_table(rows)}
        self.assertEqual(relationships["Jupiter"]["status_degree"], "5°")
        self.assertEqual(relationships["Jupiter"]["status_direction"], "up")
        self.assertEqual(relationships["Moon"]["status_degree"], "3°")
        self.assertEqual(relationships["Moon"]["status_direction"], "down")

    def test_relationships_cover_classical_and_nodes(self) -> None:
        result = calculate_reading(build_payload())
        relationships = result["relationships"]

        self.assertEqual(
            [row["key"] for row in relationships],
            ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"],
        )

    def test_transit_has_no_separate_relationship_payload(self) -> None:
        payload = build_payload()
        payload.update({
            "transitDate": "2026-08-10", "transitTime": "12:00:00",
            "transitLatitudeDegrees": "42", "transitLatitudeMinutes": "42",
            "transitLatitudeHemisphere": "N", "transitLongitudeDegrees": "23",
            "transitLongitudeMinutes": "19", "transitLongitudeHemisphere": "E",
            "transitTimezoneMode": "manual", "transitManualTzSign": "+",
            "transitManualTzHours": "3", "transitManualTzMinutes": "0",
            "transitNodeMode": "true",
        })
        result = calculate_reading(payload, build_mode="transit")
        self.assertNotIn("relationships", result["transit"])
        self.assertIn("relationships", result)

    def test_relationship_block_is_collapsed_below_natal_planet_table(self) -> None:
        response = app.test_client().post("/", data={**build_payload(), "buildMode": "natal"})
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        relationship_index = html.index("Отношения на планетите")
        planet_table_index = html.index("Таблица на Лагна и планетите")
        self.assertGreater(relationship_index, planet_table_index)
        self.assertIn('<details class="accordion strength-master">', html)
        self.assertNotIn('<details class="accordion strength-master" open', html)
        self.assertIn("Отношение на планетите в знака", html)
        self.assertRegex(html, r"Венера[\s\S]*?<td>–</td>[\s\S]*?<td>–</td>[\s\S]*?Собствен знак")


class AshtakavargaTests(unittest.TestCase):
    def test_ashtakavarga_control_sums(self) -> None:
        result = calculate_reading(build_payload())
        ashtakavarga = result["ashtakavarga"]
        self.assertEqual(
            [row["total"] for row in ashtakavarga["rows"]],
            [48, 49, 39, 54, 56, 52, 39],
        )
        self.assertEqual(ashtakavarga["sav_total"], 337)

    def test_ashtakavarga_control_sums_are_position_independent(self) -> None:
        rows = {
            key: {"sign_index": index % 12}
            for index, key in enumerate(("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Ascendant"))
        }
        result = build_ashtakavarga(rows)
        self.assertEqual([row["total"] for row in result["rows"]], [48, 49, 39, 54, 56, 52, 39])
        self.assertEqual(result["sav_total"], 337)

    def test_desktop_page_contains_ashtakavarga_view_and_menu(self) -> None:
        response = app.test_client().post("/", data={**build_payload(), "buildMode": "natal"})
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('data-desktop-analysis-view="ashtakavarga"', html)
        self.assertIn('data-desktop-analysis="ashtakavarga"', html)
        self.assertIn("САВ", html)


if __name__ == "__main__":
    unittest.main()
