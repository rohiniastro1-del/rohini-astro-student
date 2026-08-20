from __future__ import annotations

import unittest
from datetime import datetime

from vedic_app.astro import calculate_reading, default_form_values
from vedic_app.dasha_systems import build_dasha_rows


def _reference_form() -> dict[str, str]:
    form = default_form_values()
    form.update(
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
        }
    )
    return form


def _reading():
    return calculate_reading(_reference_form(), build_mode="natal")


def _top_rows(system: str):
    results = _reading()
    return build_dasha_rows(
        system,
        results["table_rows"],
        results["local_datetime"],
        [],
        None,
        None,
    )


def assert_time_close(test: unittest.TestCase, actual: str, expected: str) -> None:
    actual_dt = datetime.strptime(actual, "%Y-%m-%d %H:%M:%S")
    expected_dt = datetime.strptime(expected, "%Y-%m-%d %H:%M:%S")
    test.assertLessEqual(abs((actual_dt - expected_dt).total_seconds()), 1)


class DashaSystemsReferenceTest(unittest.TestCase):
    def test_vimshottari_matches_reference(self) -> None:
        rows = _top_rows("vimshottari")
        expected_labels = ["Сл", "Лу", "Ма", "Ра", "Юп", "Са", "Ме", "Ке", "Ве"]
        expected = [
            ("1979-07-21 19:43:51", "1985-07-21 06:36:22"),
            ("1985-07-21 06:36:22", "1995-07-21 16:43:55"),
            ("1995-07-21 16:43:55", "2002-07-21 09:25:11"),
            ("2002-07-21 09:25:11", "2020-07-20 18:02:45"),
            ("2020-07-20 18:02:45", "2036-07-20 15:02:48"),
        ]
        self.assertEqual([row["label"] for row in rows], expected_labels)
        for row, (start, end) in zip(rows, expected):
            assert_time_close(self, row["start_label"], start)
            assert_time_close(self, row["end_label"], end)

    def test_children_are_continuous_and_exhaust_parent(self) -> None:
        results = _reading()
        top = build_dasha_rows("vimshottari", results["table_rows"], results["local_datetime"], [], None, None)
        first = top[0]
        children = build_dasha_rows(
            "vimshottari",
            results["table_rows"],
            results["local_datetime"],
            first["path"],
            datetime.fromisoformat(first["start"]),
            datetime.fromisoformat(first["end"]),
        )
        self.assertGreaterEqual(len(children), 1)
        for previous, current in zip(children, children[1:]):
            self.assertEqual(previous["end"], current["start"])
        self.assertEqual(children[-1]["end"], first["end"])

    def test_unknown_system_raises(self) -> None:
        with self.assertRaises(ValueError):
            _top_rows("unknown-system")


if __name__ == "__main__":
    unittest.main()
