import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import prepare_student_data_root


class StudentDataPathTests(unittest.TestCase):
    def test_preferred_documents_folder_is_used_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            preferred = base / "Documents" / "Rohini Astro Student"
            fallback = base / "LocalAppData" / "Rohini Astro Student" / "User Data"

            selected = prepare_student_data_root(preferred, fallback)

            self.assertEqual(selected, preferred)
            self.assertTrue((preferred / "Хороскопи").is_dir())
            self.assertFalse(fallback.exists())

    def test_local_data_fallback_is_used_when_documents_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            preferred = base / "Documents" / "Rohini Astro Student"
            fallback = base / "LocalAppData" / "Rohini Astro Student" / "User Data"
            real_mkdir = Path.mkdir

            def controlled_mkdir(path: Path, *args, **kwargs) -> None:
                if str(path).startswith(str(preferred)):
                    raise FileNotFoundError(3, "Documents is unavailable", str(path))
                real_mkdir(path, *args, **kwargs)

            with patch.object(Path, "mkdir", controlled_mkdir):
                selected = prepare_student_data_root(preferred, fallback)

            self.assertEqual(selected, fallback)
            self.assertTrue((fallback / "Хороскопи").is_dir())


if __name__ == "__main__":
    unittest.main()
