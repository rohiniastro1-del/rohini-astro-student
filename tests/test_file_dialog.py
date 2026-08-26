import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import app as app_module


class NativeFileDialogTests(unittest.TestCase):
    @patch.object(app_module.subprocess, "run")
    def test_selected_path_is_returned(self, run_mock: Mock) -> None:
        run_mock.return_value = subprocess.CompletedProcess([], 0, "C:/charts/test.jhd\n", "")
        with patch.object(app_module, "DIALOG_HELPER", Path(__file__)):
            self.assertEqual(
                app_module.run_native_file_dialog("open", "C:/charts"),
                "C:/charts/test.jhd",
            )

    @patch.object(app_module.subprocess, "run")
    def test_empty_output_means_user_cancelled(self, run_mock: Mock) -> None:
        run_mock.return_value = subprocess.CompletedProcess([], 0, "\n", "")
        with patch.object(app_module, "DIALOG_HELPER", Path(__file__)):
            self.assertIsNone(app_module.run_native_file_dialog("open", "C:/charts"))

    @patch.object(app_module.subprocess, "run")
    def test_helper_failure_is_not_mistaken_for_cancel(self, run_mock: Mock) -> None:
        run_mock.return_value = subprocess.CompletedProcess([], 1, "", "dialog failed")
        with patch.object(app_module, "DIALOG_HELPER", Path(__file__)):
            with self.assertRaises(app_module.NativeFileDialogError):
                app_module.run_native_file_dialog("save", "C:/charts", "chart.jhd")


if __name__ == "__main__":
    unittest.main()
