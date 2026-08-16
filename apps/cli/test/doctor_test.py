from __future__ import annotations

import os
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch


class DoctorTests(unittest.TestCase):
    def test_codx_doctor_checks_wrapper_version_without_a_key(self) -> None:
        from enshittify_cli.main import main

        output = StringIO()
        with (
            patch.dict(os.environ, {"ENSHITTIFY_CODX_COMMAND": "codx"}, clear=False),
            patch(
                "enshittify_cli.commands.doctor.shutil.which", return_value="/bin/codx"
            ),
            patch(
                "enshittify_cli.commands.doctor.subprocess.run",
                return_value=type(
                    "Completed",
                    (),
                    {"stdout": "codex-cli test\n", "stderr": "", "returncode": 0},
                )(),
            ),
            redirect_stdout(output),
        ):
            exit_code = main(["doctor", "--provider", "codx"])

        self.assertEqual(exit_code, 0)
        self.assertIn("codex-cli test", output.getvalue())
        self.assertNotIn("API_KEY", output.getvalue())


if __name__ == "__main__":
    unittest.main()
