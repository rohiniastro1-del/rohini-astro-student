import sys
import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
PACKAGES_DIR = WORKSPACE / ".packages"
if PACKAGES_DIR.exists():
    sys.path.insert(0, str(PACKAGES_DIR))

from vedic_app.divisional import (
    calculate_d2,
    calculate_d3,
    calculate_d4,
    calculate_d7,
    calculate_d9,
    calculate_d10,
    calculate_d12,
    calculate_d24,
    calculate_amsha_details,
    calculate_divisional_placement,
)


class DivisionalLogicTests(unittest.TestCase):
    @staticmethod
    def degree(degrees: int, minutes: int = 0, seconds: int = 0) -> float:
        return degrees + (minutes / 60) + (seconds / 3600)

    def test_d2_uses_exact_odd_even_hora_logic(self) -> None:
        self.assertEqual(calculate_d2(0, 0.0), 4)  # Aries first half -> Leo
        self.assertEqual(calculate_d2(0, 15.0), 3)  # Aries second half -> Cancer
        self.assertEqual(calculate_d2(1, 0.0), 3)  # Taurus first half -> Cancer
        self.assertEqual(calculate_d2(1, 15.0), 4)  # Taurus second half -> Leo

    def test_d3_matches_same_fifth_ninth_offsets(self) -> None:
        self.assertEqual(calculate_d3(0, 9.999999), 0)  # Aries -> Aries
        self.assertEqual(calculate_d3(0, 10.0), 4)  # Aries -> Leo
        self.assertEqual(calculate_d3(0, 20.0), 8)  # Aries -> Sagittarius

    def test_d4_matches_modality_quarters(self) -> None:
        self.assertEqual(calculate_d4(7, 3 + (17 / 60)), 7)  # Scorpio 03:17 -> Scorpio
        self.assertEqual(calculate_d4(11, 19 + (3 / 60)), 5)  # Pisces 19:03 -> Virgo

    def test_d7_matches_reference_examples(self) -> None:
        self.assertEqual(calculate_d7(5, 11 + (1 / 60)), 1)  # Virgo 11:01 -> Taurus
        self.assertEqual(calculate_d7(3, 25 + (40 / 60)), 2)  # Cancer 25:40 -> Gemini

    def test_amsha_details_match_d9_reference_progress(self) -> None:
        details = calculate_amsha_details("D9", 0, self.degree(19, 36, 38))
        self.assertEqual(details["number"], 6)
        self.assertEqual(details["percentage"], 88)
        self.assertEqual(details["size_label"], "03°20′00″")

    def test_d9_keeps_existing_navamsha_logic(self) -> None:
        self.assertEqual(calculate_d9(0, 0.0), 0)  # Aries first Navamsha -> Aries
        self.assertEqual(calculate_d9(1, 3 + (20 / 60)), 10)  # Taurus second Navamsha starts Aquarius

    def test_d10_matches_reference_example(self) -> None:
        self.assertEqual(calculate_d10(6, 7 + (20 / 60)), 8)  # Libra 7:20 -> Sagittarius
        self.assertEqual(calculate_d10(3, 0.0), 11)  # Cancer first Dashamsha -> Pisces

    def test_d12_counts_from_same_sign(self) -> None:
        self.assertEqual(calculate_d12(7, 0.0), 7)  # Scorpio first -> Scorpio
        self.assertEqual(calculate_d12(7, 27.5), 6)  # Scorpio twelfth -> Libra

    def test_d24_uses_leo_for_odd_and_cancer_for_even(self) -> None:
        self.assertEqual(calculate_d24(0, 0.0), 4)  # Aries first -> Leo
        self.assertEqual(calculate_d24(0, 1.25), 5)  # Aries second -> Virgo
        self.assertEqual(calculate_d24(1, 0.0), 3)  # Taurus first -> Cancer
        self.assertEqual(calculate_d24(1, 1.25), 4)  # Taurus second -> Leo

    def test_common_dispatcher_returns_none_for_unsupported_chart_type(self) -> None:
        self.assertEqual(calculate_divisional_placement("D4", 11, 19 + (3 / 60)), 5)
        self.assertIsNone(calculate_divisional_placement("D108", 0, 0.0))


if __name__ == "__main__":
    unittest.main()
