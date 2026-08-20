import sys
import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
PACKAGES_DIR = WORKSPACE / ".packages"
if PACKAGES_DIR.exists():
    sys.path.insert(0, str(PACKAGES_DIR))

from vedic_app.astro import _apply_planetary_war


def row(key: str, label: str, longitude: float) -> dict:
    return {
        "key": key,
        "label": label,
        "longitude": longitude,
        "sign_index": int(longitude // 30),
    }


class PlanetaryWarTests(unittest.TestCase):
    def test_lower_exact_degree_wins_within_one_sign(self) -> None:
        rows = {
            "Mercury": row("Mercury", "Ме", 106 + 15 / 60 + 9 / 3600),
            "Jupiter": row("Jupiter", "Юп", 105 + 58 / 60 + 30 / 3600),
        }
        _apply_planetary_war(rows)
        self.assertTrue(rows["Mercury"]["is_planetary_war"])
        self.assertEqual(rows["Mercury"]["planetary_war_result"], "loser")
        self.assertEqual(rows["Jupiter"]["planetary_war_result"], "winner")

    def test_seconds_decide_when_degree_and_minute_match(self) -> None:
        rows = {
            "Venus": row("Venus", "Ве", 76 + 12 / 60 + 8 / 3600),
            "Mars": row("Mars", "Ма", 76 + 12 / 60 + 41 / 3600),
        }
        _apply_planetary_war(rows)
        self.assertEqual(rows["Venus"]["planetary_war_result"], "winner")
        self.assertEqual(rows["Mars"]["planetary_war_result"], "loser")

    def test_exactly_one_degree_is_not_war(self) -> None:
        rows = {
            "Mercury": row("Mercury", "Ме", 100.0),
            "Venus": row("Venus", "Ве", 101.0),
        }
        _apply_planetary_war(rows)
        self.assertFalse(rows["Mercury"]["is_planetary_war"])
        self.assertFalse(rows["Venus"]["is_planetary_war"])

    def test_neighbouring_signs_never_fight(self) -> None:
        rows = {
            "Mars": row("Mars", "Ма", 29.8),
            "Saturn": row("Saturn", "Са", 30.2),
        }
        _apply_planetary_war(rows)
        self.assertFalse(rows["Mars"]["is_planetary_war"])
        self.assertFalse(rows["Saturn"]["is_planetary_war"])

    def test_excluded_bodies_never_participate(self) -> None:
        rows = {
            key: row(key, key, 116.0 + index / 10)
            for index, key in enumerate(("Sun", "Moon", "Rahu", "Ketu"))
        }
        _apply_planetary_war(rows)
        self.assertTrue(all(not item["is_planetary_war"] for item in rows.values()))

    def test_visual_markers_do_not_replace_status_slots(self) -> None:
        template = (WORKSPACE / "templates" / "index.html").read_text(encoding="utf-8")
        styles = (WORKSPACE / "static" / "styles.css").read_text(encoding="utf-8")
        self.assertIn("planetary-war-badge", template)
        self.assertIn("is-planetary-war", styles)
        self.assertIn("desktop-graha-cell > .planetary-war-badge", styles)


if __name__ == "__main__":
    unittest.main()
