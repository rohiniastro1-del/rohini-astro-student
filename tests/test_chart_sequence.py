import unittest

from vedic_app.chart import build_sign_sequence


class ChartSequenceTests(unittest.TestCase):
    def test_sequence_from_taurus_lagna_runs_counterclockwise(self) -> None:
        self.assertEqual(
            build_sign_sequence(2),
            {
                1: 2,
                2: 3,
                3: 4,
                4: 5,
                5: 6,
                6: 7,
                7: 8,
                8: 9,
                9: 10,
                10: 11,
                11: 12,
                12: 1,
            },
        )

    def test_sequence_wraps_after_pisces(self) -> None:
        self.assertEqual(
            build_sign_sequence(7),
            {
                1: 7,
                2: 8,
                3: 9,
                4: 10,
                5: 11,
                6: 12,
                7: 1,
                8: 2,
                9: 3,
                10: 4,
                11: 5,
                12: 6,
            },
        )


if __name__ == "__main__":
    unittest.main()
