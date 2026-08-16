"""Catalog of harness-callable tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from enshittify_tools.mutations.architecture.merge_unrelated_modules import (
    merge_unrelated_modules,
)
from enshittify_tools.mutations.architecture.split_cohesive_modules import (
    split_cohesive_modules,
)
from enshittify_tools.mutations.config_sprawl.spread_configuration import (
    spread_configuration,
)
from enshittify_tools.mutations.control_flow.convert_async_style import (
    convert_async_style,
)
from enshittify_tools.mutations.control_flow.expand_conditionals import (
    expand_conditionals,
)
from enshittify_tools.mutations.control_flow.rewrite_control_flow import (
    rewrite_control_flow,
)
from enshittify_tools.mutations.dead_code.duplicate_logic import duplicate_logic
from enshittify_tools.mutations.dead_code.inject_dead_code import inject_dead_code
from enshittify_tools.mutations.dependencies.inflate_dependencies import (
    inflate_dependencies,
)
from enshittify_tools.mutations.documentation.remove_documentation import (
    remove_documentation,
)
from enshittify_tools.mutations.error_handling.degrade_error_handling import (
    degrade_error_handling,
)
from enshittify_tools.mutations.formatting.collapse_formatting import (
    collapse_formatting,
)
from enshittify_tools.mutations.indirection.extract_trivial_helpers import (
    extract_trivial_helpers,
)
from enshittify_tools.mutations.indirection.inline_useful_abstractions import (
    inline_useful_abstractions,
)
from enshittify_tools.mutations.indirection.introduce_alias_chains import (
    introduce_alias_chains,
)
from enshittify_tools.mutations.indirection.introduce_indirection import (
    introduce_indirection,
)
from enshittify_tools.mutations.naming.degrade_naming import degrade_naming
from enshittify_tools.mutations.obfuscation.encode_literals import encode_literals
from enshittify_tools.mutations.obfuscation.obfuscate_identifiers import (
    obfuscate_identifiers,
)
from enshittify_tools.mutations.obfuscation.replace_constants_with_magic_values import (
    replace_constants_with_magic_values,
)
from enshittify_tools.mutations.types.weaken_types import weaken_types


@dataclass(frozen=True)
class ToolSpec:
    name: str
    pack: str
    module: str
    description: str
    tool: Any


MUTATION_TOOL_SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="obfuscate_identifiers",
        pack="obfuscation",
        module="enshittify_tools.mutations.obfuscation.obfuscate_identifiers",
        description="Rename Python variables and arguments to unreadable identifiers.",
        tool=obfuscate_identifiers,
    ),
    ToolSpec(
        name="encode_literals",
        pack="obfuscation",
        module="enshittify_tools.mutations.obfuscation.encode_literals",
        description="Replace obvious Python literals with equivalent encoded expressions.",
        tool=encode_literals,
    ),
    ToolSpec(
        name="rewrite_control_flow",
        pack="control_flow",
        module="enshittify_tools.mutations.control_flow.rewrite_control_flow",
        description="Rewrite simple Python if-return control flow into a less direct shape.",
        tool=rewrite_control_flow,
    ),
    ToolSpec(
        name="introduce_indirection",
        pack="indirection",
        module="enshittify_tools.mutations.indirection.introduce_indirection",
        description="Wrap one direct Python function call in an unnecessary delegate.",
        tool=introduce_indirection,
    ),
    ToolSpec(
        name="duplicate_logic",
        pack="dead_code",
        module="enshittify_tools.mutations.dead_code.duplicate_logic",
        description="Duplicate simple Python logic into an unnecessary assignment.",
        tool=duplicate_logic,
    ),
    ToolSpec(
        name="extract_trivial_helpers",
        pack="indirection",
        module="enshittify_tools.mutations.indirection.extract_trivial_helpers",
        description="Extract a simple Python expression into an unnecessary helper.",
        tool=extract_trivial_helpers,
    ),
    ToolSpec(
        name="inline_useful_abstractions",
        pack="indirection",
        module="enshittify_tools.mutations.indirection.inline_useful_abstractions",
        description="Inline one simple Python helper function call into its call site.",
        tool=inline_useful_abstractions,
    ),
    ToolSpec(
        name="merge_unrelated_modules",
        pack="architecture",
        module="enshittify_tools.mutations.architecture.merge_unrelated_modules",
        description="Add a mixed-responsibility aggregation class for unrelated Python functions.",
        tool=merge_unrelated_modules,
    ),
    ToolSpec(
        name="split_cohesive_modules",
        pack="architecture",
        module="enshittify_tools.mutations.architecture.split_cohesive_modules",
        description="Add a Python source-level fragmentation plan for cohesive symbols.",
        tool=split_cohesive_modules,
    ),
    ToolSpec(
        name="weaken_types",
        pack="types",
        module="enshittify_tools.mutations.types.weaken_types",
        description="Replace Python type annotations with weaker `Any` annotations.",
        tool=weaken_types,
    ),
    ToolSpec(
        name="replace_constants_with_magic_values",
        pack="obfuscation",
        module="enshittify_tools.mutations.obfuscation.replace_constants_with_magic_values",
        description="Replace simple named Python constants with raw literal values.",
        tool=replace_constants_with_magic_values,
    ),
    ToolSpec(
        name="expand_conditionals",
        pack="control_flow",
        module="enshittify_tools.mutations.control_flow.expand_conditionals",
        description="Expand simple Python boolean returns into explicit branches.",
        tool=expand_conditionals,
    ),
    ToolSpec(
        name="introduce_alias_chains",
        pack="indirection",
        module="enshittify_tools.mutations.indirection.introduce_alias_chains",
        description="Introduce a redundant Python alias chain before a simple name use.",
        tool=introduce_alias_chains,
    ),
    ToolSpec(
        name="convert_async_style",
        pack="control_flow",
        module="enshittify_tools.mutations.control_flow.convert_async_style",
        description="Convert direct Python async style into a less direct nested coroutine style.",
        tool=convert_async_style,
    ),
    ToolSpec(
        name="inflate_dependencies",
        pack="dependencies",
        module="enshittify_tools.mutations.dependencies.inflate_dependencies",
        description="Add a redundant Python import without changing package manifests.",
        tool=inflate_dependencies,
    ),
    ToolSpec(
        name="spread_configuration",
        pack="config_sprawl",
        module="enshittify_tools.mutations.config_sprawl.spread_configuration",
        description="Spread safe Python config dictionary values into separate constants.",
        tool=spread_configuration,
    ),
    ToolSpec(
        name="inject_dead_code",
        pack="dead_code",
        module="enshittify_tools.mutations.dead_code.inject_dead_code",
        description="Insert bounded inert Python dead code.",
        tool=inject_dead_code,
    ),
    ToolSpec(
        name="degrade_error_handling",
        pack="error_handling",
        module="enshittify_tools.mutations.error_handling.degrade_error_handling",
        description="Broaden Python exception handling and weaken error messages.",
        tool=degrade_error_handling,
    ),
    ToolSpec(
        name="degrade_naming",
        pack="naming",
        module="enshittify_tools.mutations.naming.degrade_naming",
        description="Replace clear Python variable and argument names with vague names.",
        tool=degrade_naming,
    ),
    ToolSpec(
        name="remove_documentation",
        pack="documentation",
        module="enshittify_tools.mutations.documentation.remove_documentation",
        description="Remove Python comments and docstrings from source code.",
        tool=remove_documentation,
    ),
    ToolSpec(
        name="collapse_formatting",
        pack="formatting",
        module="enshittify_tools.mutations.formatting.collapse_formatting",
        description="Collapse safe Python formatting whitespace.",
        tool=collapse_formatting,
    ),
)


def iter_mutation_tool_specs() -> Iterable[ToolSpec]:
    return iter(MUTATION_TOOL_SPECS)


def list_mutation_tool_names() -> list[str]:
    return [spec.name for spec in MUTATION_TOOL_SPECS]


def get_mutation_tool(name: str) -> Any:
    for spec in MUTATION_TOOL_SPECS:
        if spec.name == name:
            return spec.tool
    raise KeyError(f"Unknown mutation tool: {name}")


def get_mutation_tools(names: Iterable[str] | None = None) -> list[Any]:
    if names is None:
        return [spec.tool for spec in MUTATION_TOOL_SPECS]
    return [get_mutation_tool(name) for name in names]
