from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from enshittify_backends import prepare_workspace


class FilesystemWorkspaceTests(unittest.TestCase):
    def test_local_copy_is_isolated_and_does_not_recurse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "main.py").write_text("value = 1\n", encoding="utf-8")
            (source / ".git").mkdir()
            output_root = source / ".enshittify" / "runs"

            workspace = prepare_workspace(str(source), output_root=output_root)

            self.assertEqual(
                (workspace.working_dir / "main.py").read_text(), "value = 1\n"
            )
            self.assertFalse((workspace.working_dir / ".git").exists())
            self.assertFalse((workspace.original_dir / ".enshittify").exists())
            self.assertEqual((source / "main.py").read_text(), "value = 1\n")

    def test_output_root_cannot_equal_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            with self.assertRaisesRegex(RuntimeError, "cannot be the source"):
                prepare_workspace(str(source), output_root=source)


if __name__ == "__main__":
    unittest.main()
