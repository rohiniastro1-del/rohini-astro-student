import unittest
from datetime import datetime, timedelta

from app import app
from vedic_app.astro import _calculate_chart, calculate_lagna_sign, default_form_values


SUPPORTED_CHARTS = ("D1", "D2", "D3", "D4", "D7", "D9", "D10", "D12", "D24")


class LagnaBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.form = default_form_values()
        cls.form.update(
            {
                "birthDate": "1980-12-10",
                "birthTime": "16:14:28",
                "cityName": "Горна Оряховица",
                "latitudeDegrees": "43",
                "latitudeMinutes": "8",
                "latitudeSeconds": "0",
                "latitudeHemisphere": "N",
                "longitudeDegrees": "25",
                "longitudeMinutes": "42",
                "longitudeSeconds": "0",
                "longitudeHemisphere": "E",
                "timezoneMode": "manual",
                "manualTzSign": "+",
                "manualTzHours": "2",
                "manualTzMinutes": "0",
            }
        )
        cls.client = app.test_client()

    @staticmethod
    def moved_form(form: dict[str, str], offset_seconds: float) -> dict[str, str]:
        value = datetime.fromisoformat(f"{form['birthDate']}T{form['birthTime']}")
        value += timedelta(seconds=offset_seconds)
        return dict(
            form,
            birthDate=value.date().isoformat(),
            birthTime=value.isoformat(timespec="microseconds").split("T", 1)[1],
        )

    @staticmethod
    def form_from_boundary(form: dict[str, str], boundary: dict[str, str]) -> dict[str, str]:
        return dict(form, birthDate=boundary["date"], birthTime=boundary["time"])

    def sign_at_offset(self, form: dict[str, str], chart_code: str, offset_seconds: float) -> int:
        moved = self.moved_form(form, offset_seconds)
        return calculate_lagna_sign(moved, chart_code, "natal")

    def boundary_response(self, form: dict[str, str], chart_code: str) -> dict[str, object]:
        response = self.client.post(
            "/api/chart-context/lagna-boundaries",
            json={"form": form, "chart_code": chart_code, "prefix": "natal"},
        )
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def test_boundaries_preserve_subsecond_precision_for_every_chart(self) -> None:
        for chart_code in SUPPORTED_CHARTS:
            with self.subTest(chart_code=chart_code):
                result = self.boundary_response(self.form, chart_code)
                current_sign = result["sign_number"]
                backward = result["backward_seconds"]
                forward = result["forward_seconds"]

                self.assertIn(".", result["backward"]["time"])
                self.assertIn(".", result["forward"]["time"])
                self.assertEqual(self.sign_at_offset(self.form, chart_code, -backward + 0.001), current_sign)
                self.assertNotEqual(
                    calculate_lagna_sign(self.form_from_boundary(self.form, result["backward"]), chart_code, "natal"),
                    current_sign,
                )
                self.assertEqual(self.sign_at_offset(self.form, chart_code, forward - 0.001), current_sign)
                self.assertNotEqual(
                    calculate_lagna_sign(self.form_from_boundary(self.form, result["forward"]), chart_code, "natal"),
                    current_sign,
                )

    def test_repeated_moves_do_not_lose_the_precise_boundary(self) -> None:
        for chart_code in SUPPORTED_CHARTS:
            for direction in ("forward", "backward"):
                form = dict(self.form)
                for _step in range(4):
                    result = self.boundary_response(form, chart_code)
                    current_sign = calculate_lagna_sign(form, chart_code, "natal")
                    form = self.form_from_boundary(form, result[direction])
                    self.assertNotEqual(calculate_lagna_sign(form, chart_code, "natal"), current_sign)
                    self.assertIn(".", form["birthTime"])

    def test_d1_boundary_is_astronomically_at_the_sign_edge(self) -> None:
        result = self.boundary_response(self.form, "D1")
        backward_chart = _calculate_chart(
            self.form_from_boundary(self.form, result["backward"]), "natal", "Раши", include_d9=True
        )
        forward_chart = _calculate_chart(
            self.form_from_boundary(self.form, result["forward"]), "natal", "Раши", include_d9=True
        )
        backward_degree = float(backward_chart["raw_rows"]["Ascendant"]["degree_in_sign"])
        forward_degree = float(forward_chart["raw_rows"]["Ascendant"]["degree_in_sign"])

        self.assertLess((30.0 - backward_degree) * 3600.0, 0.01)
        self.assertLess(forward_degree * 3600.0, 0.01)
        self.assertEqual(backward_chart["lagna"]["degree_dms"], "29° 59' 59\"")
        self.assertEqual(forward_chart["lagna"]["degree_dms"], "00° 00' 00\"")

    def test_browser_applies_the_precise_boundary_without_integer_shifting(self) -> None:
        with open("static/app.js", encoding="utf-8") as source_file:
            source = source_file.read()

        self.assertIn("const boundary = forward ? contextBoundary.forward : contextBoundary.backward;", source)
        self.assertIn('hidden.dataset.subsecond = preciseTime?.[1] || "";', source)
        self.assertIn('${target.dataset.subsecond || ""}', source)
        self.assertIn("Math.round(Number(seconds) || 0)", source)


if __name__ == "__main__":
    unittest.main()
