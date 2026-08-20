import re
import sys
import unittest
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
PACKAGES_DIR = WORKSPACE / ".packages"
if PACKAGES_DIR.exists():
    sys.path.insert(0, str(PACKAGES_DIR))

from vedic_app.astro import _build_nava_tara_table, calculate_reading
from tests.test_outer_planets import build_payload

NATAL_TARA_ORDER = [
    "Ascendant", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
]


def _mock_rows():
    names = {
        "Ascendant": "Пушя",      # №8 → разстояние 5, тара 5 (Пратяк)
        "Sun": "Рохини",          # №4 → разстояние 1, тара 1 (Джанма)
        "Moon": "Рохини",         # рождена накшатра
        "Mars": "Мригашира",      # №5 → разстояние 2, тара 2 (Сампат)
        "Mercury": "Ардра",       # №6 → разстояние 3, тара 3 (Випат)
        "Jupiter": "Ашлеша",      # №9 → разстояние 6, тара 6 (Садхака)
        "Venus": "Магха",          # №10 → разстояние 7, тара 7 (Найдхана)
        "Saturn": "Хаста",        # №13 → разстояние 10, тара 1, цикъл 2
        "Rahu": "Ревати",         # №27 → разстояние 24, тара 6, цикъл 3
        "Ketu": "Ашвини",         # №1 → разстояние 25, тара 7, цикъл 3
    }
    return {key: {"key": key, "nakshatra": name} for key, name in names.items()}


class NavaTaraTests(unittest.TestCase):
    def test_ten_rows_ascendant_first_in_standard_order(self) -> None:
        rows = _build_nava_tara_table(_mock_rows())
        self.assertEqual([row["key"] for row in rows], NATAL_TARA_ORDER)
        self.assertEqual(rows[0]["key"], "Ascendant")
        self.assertEqual(rows[0]["label"], "Асцендент")

    def test_ascendant_pushya_from_rohini(self) -> None:
        rows = _build_nava_tara_table(_mock_rows())
        asc = rows[0]
        self.assertEqual(asc["nakshatra"], "Пушя")
        self.assertEqual(asc["position"], 5)
        self.assertEqual(asc["tara_number"], 5)
        self.assertEqual(asc["tara_name"], "Пратяк")
        self.assertEqual(asc["cycle"], 1)

    def test_moon_is_janma_position_one(self) -> None:
        rows = _build_nava_tara_table(_mock_rows())
        moon = next(row for row in rows if row["key"] == "Moon")
        self.assertEqual(moon["position"], 1)
        self.assertEqual(moon["tara_number"], 1)
        self.assertEqual(moon["tara_name"], "Джанма")
        self.assertEqual(moon["cycle"], 1)

    def test_mars_mrigashira_is_sampat(self) -> None:
        rows = _build_nava_tara_table(_mock_rows())
        mars = next(row for row in rows if row["key"] == "Mars")
        self.assertEqual(mars["position"], 2)
        self.assertEqual(mars["tara_number"], 2)
        self.assertEqual(mars["tara_name"], "Сампат")

    def test_saturn_second_cycle(self) -> None:
        rows = _build_nava_tara_table(_mock_rows())
        saturn = next(row for row in rows if row["key"] == "Saturn")
        self.assertEqual(saturn["position"], 10)
        self.assertEqual(saturn["tara_number"], 1)
        self.assertEqual(saturn["cycle"], 2)

    def test_rahu_ketu_third_cycle(self) -> None:
        rows = _build_nava_tara_table(_mock_rows())
        rahu = next(row for row in rows if row["key"] == "Rahu")
        ketu = next(row for row in rows if row["key"] == "Ketu")
        self.assertEqual(rahu["position"], 24)
        self.assertEqual(rahu["cycle"], 3)
        self.assertEqual(ketu["position"], 25)
        self.assertEqual(ketu["cycle"], 3)

    def test_reference_reading_matches_d1_nakshatras(self) -> None:
        result = calculate_reading(build_payload())
        rows = result["nava_tara"]
        self.assertEqual([row["key"] for row in rows], NATAL_TARA_ORDER)
        d1_by_key = {row["key"]: row for row in result["table_rows"]}
        for row in rows:
            self.assertEqual(row["nakshatra"], d1_by_key[row["key"]]["nakshatra"], row["key"])
        moon = next(row for row in rows if row["key"] == "Moon")
        self.assertEqual(moon["position"], 1)
        self.assertEqual(moon["tara_number"], 1)

    def test_desktop_page_contains_tara_view_and_menu(self) -> None:
        from app import app
        client = app.test_client()
        response = client.post("/", data={**build_payload(), "buildMode": "natal"})
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('data-desktop-analysis-view="tara"', html)
        self.assertIn('data-desktop-analysis="tara"', html)
        self.assertIn("Нава Тара", html)

    def test_bad_taras_marked_red_in_table(self) -> None:
        from app import app
        client = app.test_client()
        response = client.post("/", data={**build_payload(), "buildMode": "natal"})
        html = response.get_data(as_text=True)
        start = html.index("desktop-tara-table")
        end = html.index("</table>", start)
        table = html[start:end]
        pattern = re.compile(r'<td(?: class="([^"]*)")?>\s*(\d+) — ([^<]+)</td>')
        found_bad = set()
        for class_attr, number, name in pattern.findall(table):
            is_bad = "is-bad-tara" in (class_attr or "")
            if int(number) in (3, 5, 7):
                self.assertTrue(is_bad, f"{number} — {name} трябва да е в червено")
                found_bad.add(int(number))
            else:
                self.assertFalse(is_bad, f"{number} — {name} не трябва да е в червено")
        self.assertTrue(found_bad, "Трябва да има поне една лоша тара, отбелязана в червено")
        template_source = (WORKSPACE / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn("row.tara_number in (3, 5, 7)", template_source)


if __name__ == "__main__":
    unittest.main()
