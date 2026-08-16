from __future__ import annotations

import ast
import importlib.util
import sys
import types
import unittest
from dataclasses import dataclass
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


def _load_tool(relative_path: str):
    _install_langchain_stub_if_missing()
    _add_tools_src_to_path()

    root = Path(__file__).parents[1]
    path = root / "src" / "enshittify_tools" / "mutations" / relative_path
    module_name = "test_" + relative_path.replace("/", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _add_tools_src_to_path() -> None:
    src_path = Path(__file__).parents[1] / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


@dataclass(frozen=True)
class ToolCase:
    relative_path: str
    source: str
    expected_fragments: tuple[str, ...]
    expected_edit_kinds: tuple[str, ...]
    forbidden_fragments: tuple[str, ...] = ()
    expected_warning_fragments: tuple[str, ...] = ()
    parse_output: bool = True
    wrapper_name: str | None = None
    wrapper_fragments: tuple[str, ...] = ()

    @property
    def resolved_wrapper_name(self) -> str:
        return self.wrapper_name or Path(self.relative_path).stem


TOOL_CASES: tuple[ToolCase, ...] = (
    ToolCase(
        relative_path="architecture/merge_unrelated_modules.py",
        source="def parse_user(x):\n    return x\n\ndef send_email(y):\n    return y\n",
        expected_fragments=(
            "class MixedResponsibilityJunkDrawer",
            "parse_user = staticmethod(parse_user)",
            "send_email = staticmethod(send_email)",
        ),
        expected_edit_kinds=("merge_unrelated_modules",),
        expected_warning_fragments=("source-level stand-in",),
    ),
    ToolCase(
        relative_path="architecture/split_cohesive_modules.py",
        source="def parse_user(x):\n    return x\n\nclass UserThing:\n    pass\n",
        expected_fragments=(
            "_COHESIVE_MODULE_FRAGMENT_PLAN",
            "'parse_user'",
            "'UserThing'",
        ),
        expected_edit_kinds=("split_cohesive_modules",),
        expected_warning_fragments=("actual file splitting",),
    ),
    ToolCase(
        relative_path="config_sprawl/spread_configuration.py",
        source='CONFIG = {"timeout": 30, "retries": 3, "api_key": "secret"}\n',
        expected_fragments=(
            "CONFIG_TIMEOUT = 30",
            "CONFIG_RETRIES = 3",
            "'timeout': CONFIG_TIMEOUT",
            "'retries': CONFIG_RETRIES",
        ),
        expected_edit_kinds=("spread_configuration",),
        forbidden_fragments=("CONFIG_API_KEY",),
        expected_warning_fragments=("secret-like config key",),
    ),
    ToolCase(
        relative_path="control_flow/convert_async_style.py",
        source="async def load(client):\n    return await client.get()\n",
        expected_fragments=(
            "async def _async_style_delegate",
            "_async_style_result = await _async_style_delegate()",
        ),
        expected_edit_kinds=("convert_async_style",),
    ),
    ToolCase(
        relative_path="control_flow/expand_conditionals.py",
        source="def allowed(active, paid):\n    return active and paid\n",
        expected_fragments=("if active:", "return paid", "return active"),
        expected_edit_kinds=("expand_conditional",),
    ),
    ToolCase(
        relative_path="control_flow/rewrite_control_flow.py",
        source='def label(active):\n    if active:\n        return "yes"\n    return "no"\n',
        expected_fragments=(
            "_control_flow_result = None",
            "_control_flow_result = 'yes'",
            "_control_flow_result = 'no'",
            "return _control_flow_result",
        ),
        expected_edit_kinds=("rewrite_control_flow",),
    ),
    ToolCase(
        relative_path="dead_code/duplicate_logic.py",
        source="def total(a, b):\n    value = a + b\n    return value\n",
        expected_fragments=("_duplicated_value = a + b", "value = a + b"),
        expected_edit_kinds=("duplicate_logic",),
    ),
    ToolCase(
        relative_path="dead_code/inject_dead_code.py",
        source="def f():\n    return 1\n",
        expected_fragments=(
            "def _unused_legacy_compatibility_path",
            "if False:",
            "def f():",
        ),
        expected_edit_kinds=("inject_dead_code",),
    ),
    ToolCase(
        relative_path="dependencies/inflate_dependencies.py",
        source="def f():\n    return 1\n",
        expected_fragments=("import collections as _enshittify_collections",),
        expected_edit_kinds=("inflate_dependencies",),
        expected_warning_fragments=("Package manifests",),
    ),
    ToolCase(
        relative_path="documentation/remove_documentation.py",
        source='"""module docs"""\n# explain\ndef f():\n    """function docs"""\n    return 1\n',
        expected_fragments=("def f():", "return 1"),
        expected_edit_kinds=("remove_docstring", "remove_comment"),
        forbidden_fragments=("module docs", "function docs", "explain"),
        expected_warning_fragments=("AST does not preserve comments",),
    ),
    ToolCase(
        relative_path="error_handling/degrade_error_handling.py",
        source='def f(value):\n    try:\n        int(value)\n    except ValueError as exc:\n        raise RuntimeError("Invalid value") from exc\n',
        expected_fragments=(
            "except Exception as exc:",
            "raise RuntimeError('Something went wrong') from exc",
        ),
        expected_edit_kinds=("broaden_exception_handler", "degrade_error_message"),
        forbidden_fragments=("ValueError", "Invalid value"),
    ),
    ToolCase(
        relative_path="formatting/collapse_formatting.py",
        source="def f():\n\n    return 1  \n",
        expected_fragments=("def f():\n    return 1\n",),
        expected_edit_kinds=("remove_blank_lines", "remove_trailing_whitespace"),
        forbidden_fragments=("\n\n", "  \n"),
    ),
    ToolCase(
        relative_path="indirection/extract_trivial_helpers.py",
        source="def total(price, tax):\n    amount = price + tax\n    return amount\n",
        expected_fragments=(
            "def _trivial_helper(price, tax):",
            "return price + tax",
            "amount = _trivial_helper(price, tax)",
        ),
        expected_edit_kinds=("extract_trivial_helper",),
    ),
    ToolCase(
        relative_path="indirection/inline_useful_abstractions.py",
        source="def normalize(value):\n    return value.strip()\n\ndef f(raw):\n    return normalize(raw)\n",
        expected_fragments=("return raw.strip()",),
        expected_edit_kinds=("inline_useful_abstraction",),
        forbidden_fragments=("return normalize(raw)",),
    ),
    ToolCase(
        relative_path="indirection/introduce_alias_chains.py",
        source="def f(value):\n    return value\n",
        expected_fragments=(
            "_alias_value = value",
            "_alias_value_next = _alias_value",
            "return _alias_value_next",
        ),
        expected_edit_kinds=("introduce_alias_chain",),
    ),
    ToolCase(
        relative_path="indirection/introduce_indirection.py",
        source="def add(a, b):\n    return a + b\n\ndef f(a, b):\n    return add(a, b)\n",
        expected_fragments=(
            "def _delegate_add(*args, **kwargs):",
            "return add(*args, **kwargs)",
            "return _delegate_add(a, b)",
        ),
        expected_edit_kinds=("introduce_indirection",),
    ),
    ToolCase(
        relative_path="naming/degrade_naming.py",
        source="def calculate_total(price, tax_rate):\n    subtotal = price + 10\n    final_total = subtotal * tax_rate\n    return final_total\n",
        expected_fragments=("def calculate_total(data, thing):", "stuff = data + 10", "return value"),
        expected_edit_kinds=("degrade_name",),
        forbidden_fragments=("price", "tax_rate", "subtotal", "final_total"),
    ),
    ToolCase(
        relative_path="obfuscation/encode_literals.py",
        source='def f():\n    message = "hello"\n    limit = 10\n    return message, limit\n',
        expected_fragments=("''.join(['h', 'e', 'l', 'l', 'o'])", "9 + 1"),
        expected_edit_kinds=("encode_literal",),
        forbidden_fragments=('"hello"', "limit = 10"),
    ),
    ToolCase(
        relative_path="obfuscation/obfuscate_identifiers.py",
        source="def calculate_total(price, tax_rate):\n    subtotal = price + 10\n    final_total = subtotal * tax_rate\n    return final_total\n",
        expected_fragments=("def calculate_total(_l, _I):", "_1 = _l + 10", "return _0"),
        expected_edit_kinds=("rename_identifier",),
        forbidden_fragments=("price", "tax_rate", "subtotal", "final_total"),
        wrapper_name="obfuscate_identifiers",
    ),
    ToolCase(
        relative_path="obfuscation/replace_constants_with_magic_values.py",
        source="MAX_RETRIES = 3\n\ndef f():\n    return MAX_RETRIES\n",
        expected_fragments=("def f():", "return 3"),
        expected_edit_kinds=("replace_constant_with_magic_value", "remove_constant_declaration"),
        forbidden_fragments=("MAX_RETRIES",),
    ),
    ToolCase(
        relative_path="types/weaken_types.py",
        source="def f(value: int) -> str:\n    result: str = str(value)\n    return result\n",
        expected_fragments=("from typing import Any", "def f(value: Any) -> Any:", "result: Any"),
        expected_edit_kinds=("weaken_argument_type", "weaken_variable_type", "weaken_return_type"),
        forbidden_fragments=("value: int", "-> str", "result: str"),
    ),
)


class MutationToolTests(unittest.TestCase):
    def test_each_tool_changes_supported_sample_with_expected_metadata(self) -> None:
        for case in TOOL_CASES:
            with self.subTest(tool=case.relative_path):
                module = _load_tool(case.relative_path)
                result = module.mutate_source(case.source)

                self.assertTrue(result.changed)
                self.assertNotEqual(result.code, case.source)
                self.assertTrue(result.summary)
                self.assertIsInstance(result.edits, list)
                self.assertGreaterEqual(len(result.edits), 1)

                edit_kinds = {edit.kind for edit in result.edits}
                for kind in case.expected_edit_kinds:
                    self.assertIn(kind, edit_kinds)

                for fragment in case.expected_fragments:
                    self.assertIn(fragment, result.code)

                for fragment in case.forbidden_fragments:
                    self.assertNotIn(fragment, result.code)

                for warning_fragment in case.expected_warning_fragments:
                    self.assertTrue(
                        any(warning_fragment in warning for warning in result.warnings),
                        result.warnings,
                    )

                if case.parse_output:
                    ast.parse(result.code)

    def test_each_tool_is_deterministic_for_supported_sample(self) -> None:
        for case in TOOL_CASES:
            with self.subTest(tool=case.relative_path):
                module = _load_tool(case.relative_path)
                first = module.mutate_source(case.source)
                second = module.mutate_source(case.source)

                self.assertEqual(first.code, second.code)
                self.assertEqual(first.summary, second.summary)
                self.assertEqual(first.warnings, second.warnings)
                self.assertEqual(
                    [(edit.kind, edit.before, edit.after, edit.line) for edit in first.edits],
                    [(edit.kind, edit.before, edit.after, edit.line) for edit in second.edits],
                )

    def test_each_tool_handles_invalid_syntax_without_crashing(self) -> None:
        invalid_source = "def broken(:\n    pass\n"

        for case in TOOL_CASES:
            with self.subTest(tool=case.relative_path):
                module = _load_tool(case.relative_path)
                result = module.mutate_source(invalid_source)

                self.assertFalse(result.changed)
                self.assertEqual(result.code, invalid_source)
                self.assertEqual(result.edits, [])
                self.assertTrue(any("SyntaxError" in warning for warning in result.warnings))

    def test_each_langchain_wrapper_returns_mutated_code(self) -> None:
        for case in TOOL_CASES:
            with self.subTest(tool=case.relative_path):
                module = _load_tool(case.relative_path)
                wrapper = getattr(module, case.resolved_wrapper_name)

                mutated_code = wrapper.invoke({"code": case.source})

                self.assertIsInstance(mutated_code, str)
                self.assertNotEqual(mutated_code, case.source)
                for fragment in (*case.expected_fragments, *case.wrapper_fragments):
                    self.assertIn(fragment, mutated_code)
                ast.parse(mutated_code)

    def test_every_tool_module_exposes_expected_api(self) -> None:
        _add_tools_src_to_path()
        from enshittify_tools.result import MutationEdit, MutationResult

        for case in TOOL_CASES:
            with self.subTest(tool=case.relative_path):
                module = _load_tool(case.relative_path)

                self.assertTrue(callable(module.mutate_source))
                self.assertIs(module.MutationEdit, MutationEdit)
                self.assertIs(module.MutationResult, MutationResult)
                self.assertTrue(hasattr(module, case.resolved_wrapper_name))

    def test_results_are_serializable_to_dicts(self) -> None:
        for case in TOOL_CASES:
            with self.subTest(tool=case.relative_path):
                module = _load_tool(case.relative_path)
                result = module.mutate_source(case.source)

                serialized = result.to_dict()

                self.assertEqual(serialized["code"], result.code)
                self.assertEqual(serialized["changed"], result.changed)
                self.assertEqual(serialized["summary"], result.summary)
                self.assertEqual(serialized["warnings"], result.warnings)
                self.assertIsInstance(serialized["edits"], list)
                self.assertGreaterEqual(len(serialized["edits"]), 1)
                self.assertIn("kind", serialized["edits"][0])


if __name__ == "__main__":
    unittest.main()
