from __future__ import annotations

import ast
import sys
import types
import unittest
from pathlib import Path


def _install_langchain_stub_if_missing() -> None:
    try:
        import langchain.tools  # noqa: F401
    except ModuleNotFoundError:
        langchain = types.ModuleType("langchain")
        langchain_tools = types.ModuleType("langchain.tools")

        def tool(function):
            function.invoke = lambda payload: function(**payload)
            return function

        langchain_tools.tool = tool
        sys.modules["langchain"] = langchain
        sys.modules["langchain.tools"] = langchain_tools


def _add_tools_src_to_path() -> None:
    src_path = Path(__file__).parents[1] / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


class ExecutorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _install_langchain_stub_if_missing()
        _add_tools_src_to_path()

    def test_invoke_tool_uses_langchain_wrapper(self) -> None:
        from enshittify_tools.executor import invoke_tool

        source = "def f(value):\n    return value\n"
        mutated = invoke_tool("degrade_naming", source)

        self.assertIn("def f(data):", mutated)
        ast.parse(mutated)

    def test_execute_tool_returns_structured_result(self) -> None:
        from enshittify_tools.executor import execute_tool

        source = "def f(value):\n    return value\n"
        result = execute_tool("degrade_naming", source)

        self.assertTrue(result.changed)
        self.assertIn("data", result.code)
        self.assertTrue(result.summary)
        self.assertGreaterEqual(len(result.edits), 1)
        self.assertTrue(hasattr(result, "to_dict"))

    def test_execute_tool_chain_returns_structured_chain(self) -> None:
        from enshittify_tools.executor import execute_tool_chain

        source = "def f(value):\n    return value\n"
        chain = execute_tool_chain(["degrade_naming", "inject_dead_code"], source)

        self.assertTrue(chain.changed)
        self.assertIn("_unused_legacy_compatibility_path", chain.code)
        self.assertEqual([run.name for run in chain.runs], ["degrade_naming", "inject_dead_code"])
        self.assertGreaterEqual(len(chain.warnings), 0)
        self.assertTrue(hasattr(chain, "to_dict"))
        ast.parse(chain.code)

    def test_execute_tool_chain_to_dict_is_serializable(self) -> None:
        from enshittify_tools.executor import execute_tool_chain

        source = "def f(value):\n    return value\n"
        chain = execute_tool_chain(["degrade_naming"], source)

        payload = chain.to_dict()

        self.assertEqual(payload["code"], chain.code)
        self.assertEqual(payload["changed"], chain.changed)
        self.assertEqual(payload["warnings"], chain.warnings)
        self.assertEqual(payload["runs"][0]["name"], "degrade_naming")
        self.assertIn("result", payload["runs"][0])

    def test_unknown_tool_raises_key_error(self) -> None:
        from enshittify_tools.executor import execute_tool

        with self.assertRaises(KeyError):
            execute_tool("not_real", "def f():\n    return 1\n")


if __name__ == "__main__":
    unittest.main()
