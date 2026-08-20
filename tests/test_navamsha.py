import unittest
from decimal import Decimal

from vedic_app.data import navamsha_sign_index


def _segment_midpoint(segment_index: int) -> float:
    start_arcminutes = Decimal(segment_index) * Decimal("200")
    midpoint_arcminutes = start_arcminutes + Decimal("100")
    return float(midpoint_arcminutes / Decimal("60"))


class NavamshaTableTests(unittest.TestCase):
    def test_reference_rows_match_user_table(self) -> None:
        expected_rows = {
            0: [1, 2, 3, 4, 5, 6, 7, 8, 9],          # Aries
            1: [10, 11, 12, 1, 2, 3, 4, 5, 6],      # Taurus
            2: [7, 8, 9, 10, 11, 12, 1, 2, 3],      # Gemini
            3: [4, 5, 6, 7, 8, 9, 10, 11, 12],      # Cancer
            6: [7, 8, 9, 10, 11, 12, 1, 2, 3],      # Libra
            11: [4, 5, 6, 7, 8, 9, 10, 11, 12],     # Pisces
        }

        for sign_index, expected_sign_numbers in expected_rows.items():
            actual = [
                navamsha_sign_index(sign_index, _segment_midpoint(segment_index)) + 1
                for segment_index in range(9)
            ]
            self.assertEqual(actual, expected_sign_numbers)

    def test_exact_boundary_moves_to_next_navamsha(self) -> None:
        boundary = float(Decimal("200") / Decimal("60"))  # 3°20'
        self.assertEqual(navamsha_sign_index(0, boundary) + 1, 2)  # Aries -> Taurus
        self.assertEqual(navamsha_sign_index(1, boundary) + 1, 11)  # Taurus -> Aquarius


if __name__ == "__main__":
    unittest.main()
