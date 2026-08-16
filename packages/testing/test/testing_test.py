from __future__ import annotations

import unittest

from enshittify_testing import ToolCallingFakeChatModel, tool_call_message
from langchain.tools import tool
from langchain_core.messages import AIMessage


class TestingHelpersTests(unittest.TestCase):
    def test_fake_model_records_bound_tools(self) -> None:
        @tool
        def fixture_tool(value: str) -> str:
            """Return a fixture value."""
            return value

        model = ToolCallingFakeChatModel(responses=[AIMessage(content="done")])
        self.assertIs(model.bind_tools([fixture_tool]), model)
        self.assertEqual(model.bound_tool_names, ["fixture_tool"])

    def test_tool_call_helper_includes_usage(self) -> None:
        message = tool_call_message(
            "fixture_tool",
            {"value": "x"},
            call_id="call-1",
            input_tokens=5,
            output_tokens=2,
        )
        self.assertEqual(message.tool_calls[0]["name"], "fixture_tool")
        self.assertEqual(message.usage_metadata["total_tokens"], 7)


if __name__ == "__main__":
    unittest.main()
