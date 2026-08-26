import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


WORKSPACE = Path(__file__).resolve().parent.parent
PACKAGES_DIR = WORKSPACE / ".packages"
if PACKAGES_DIR.exists():
    sys.path.insert(0, str(PACKAGES_DIR))

import app as app_module


class PersistentUserSettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.settings_path = Path(self.temporary_directory.name) / "user-settings.json"
        self.path_patch = patch.object(app_module, "USER_SETTINGS_PATH", self.settings_path)
        self.path_patch.start()

    def tearDown(self) -> None:
        self.path_patch.stop()
        self.temporary_directory.cleanup()

    def test_style_orb_and_nodes_survive_a_fresh_client(self) -> None:
        first_client = app_module.app.test_client()
        response = first_client.post(
            "/api/user-settings",
            json={
                "chart_style": "south",
                "combustion_orb": 7.5,
                "node_mode": "mean",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(self.settings_path.read_text(encoding="utf-8")),
            {
                "chart_style": "south",
                "combustion_orb": "7.5",
                "node_mode": "mean",
            },
        )

        # Новият клиент няма localStorage или cookies от предишното отваряне.
        # Настройките пак идват от постоянния локален файл.
        second_client = app_module.app.test_client()
        page = second_client.get("/")
        html = page.get_data(as_text=True)
        self.assertEqual(page.status_code, 200)
        self.assertIn('data-persistent-chart-style="south"', html)
        self.assertIn('id="combustionOrbDegrees"', html)
        self.assertIn('value="7.5"', html)
        self.assertIn('value="mean" selected', html)
        self.assertIn('id="nodeMode" value="mean"', html)

    def test_each_setting_can_be_changed_without_erasing_the_others(self) -> None:
        client = app_module.app.test_client()
        client.post(
            "/api/user-settings",
            json={"chart_style": "north", "combustion_orb": 6, "node_mode": "true"},
        )
        response = client.post("/api/user-settings", json={"chart_style": "south"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["settings"],
            {"chart_style": "south", "combustion_orb": "6", "node_mode": "true"},
        )

    def test_invalid_setting_is_rejected_without_overwriting_saved_values(self) -> None:
        client = app_module.app.test_client()
        client.post("/api/user-settings", json={"node_mode": "mean"})
        response = client.post("/api/user-settings", json={"node_mode": "invalid"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(app_module.load_user_settings(), {"node_mode": "mean"})

    def test_interface_persists_all_three_choices(self) -> None:
        source = (WORKSPACE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('persistUserSetting("chart_style"', source)
        self.assertIn('persistUserSetting("combustion_orb"', source)
        self.assertIn('persistUserSetting("node_mode"', source)


if __name__ == "__main__":
    unittest.main()
