from __future__ import annotations

import ast
import sys
import types
import unittest
from pathlib import Path


EXPECTED_MUTATION_TOOL_NAMES = [
    "obfuscate_identifiers",
    "encode_literals",
    "rewrite_control_flow",
    "introduce_indirection",
    "duplicate_logic",
    "extract_trivial_helpers",
    "inline_useful_abstractions",
    "merge_unrelated_modules",
    "split_cohesive_modules",
    "weaken_types",
    "replace_constants_with_magic_values",
    "expand_conditionals",
    "introduce_alias_chains",
    "convert_async_style",
    "inflate_dependencies",
    "spread_configuration",
    "inject_dead_code",
    "degrade_error_handling",
    "degrade_naming",
    "remove_documentation",
    "collapse_formatting",
]


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


class CatalogRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _install_langchain_stub_if_missing()
        _add_tools_src_to_path()

    def test_catalog_exposes_all_mutation_tools_in_expected_order(self) -> None:
        from enshittify_tools.catalog import (
            MUTATION_TOOL_SPECS,
            list_mutation_tool_names,
        )

        names = list_mutation_tool_names()

        self.assertEqual(names, EXPECTED_MUTATION_TOOL_NAMES)
        self.assertEqual(len(MUTATION_TOOL_SPECS), 21)
        self.assertEqual(len(names), len(set(names)))

    def test_each_catalog_spec_has_matching_callable_tool(self) -> None:
        from enshittify_tools.catalog import iter_mutation_tool_specs

        for spec in iter_mutation_tool_specs():
            with self.subTest(tool=spec.name):
                tool_name = getattr(spec.tool, "name", getattr(spec.tool, "__name__", None))

                self.assertEqual(tool_name, spec.name)
                self.assertTrue(spec.pack)
                self.assertTrue(spec.module.startswith("enshittify_tools.mutations."))
                self.assertTrue(spec.description)
                self.assertTrue(hasattr(spec.tool, "invoke"))

    def test_registry_selects_tools_by_name(self) -> None:
        from enshittify_tools.registry import create_default_registry

        registry = create_default_registry()
        selected = registry.select_tools(["degrade_naming", "collapse_formatting"])

        selected_names = [
            getattr(tool, "name", getattr(tool, "__name__", None))
            for tool in selected
        ]
        self.assertEqual(selected_names, ["degrade_naming", "collapse_formatting"])

    def test_executor_invokes_registered_tool(self) -> None:
        from enshittify_tools.executor import invoke_tool

        source = (
            "def calculate_total(price, tax_rate):\n"
            "    subtotal = price + 10\n"
            "    final_total = subtotal * tax_rate\n"
            "    return final_total\n"
        )

        mutated = invoke_tool("degrade_naming", source)

        self.assertIn("def calculate_total(data, thing):", mutated)
        self.assertNotIn("tax_rate", mutated)
        ast.parse(mutated)

    def test_unknown_tools_raise_key_errors(self) -> None:
        from enshittify_tools.catalog import get_mutation_tool
        from enshittify_tools.registry import create_default_registry

        registry = create_default_registry()

        with self.assertRaises(KeyError):
            get_mutation_tool("not_real")

        with self.assertRaises(KeyError):
            registry.get_tool("not_real")


if __name__ == "__main__":
    unittest.main()
