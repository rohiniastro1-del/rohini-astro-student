import sys
import unittest
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parent.parent
PACKAGES_DIR = WORKSPACE / ".packages"
if PACKAGES_DIR.exists():
    sys.path.insert(0, str(PACKAGES_DIR))

from app import APP_SESSION_ID, app


class AnalysisSelectionStateTests(unittest.TestCase):
    def test_page_identifies_the_current_program_run(self) -> None:
        html = app.test_client().get("/").get_data(as_text=True)
        self.assertIn(f'data-app-session-id="{APP_SESSION_ID}"', html)

    def test_analysis_choice_is_scoped_to_one_program_run(self) -> None:
        source = (WORKSPACE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('const ANALYSIS_STATE_KEY = "rohini.desktopAnalysisState.v1"', source)
        self.assertIn("candidate?.sessionId === appSessionId", source)
        self.assertIn("sessionStorage.setItem(ANALYSIS_STATE_KEY", source)
        self.assertNotIn("localStorage.setItem(ANALYSIS_STATE_KEY", source)

    def test_only_the_view_name_and_dasha_system_are_remembered(self) -> None:
        source = (WORKSPACE / "static" / "app.js").read_text(encoding="utf-8")
        state_start = source.index("sessionStorage.setItem(ANALYSIS_STATE_KEY")
        state_end = source.index("}));", state_start)
        stored_payload = source[state_start:state_end]
        self.assertIn("view: currentAnalysisName", stored_payload)
        self.assertIn("dashaSystem: rememberedDashaSystem", stored_payload)
        self.assertNotIn("rows", stored_payload)
        self.assertNotIn("table", stored_payload)

    def test_dasha_is_recalculated_from_the_current_form_after_reload(self) -> None:
        source = (WORKSPACE / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("dashaState.system = rememberedDashaSystem", source)
        self.assertIn("loadDashaLevel();", source)
        self.assertIn("form: formPayload()", source)


if __name__ == "__main__":
    unittest.main()
