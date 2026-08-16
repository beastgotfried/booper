from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path

from enshittify_providers import wrap_chat_model
from enshittify_sdk import Enshittify
from enshittify_testing import ToolCallingFakeChatModel, tool_call_message
from langchain_core.messages import AIMessage


class ProviderHarnessIntegrationTests(unittest.TestCase):
    def test_agent_inspects_rewrites_mutates_and_reviews_an_isolated_file(self) -> None:
        responses = [
            tool_call_message(
                "inspect_workspace",
                {},
                call_id="call-1",
                input_tokens=10,
                output_tokens=2,
            ),
            tool_call_message("read_source", {"path": "main.py"}, call_id="call-2"),
            tool_call_message(
                "rewrite_source",
                {
                    "path": "main.py",
                    "code": (
                        "def calculate_total(value):\n"
                        "    temporary = value\n"
                        "    thing = temporary\n"
                        "    return thing\n"
                    ),
                    "rationale": "Add a pointless alias chain.",
                },
                call_id="call-3",
            ),
            tool_call_message(
                "apply_mutation",
                {
                    "path": "main.py",
                    "mutation": "degrade_naming",
                    "rationale": "Erase the remaining useful names.",
                },
                call_id="call-4",
            ),
            tool_call_message("review_diff", {}, call_id="call-5"),
            AIMessage(
                content="Added pointless indirection and degraded identifiers.",
                usage_metadata={
                    "input_tokens": 3,
                    "output_tokens": 2,
                    "total_tokens": 5,
                },
            ),
        ]
        model = ToolCallingFakeChatModel(responses=responses)
        provider = wrap_chat_model(model, name="fake", model="scripted")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            original = "def calculate_total(value):\n    return value\n"
            (source / "main.py").write_text(original, encoding="utf-8")

            result = Enshittify(
                output_root=root / "runs",
                provider=provider,
                mode="agent",
            ).run_repository(
                str(source),
                tools=["degrade_naming"],
                budget=2,
            )

            mutated = (result.workspace_dir / "main.py").read_text(encoding="utf-8")
            ast.parse(mutated)
            self.assertEqual((source / "main.py").read_text(), original)
            self.assertEqual(result.changed_files, ["main.py"])
            self.assertEqual(result.report["agent"]["model_calls"], 6)
            self.assertEqual(result.report["agent"]["usage"]["total_tokens"], 17)
            self.assertEqual(
                [action["tool"] for action in result.report["agent"]["actions"]],
                ["llm_rewrite", "degrade_naming"],
            )
            self.assertEqual(
                sorted(model.bound_tool_names),
                [
                    "apply_mutation",
                    "inspect_workspace",
                    "read_source",
                    "review_diff",
                    "rewrite_source",
                ],
            )


if __name__ == "__main__":
    unittest.main()
