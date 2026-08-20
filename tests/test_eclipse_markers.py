import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
PACKAGES_DIR = WORKSPACE / ".packages"
if PACKAGES_DIR.exists():
    sys.path.insert(0, str(PACKAGES_DIR))

from vedic_app.astro import ECLIPSE_MARKER_KEYS, _eclipse_marker_for_datetime, _julian_day


def utc_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


class EclipseMarkerTests(unittest.TestCase):
    def marker(self, value: str) -> dict | None:
        moment = utc_datetime(value)
        return _eclipse_marker_for_datetime(moment, _julian_day(moment))

    def test_solar_eclipse_day_is_dark_marker(self) -> None:
        marker = self.marker("2024-04-08T12:00:00")
        self.assertIsNotNone(marker)
        self.assertEqual(marker["state"], "day")
        self.assertEqual(marker["kind"], "solar")

    def test_lunar_eclipse_day_is_dark_marker(self) -> None:
        marker = self.marker("2025-03-14T12:00:00")
        self.assertIsNotNone(marker)
        self.assertEqual(marker["state"], "day")
        self.assertEqual(marker["kind"], "lunar")

    def test_adjacent_calendar_day_is_gray_marker(self) -> None:
        marker = self.marker("2024-04-07T12:00:00")
        self.assertEqual(marker["state"], "near")
        self.assertEqual(marker["day_distance"], 1)

    def test_two_to_seven_days_use_outline_marker(self) -> None:
        marker = self.marker("2024-04-03T12:00:00")
        self.assertEqual(marker["state"], "window")
        self.assertEqual(marker["day_distance"], 5)

    def test_outside_seven_days_has_no_marker(self) -> None:
        self.assertIsNone(self.marker("2024-04-17T12:00:00"))

    def test_visual_state_is_wired_to_all_position_tables(self) -> None:
        template = (WORKSPACE / "templates" / "index.html").read_text(encoding="utf-8")
        styles = (WORKSPACE / "static" / "styles.css").read_text(encoding="utf-8")
        script = (WORKSPACE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertGreaterEqual(template.count("data-eclipse-state"), 3)
        self.assertIn("is-eclipse-window", styles)
        self.assertIn("is-eclipse-near", styles)
        self.assertIn("is-eclipse-day", styles)
        self.assertIn("reconcileDesktopEclipseMarkers", script)

    def test_marker_applies_to_both_luminaries(self) -> None:
        self.assertEqual(ECLIPSE_MARKER_KEYS, frozenset({"Sun", "Moon"}))

    def test_august_2026_solar_eclipse_control_range(self) -> None:
        expected = {
            "2026-08-04": None,
            "2026-08-05": "window",
            "2026-08-06": "window",
            "2026-08-07": "window",
            "2026-08-08": "window",
            "2026-08-09": "window",
            "2026-08-10": "window",
            "2026-08-11": "near",
            "2026-08-12": "day",
            "2026-08-13": "near",
            "2026-08-14": "window",
            "2026-08-15": "window",
            "2026-08-16": "window",
            "2026-08-17": "window",
            "2026-08-18": "window",
            "2026-08-19": "window",
            "2026-08-20": None,
        }
        for date_text, state in expected.items():
            marker = self.marker(f"{date_text}T12:00:00")
            if state is None:
                self.assertIsNone(marker, date_text)
            else:
                self.assertIsNotNone(marker, date_text)
                self.assertEqual(marker["state"], state, date_text)

    def test_eclipse_state_rules_share_single_geometry(self) -> None:
        styles = (WORKSPACE / "static" / "styles.css").read_text(encoding="utf-8")
        base_marker = ".desktop-graha-cell.is-eclipse > strong"
        self.assertIn(base_marker, styles)
        base_block = styles.split(base_marker, 1)[1].split("}", 1)[0]
        for geometry_prop in ("min-width", "height", "border-radius", "box-sizing"):
            self.assertIn(geometry_prop, base_block)
        for state in ("window", "near", "day"):
            selector = f".desktop-graha-cell.is-eclipse-{state} > strong"
            self.assertIn(selector, styles)
            state_block = styles.split(selector, 1)[1].split("}", 1)[0]
            for geometry_prop in ("min-width", "height", "border-radius", "padding", "width"):
                self.assertNotIn(geometry_prop, state_block, f"{state} redefines {geometry_prop}")


if __name__ == "__main__":
    unittest.main()
