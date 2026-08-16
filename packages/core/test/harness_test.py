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


class HarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _add_package_paths()

    def test_compiled_harness_runs_tool_chain_end_to_end(self) -> None:
        from enshittify_core.harness.create_harness import create_harness

        graph = create_harness()
        result = graph.invoke(
            {
                "code": "def f(value):\n    return value\n",
                "tool_names": ["degrade_naming", "inject_dead_code"],
            }
        )

        self.assertIn("data", result["code"])
        self.assertIn("_unused_legacy_compatibility_path", result["code"])
        self.assertIn("result", result)
        self.assertEqual(
            [run.name for run in result["result"].runs],
            ["degrade_naming", "inject_dead_code"],
        )

    def test_harness_wrapper_invokes_graph(self) -> None:
        from enshittify_core.harness.create_harness import create_harness
        from enshittify_core.harness.harness import MutationHarness

        harness = MutationHarness(graph=create_harness())
        result = harness.invoke(
            code="def f(value):\n    return value\n",
            tool_names=["degrade_naming"],
        )

        self.assertIn("data", result["code"])
        self.assertEqual(
            [run.name for run in result["result"].runs], ["degrade_naming"]
        )


if __name__ == "__main__":
    unittest.main()
