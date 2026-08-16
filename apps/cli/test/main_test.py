from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


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

    def test_providers_command_lists_groq(self) -> None:
        from enshittify_cli.main import main

        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["providers", "--json"])

        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual([item["name"] for item in payload], ["none", "groq"])

    def test_groq_run_requires_key_environment_variable(self) -> None:
        from enshittify_cli.main import main

        error = StringIO()
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            (source / "main.py").write_text("value = 1\n", encoding="utf-8")
            with (
                patch.dict(os.environ, {"GROQ_API_KEY": ""}),
                redirect_stderr(error),
            ):
                exit_code = main(["run", str(source), "--provider", "groq"])

        self.assertEqual(exit_code, 2)
        self.assertIn("GROQ_API_KEY", error.getvalue())


if __name__ == "__main__":
    unittest.main()
