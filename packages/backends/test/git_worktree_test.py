from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from enshittify_backends import prepare_workspace


def _git(arguments: list[str], cwd: Path | None = None) -> None:
    subprocess.run(
        ["git", *arguments], cwd=cwd, check=True, capture_output=True, text=True
    )


class GitWorkspaceTests(unittest.TestCase):
    def test_file_git_url_is_cloned_with_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            remote = root / "remote.git"
            source.mkdir()
            _git(["init", "-q"], source)
            _git(["config", "user.email", "fixture@example.com"], source)
            _git(["config", "user.name", "Fixture"], source)
            (source / "main.py").write_text("value = 1\n", encoding="utf-8")
            _git(["add", "main.py"], source)
            _git(["commit", "-qm", "fixture"], source)
            _git(["clone", "-q", "--bare", str(source), str(remote)])

            workspace = prepare_workspace(remote.as_uri(), output_root=root / "runs")

            self.assertEqual(workspace.source_kind, "git")
            self.assertEqual(len(workspace.revision or ""), 40)
            self.assertEqual(
                (workspace.working_dir / "main.py").read_text(), "value = 1\n"
            )
            self.assertFalse((workspace.working_dir / ".git").exists())


if __name__ == "__main__":
    unittest.main()
