import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


WORKSPACE = Path(__file__).resolve().parent.parent
PACKAGES_DIR = WORKSPACE / ".packages"
if PACKAGES_DIR.exists():
    sys.path.insert(0, str(PACKAGES_DIR))

from vedic_app import astro


class EphemerisPathTests(unittest.TestCase):
    def test_prepare_ascii_ephemeris_mirror_copies_required_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source_dir = base / "епхе"
            source_dir.mkdir()
            (source_dir / "sepl_18.se1").write_text("planet", encoding="utf-8")
            (source_dir / "semo_18.se1").write_text("moon", encoding="utf-8")

            cache_root = base / "ascii-cache"
            with patch.object(astro, "_ephemeris_cache_candidates", return_value=[cache_root]):
                mirror = astro._prepare_ascii_ephemeris_mirror(source_dir)

            self.assertIsNotNone(mirror)
            assert mirror is not None
            self.assertTrue(astro._is_ascii_safe_path(mirror))
            self.assertEqual((mirror / "sepl_18.se1").read_text(encoding="utf-8"), "planet")
            self.assertEqual((mirror / "semo_18.se1").read_text(encoding="utf-8"), "moon")

    def test_configure_ephemeris_keeps_original_directory_when_backend_is_valid(self) -> None:
        source_dir = Path(r"C:\Temp\rohini-ephe")

        with (
            patch.object(astro, "_discover_ephemeris_directory", return_value=source_dir),
            patch.object(astro, "_validate_de441_files") as files_mock,
            patch.object(astro, "_set_and_validate_ephemeris_path", return_value=True) as validate_mock,
            patch.object(astro, "_prepare_ascii_ephemeris_mirror") as mirror_mock,
        ):
            configured = astro._configure_ephemeris()

        self.assertEqual(configured, str(source_dir))
        files_mock.assert_called_once_with(source_dir)
        validate_mock.assert_called_once_with(source_dir)
        mirror_mock.assert_not_called()

    def test_configure_ephemeris_uses_ascii_mirror_when_unicode_path_falls_back(self) -> None:
        source_dir = Path(r"C:\Unicode\епхе")
        mirror_dir = Path(r"C:\Temp\rohini_swe_ephe\mirror")

        with (
            patch.object(astro, "_discover_ephemeris_directory", return_value=source_dir),
            patch.object(astro, "_validate_de441_files") as files_mock,
            patch.object(astro, "_set_and_validate_ephemeris_path", side_effect=[False, True]) as validate_mock,
            patch.object(astro, "_prepare_ascii_ephemeris_mirror", return_value=mirror_dir) as mirror_mock,
        ):
            configured = astro._configure_ephemeris()

        self.assertEqual(configured, str(mirror_dir))
        files_mock.assert_called_once_with(source_dir)
        self.assertEqual(validate_mock.call_count, 2)
        mirror_mock.assert_called_once_with(source_dir)

    def test_requested_swieph_backend_warning_reports_moseph_fallback(self) -> None:
        warning = astro._requested_swieph_backend_warning("Moon", astro.swe.FLG_SWIEPH, astro.swe.FLG_MOSEPH)

        self.assertIsNotNone(warning)
        assert warning is not None
        self.assertIn("Луна", warning)
        self.assertIn("FLG_SWIEPH", warning)
        self.assertIn("FLG_MOSEPH", warning)

    def test_unicode_path_ascii_mirror_keeps_real_swieph_backend(self) -> None:
        workspace_ephe = (WORKSPACE / "ephe").resolve()
        self.assertTrue(workspace_ephe.is_dir())

        with tempfile.TemporaryDirectory() as temp_dir:
            unicode_dir = Path(temp_dir) / "епхе"
            unicode_dir.mkdir()
            for name in ("seas_18.se1", "semo_18.se1", "sepl_18.se1"):
                shutil.copy2(workspace_ephe / name, unicode_dir / name)

            self.assertFalse(astro._is_ascii_safe_path(unicode_dir))

            mirror = astro._prepare_ascii_ephemeris_mirror(unicode_dir)
            self.assertIsNotNone(mirror)
            assert mirror is not None
            self.assertTrue(astro._is_ascii_safe_path(mirror))

            with astro.SWE_LOCK:
                original_directory = astro.EPHEMERIS_DIRECTORY
                astro.swe.set_ephe_path(str(unicode_dir))
                _, source_retflags = astro.swe.calc_ut(
                    astro.swe.julday(2000, 1, 1, 0.0),
                    astro.swe.SUN,
                    astro.swe.FLG_SWIEPH,
                )

                validated = astro._set_and_validate_ephemeris_path(mirror)
                _, mirror_retflags = astro.swe.calc_ut(
                    astro.swe.julday(2000, 1, 1, 0.0),
                    astro.swe.SUN,
                    astro.swe.FLG_SWIEPH,
                )
                if original_directory:
                    astro.swe.set_ephe_path(original_directory)

            self.assertTrue(source_retflags & astro.swe.FLG_MOSEPH)
            self.assertTrue(validated)
            self.assertTrue(mirror_retflags & astro.swe.FLG_SWIEPH)
            self.assertFalse(mirror_retflags & astro.swe.FLG_MOSEPH)


    def test_flask_request_in_worker_thread_keeps_swieph(self) -> None:
        import threading

        from vedic_app.astro import calculate_reading, default_form_values

        holder: dict[str, str] = {}

        def run() -> None:
            result = calculate_reading(default_form_values(), build_mode="natal")
            holder["label"] = result["ephemeris_source"]["label"]

        thread = threading.Thread(target=run)
        thread.start()
        thread.join()

        self.assertEqual(holder.get("label", ""), "Swiss Ephemeris")


if __name__ == "__main__":
    unittest.main()
