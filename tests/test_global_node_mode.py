import json
import sys
import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
PACKAGES_DIR = WORKSPACE / ".packages"
if PACKAGES_DIR.exists():
    sys.path.insert(0, str(PACKAGES_DIR))

from app import app, apply_global_node_mode, build_jhd_file, parse_jhd_to_form_values
from vedic_app.astro import calculate_reading, default_form_values


def build_payload(node_mode: str) -> dict[str, str]:
    """Глобален режим на възлите: една и съща стойност се подава и за
    рождената, и за транзитната карта (както прави глобалният избор)."""
    payload = default_form_values()
    payload.update(
        {
            "birthDate": "1990-07-15",
            "birthTime": "10:30:00",
            "cityName": "София",
            "latitudeDegrees": "42",
            "latitudeMinutes": "42",
            "latitudeHemisphere": "N",
            "longitudeDegrees": "23",
            "longitudeMinutes": "19",
            "longitudeHemisphere": "E",
            "timezoneMode": "manual",
            "manualTzSign": "+",
            "manualTzHours": "3",
            "manualTzMinutes": "0",
            "nodeMode": node_mode,
            "transitNodeMode": node_mode,
            "transitDate": "2026-08-17",
            "transitTime": "12:00:00",
        }
    )
    return payload


def rahu_ketu_longitudes(chart: dict) -> tuple[float, float]:
    rows = chart["raw_rows"]
    return float(rows["Rahu"]["longitude"]), float(rows["Ketu"]["longitude"])


class GlobalNodeModeTests(unittest.TestCase):
    def test_natal_rahu_ketu_change_with_node_mode(self) -> None:
        mean = calculate_reading(build_payload("mean"), build_mode="natal")
        true = calculate_reading(build_payload("true"), build_mode="natal")

        mean_rahu, mean_ketu = rahu_ketu_longitudes(mean)
        true_rahu, true_ketu = rahu_ketu_longitudes(true)

        self.assertNotAlmostEqual(mean_rahu, true_rahu, places=4)
        self.assertAlmostEqual((mean_ketu - mean_rahu) % 360, 180.0, places=4)
        self.assertAlmostEqual((true_ketu - true_rahu) % 360, 180.0, places=4)

        self.assertEqual(mean["node_mode_label"], "Среден възел")
        self.assertEqual(true["node_mode_label"], "Истинен възел")

    def test_transit_rahu_ketu_change_with_node_mode(self) -> None:
        mean = calculate_reading(build_payload("mean"), build_mode="transit")
        true = calculate_reading(build_payload("true"), build_mode="transit")

        mean_rahu, _ = rahu_ketu_longitudes(mean["transit"])
        true_rahu, _ = rahu_ketu_longitudes(true["transit"])

        self.assertNotAlmostEqual(mean_rahu, true_rahu, places=4)
        self.assertEqual(mean["transit"]["node_mode_label"], "Среден възел")
        self.assertEqual(true["transit"]["node_mode_label"], "Истинен възел")

    def test_global_node_mode_reaches_both_natal_and_transit(self) -> None:
        """Една глобална стойност трябва да се приложи и към рождената, и към
        транзитната карта, а не само към едната."""
        result = calculate_reading(build_payload("mean"), build_mode="transit")
        self.assertEqual(result["node_mode_label"], "Среден възел")
        self.assertEqual(result["transit"]["node_mode_label"], "Среден възел")

    def test_d1_chart_payload_reflects_node_mode(self) -> None:
        mean = calculate_reading(build_payload("mean"), build_mode="natal")
        true = calculate_reading(build_payload("true"), build_mode="natal")
        self.assertNotEqual(
            json.dumps(mean["d1_chart_data"], sort_keys=True, ensure_ascii=False),
            json.dumps(true["d1_chart_data"], sort_keys=True, ensure_ascii=False),
        )

    def test_cookie_persists_global_node_mode(self) -> None:
        client = app.test_client()
        client.set_cookie("rohini_node_mode", "mean")
        response = client.get("/")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="globalNodeMode"', html)
        self.assertIn('value="mean" selected', html)
        self.assertIn('id="nodeMode" value="mean"', html)
        self.assertIn('id="transitNodeMode" value="mean"', html)

    def test_open_jhd_applies_global_node_mode(self) -> None:
        # Запазваме хороскоп; .jhd файлът не съхранява режима на възлите,
        # затова при отваряне трябва да се приложи глобалната настройка.
        payload = build_payload("true")
        result = calculate_reading(payload, build_mode="natal")
        content, _ = build_jhd_file(result, payload)

        with app.test_request_context("/", headers={"Cookie": "rohini_node_mode=mean"}):
            form_values = parse_jhd_to_form_values(content)
            apply_global_node_mode(form_values)
            self.assertEqual(form_values["nodeMode"], "mean")
            self.assertEqual(form_values["transitNodeMode"], "mean")
            rebuilt = calculate_reading(form_values, build_mode="natal")
            self.assertEqual(rebuilt["node_mode_label"], "Среден възел")
            mean_rahu = float(rebuilt["raw_rows"]["Rahu"]["longitude"])

        with app.test_request_context("/", headers={"Cookie": "rohini_node_mode=true"}):
            form_values = parse_jhd_to_form_values(content)
            apply_global_node_mode(form_values)
            self.assertEqual(form_values["nodeMode"], "true")
            self.assertEqual(form_values["transitNodeMode"], "true")
            rebuilt = calculate_reading(form_values, build_mode="natal")
            self.assertEqual(rebuilt["node_mode_label"], "Истинен възел")
            true_rahu = float(rebuilt["raw_rows"]["Rahu"]["longitude"])

        # Двата режима дават различна позиция на Раху — глобалната настройка
        # наистина се прилага при препострояване на картата.
        self.assertNotAlmostEqual(mean_rahu, true_rahu, places=4)

    def test_open_jhd_without_cookie_keeps_default_node_mode(self) -> None:
        payload = build_payload("true")
        result = calculate_reading(payload, build_mode="natal")
        content, _ = build_jhd_file(result, payload)

        with app.test_request_context("/"):
            form_values = parse_jhd_to_form_values(content)
            apply_global_node_mode(form_values)
            # Без cookie се ползва стойността по подразбиране („Истинен“).
            self.assertEqual(form_values["nodeMode"], "true")
            rebuilt = calculate_reading(form_values, build_mode="natal")
            self.assertEqual(rebuilt["node_mode_label"], "Истинен възел")


if __name__ == "__main__":
    unittest.main()
