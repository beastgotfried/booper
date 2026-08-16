from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


class CliTests(unittest.TestCase):
    def test_run_json_reports_persistent_artifacts(self) -> None:
        from enshittify_cli.main import main

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "main.py").write_text(
                "def calculate_total(value):\n    return value\n",
                encoding="utf-8",
            )
            output = StringIO()

            with redirect_stdout(output):
                exit_code = main(
                    [
                        "run",
                        str(source),
                        "--output-dir",
                        str(root / "runs"),
                        "--tool",
                        "degrade_naming",
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "completed")
            self.assertEqual(payload["summary"]["changed_files"], ["main.py"])
            self.assertTrue(Path(payload["artifacts"]["patch"]).is_file())
            self.assertTrue(Path(payload["artifacts"]["report"]).is_file())


if __name__ == "__main__":
    unittest.main()
