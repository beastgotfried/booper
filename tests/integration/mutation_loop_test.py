from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from enshittify_providers import wrap_chat_model
from enshittify_sdk import Enshittify
from enshittify_testing import ToolCallingFakeChatModel
from langchain_core.messages import AIMessage


class HybridMutationLoopTests(unittest.TestCase):
    def test_hybrid_mode_spends_remaining_budget_with_deterministic_fallback(
        self,
    ) -> None:
        model = ToolCallingFakeChatModel(
            responses=[AIMessage(content="I am finished without making changes.")]
        )
        provider = wrap_chat_model(model, name="fake", model="scripted")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "main.py").write_text(
                "def f(readable_value):\n    return readable_value\n",
                encoding="utf-8",
            )

            result = Enshittify(
                output_root=root / "runs",
                provider=provider,
            ).run_repository(
                str(source),
                tools=["degrade_naming", "inject_dead_code"],
                budget=2,
            )

            self.assertEqual(result.report["configuration"]["mode"], "hybrid")
            self.assertTrue(result.report["agent"]["fallback_used"])
            self.assertEqual(
                [action["actor"] for action in result.report["agent"]["actions"]],
                ["fallback", "fallback"],
            )
            self.assertEqual(result.report["summary"]["attempted_tool_invocations"], 2)
            self.assertEqual(result.changed_files, ["main.py"])


if __name__ == "__main__":
    unittest.main()
