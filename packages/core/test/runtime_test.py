from __future__ import annotations

import sys
import unittest
from pathlib import Path


def _add_package_paths() -> None:
    core_src = Path(__file__).parents[1] / "src"
    tools_src = Path(__file__).parents[2] / "tools" / "src"

    for path in (core_src, tools_src):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _add_package_paths()

    def test_execute_mutations_returns_structured_chain(self) -> None:
        from enshittify_core.runtime.executor import execute_mutations

        result = execute_mutations(
            ["degrade_naming", "collapse_formatting"],
            "def f(value):\n\n    return value  \n",
        )

        self.assertTrue(result.changed)
        self.assertEqual([run.name for run in result.runs], ["degrade_naming", "collapse_formatting"])
        self.assertIn("data", result.code)
        self.assertFalse("\n\n" in result.code)
        import ast

        ast.parse(result.code)
        self.assertGreaterEqual(len(result.to_dict()["runs"]), 2)

    def test_execute_mutations_serializes_to_dict(self) -> None:
        from enshittify_core.runtime.executor import execute_mutations

        result = execute_mutations(["degrade_naming"], "def f(value):\n    return value\n")
        payload = result.to_dict()

        self.assertEqual(payload["code"], result.code)
        self.assertEqual(payload["changed"], result.changed)
        self.assertIn("runs", payload)


if __name__ == "__main__":
    unittest.main()
