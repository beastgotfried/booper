from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from enshittify_languages import inspect_repository, iter_python_files


class LanguageDetectionTests(unittest.TestCase):
    def test_inspection_and_test_exclusion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "app.py").write_text("value = 1\n", encoding="utf-8")
            (root / "tests" / "test_app.py").write_text(
                "assert True\n", encoding="utf-8"
            )
            (root / "web.ts").write_text("export {};\n", encoding="utf-8")

            inspection = inspect_repository(root)
            self.assertEqual(inspection.languages, {"Python": 2, "TypeScript": 1})
            self.assertEqual(
                [path.name for path in iter_python_files(root)], ["app.py"]
            )
            self.assertEqual(len(iter_python_files(root, include_tests=True)), 2)


if __name__ == "__main__":
    unittest.main()
