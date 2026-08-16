# Mutation Tool Engineering Guide

This guide defines how to build the mutation tools for `enshittify.dev`.

The product goal is not low-quality engineering. The product goal is a high-quality harness that can intentionally produce controlled code degradation. Internally, the system should be deterministic, typed, testable, observable, reversible, and easy to extend.

The tools may make target code harder to read. The tools themselves should be excellent.

## Framework Responsibilities

Use **LangChain** for model-facing tool definitions.

LangChain tools are callable functions with defined inputs and outputs. A model chooses whether to call a tool based on the tool name, argument schema, and docstring. The docstring is only a description for the model. It does not implement the transformation.

Use **LangGraph** for orchestration.

LangGraph should manage stateful workflows: selecting files, selecting tools, applying mutations, evaluating results, retrying, branching, checkpointing, and asking for human approval when needed. A graph node reads the current state and returns a partial state update.

Use pure Python for mutation logic.

Every mutation should have a normal Python implementation that can be tested without an LLM, without LangChain, and without LangGraph. The agent framework wraps and orchestrates the logic; it should not hide it.

## Source References

- LangChain tools: https://docs.langchain.com/oss/python/langchain/tools
- LangChain overview: https://docs.langchain.com/oss/python/langchain/overview
- LangGraph graph API: https://docs.langchain.com/oss/python/langgraph/graph-api
- LangGraph `StateGraph` reference: https://reference.langchain.com/python/langgraph/graph/state/StateGraph
- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview

## Tool Directory

Callable mutation tools live under:

```text
packages/tools/src/enshittify_tools/mutations/
```

Each pack groups related tools:

```text
architecture/
config_sprawl/
control_flow/
dead_code/
dependencies/
documentation/
error_handling/
formatting/
indirection/
naming/
obfuscation/
types/
```

Example:

```text
packages/tools/src/enshittify_tools/mutations/obfuscation/obfuscate_identifiers.py
```

## Product Quality Bar

Every tool should meet these standards before it is considered complete.

### Deterministic

Given the same input and options, the tool should produce the same output. If randomness is useful later, inject a seed through the input schema and record it in the result.

### Scoped

The tool must only operate on the file or workspace paths passed to it. It should never scan unrelated directories, home folders, dependency caches, `.git`, virtual environments, secrets, or generated artifacts by default.

### Parser-Aware

Use language parsers whenever possible. For Python, prefer `ast`, `tokenize`, and structured import handling. Avoid regex for semantic rewrites such as renaming, control flow, type changes, and import updates.

### Reversible

Return enough metadata to show what changed. The harness should eventually be able to produce a diff, checkpoint, or rollback.

### Observable

Return summaries, counts, warnings, skipped items, and parse errors. The graph should not need to infer what happened from raw source strings.

### Idempotent or Bounded

A tool should either be idempotent or explicitly bounded. Running it twice should not create infinite wrappers, infinite aliases, unbounded dead code, or unbounded dependency growth.

### Tested

Each tool needs unit tests for the pure function, import tests for the module, LangChain invocation tests, and later LangGraph node tests.

## Recommended Module Shape

Start each tool with a pure implementation and a thin LangChain wrapper.

```python
"""Tool for applying one specific mutation."""

from __future__ import annotations

from dataclasses import dataclass
from langchain.tools import tool


@dataclass(frozen=True)
class MutationEdit:
    kind: str
    before: str
    after: str
    line: int | None = None


@dataclass(frozen=True)
class MutationResult:
    code: str
    changed: bool
    summary: str
    edits: list[MutationEdit]
    warnings: list[str]


def mutate_source(code: str) -> MutationResult:
    """Pure implementation. This function should be directly unit tested."""
    return MutationResult(
        code=code,
        changed=False,
        summary="No changes applied.",
        edits=[],
        warnings=[],
    )


@tool
def tool_name(code: str) -> str:
    """Model-facing description of when this tool should be used."""
    result = mutate_source(code)
    return result.code
```

The wrapper can return only `str` at first because that is easiest to learn. The pure function should move toward returning structured metadata.

## Preferred Final Contract

A mature mutation tool should accept structured input:

```python
class MutationToolInput(BaseModel):
    code: str
    language: str = "python"
    file_path: str | None = None
    intensity: Literal["low", "medium", "high"] = "medium"
    preserve_behavior: bool = True
    seed: int = 0
```

And return structured output:

```python
class MutationToolOutput(BaseModel):
    code: str
    changed: bool
    tool: str
    language: str
    summary: str
    edits: list[dict]
    warnings: list[str]
    metrics: dict[str, int | float | str | bool]
```

Keep this as the target shape even if the first working version returns a string.

## Build Strategy

Implement each tool in three milestones.

### Milestone 1: Single-File Pure Function

The tool accepts a code string and returns a changed code string or structured result. It does not know about the file system, the harness, or the model.

### Milestone 2: Robust Tool Module

The module validates input, handles parse errors, reports metadata, has unit tests, and exposes a LangChain `@tool` wrapper.

### Milestone 3: Harness Integration

The tool is registered in the tool catalog, called by a LangGraph node, traced, scored by evaluators, and protected by rollback/checkpoint behavior.

## Build Order

Build in this order so each tool teaches one new concept without forcing the whole system at once.

1. `obfuscate_identifiers`
2. `degrade_naming`
3. `remove_documentation`
4. `collapse_formatting`
5. `inject_dead_code`
6. `encode_literals`
7. `replace_constants_with_magic_values`
8. `extract_trivial_helpers`
9. `introduce_indirection`
10. `duplicate_logic`
11. `expand_conditionals`
12. `rewrite_control_flow`
13. `weaken_types`
14. `introduce_alias_chains`
15. `spread_configuration`
16. `inflate_dependencies`
17. `split_cohesive_modules`
18. `merge_unrelated_modules`
19. `inline_useful_abstractions`
20. `convert_async_style`
21. LangGraph orchestration and evaluator loops

## Common Testing Checklist

Each tool should have tests for:

- Module import.
- Empty input.
- Invalid syntax input.
- A minimal successful mutation.
- A case that should be skipped.
- Deterministic output.
- Output parses when `preserve_behavior=True`.
- Metadata explains what changed.
- LangChain wrapper invocation.
- Later: LangGraph node execution.

For Python syntax preservation:

```python
import ast

ast.parse(mutated_code)
```

For behavior preservation in selected tools, execute tiny before/after fixtures in a sandboxed test harness and compare results.

## Tool Specifications

### `obfuscate_identifiers`

Path:

```text
packages/tools/src/enshittify_tools/mutations/obfuscation/obfuscate_identifiers.py
```

Purpose:

Rename identifiers so the target code becomes harder to read while still compiling. This is an obfuscation tool, not a naming-style tool.

High-quality behavior:

- Parse Python source with `ast`.
- Collect rename candidates from local variables, function arguments, exception aliases, and comprehension variables.
- Skip builtins, keywords, imports, dunder names, `self`, `cls`, public API symbols, and attributes.
- Generate deterministic replacements.
- Rewrite all references consistently inside the valid scope.
- Return a rename map in metadata.

Implementation notes:

- Start with function-local variables and arguments.
- Treat scoping carefully. Nested functions, comprehensions, globals, and nonlocals can be tricky.
- Do not rename `obj.attr` until attribute-level analysis exists.

Learning focus:

AST traversal, symbol collection, scope handling, and LangChain wrapper separation.

Quality tests:

- Renames a simple local variable.
- Renames an argument and all its uses.
- Does not rename `print`, imports, `self`, or attributes.
- Produces the same rename map for the same input.

### `encode_literals`

Path:

```text
packages/tools/src/enshittify_tools/mutations/obfuscation/encode_literals.py
```

Purpose:

Replace obvious literal values with equivalent but less readable expressions.

High-quality behavior:

- Parse Python with `ast`.
- Replace selected `ast.Constant` values with generated expressions.
- Preserve runtime values.
- Avoid docstrings, import paths, decorators, type annotations, and framework declarations by default.
- Track how many strings, numbers, booleans, and bytes were encoded.

Implementation notes:

- Strings can become `"".join([...])`.
- Integers can become arithmetic expressions like `(7 + 3)`.
- Booleans can become comparisons like `(1 == 1)`, but avoid overdoing this early.
- Use `ast.parse(expression, mode="eval").body` to create replacement expressions.

Learning focus:

AST node replacement and value-preserving transformations.

Quality tests:

- Encoded literals evaluate to the same values.
- Docstrings are left alone unless explicitly enabled.
- The output parses.
- The transformation is deterministic.

### `rewrite_control_flow`

Path:

```text
packages/tools/src/enshittify_tools/mutations/control_flow/rewrite_control_flow.py
```

Purpose:

Rewrite simple control flow into more verbose or less direct shapes.

High-quality behavior:

- Work only on small, well-understood patterns at first.
- Preserve semantics when `preserve_behavior=True`.
- Avoid rewriting loops, exceptions, `yield`, and `await` until explicitly supported.
- Add metadata describing which pattern was rewritten.

Implementation notes:

- Start by transforming simple `if/return` pairs into temporary result variables.
- Keep source locations where possible with `ast.copy_location`.
- Run `ast.fix_missing_locations`.

Learning focus:

Statement-level AST rewrites and semantic preservation.

Quality tests:

- Rewrites a simple early return.
- Skips complex branches.
- Before and after functions return the same values for sample inputs.

### `introduce_indirection`

Path:

```text
packages/tools/src/enshittify_tools/mutations/indirection/introduce_indirection.py
```

Purpose:

Add wrapper functions, delegates, dispatch maps, or adapter layers that make direct logic harder to trace.

High-quality behavior:

- Add one bounded layer of indirection per run.
- Use deterministic helper names.
- Avoid wrapping calls with unknown side effects in a way that changes evaluation order.
- Record the inserted helper and modified call sites.

Implementation notes:

- Start with simple function calls in assignments.
- Generate a helper near the top of the module or near the target function.
- Later, support classes and dispatch dictionaries.

Learning focus:

Generating new AST declarations and updating call sites.

Quality tests:

- Inserts one helper.
- Updates exactly the selected call.
- Does not repeat the same wrapper on a second run unless configured.

### `duplicate_logic`

Path:

```text
packages/tools/src/enshittify_tools/mutations/dead_code/duplicate_logic.py
```

Purpose:

Increase maintenance cost by duplicating logic that should be shared.

High-quality behavior:

- Duplicate only simple, safe patterns.
- Keep the duplicated code syntactically valid.
- Report where the duplicate was inserted.
- Avoid unbounded duplication across repeated runs.

Implementation notes:

- Start by duplicating a tiny assignment or expression into an unnecessary intermediate variable.
- Later, inline small pure helpers at multiple call sites.

Learning focus:

Recognizing repeated logic and controlling transformation scope.

Quality tests:

- Creates a duplicate expression.
- Does not duplicate already duplicated generated code.
- Output parses.

### `extract_trivial_helpers`

Path:

```text
packages/tools/src/enshittify_tools/mutations/indirection/extract_trivial_helpers.py
```

Purpose:

Extract simple expressions into unnecessary helper functions.

High-quality behavior:

- Only extract expressions whose dependencies are easy to pass as arguments.
- Generate deterministic helper names.
- Avoid closures, comprehensions, lambdas, and expressions with side effects at first.
- Record the helper signature and replaced expression.

Implementation notes:

- Start with binary operations in assignments.
- Replace `total = price + tax` with a helper call.
- Add the helper once per module.

Learning focus:

Expression analysis, parameter extraction, and helper generation.

Quality tests:

- Extracts a simple binary expression.
- Does not extract function calls or mutations.
- Generated helper is called with correct arguments.

### `inline_useful_abstractions`

Path:

```text
packages/tools/src/enshittify_tools/mutations/indirection/inline_useful_abstractions.py
```

Purpose:

Remove helpful small abstractions and push their logic into call sites.

High-quality behavior:

- Inline only pure single-return helpers at first.
- Preserve behavior for simple positional arguments.
- Skip decorated functions, async functions, generators, methods, closures, and helpers used as values.
- Record removed abstraction and updated call sites.

Implementation notes:

- Build a map of candidate helper functions.
- Match call expressions by name.
- Substitute arguments into the return expression.

Learning focus:

Symbol substitution and why inlining is harder than it looks.

Quality tests:

- Inlines a simple pure helper.
- Skips a helper with multiple statements.
- Skips a helper with side effects.

### `merge_unrelated_modules`

Path:

```text
packages/tools/src/enshittify_tools/mutations/architecture/merge_unrelated_modules.py
```

Purpose:

Increase coupling by merging files that should remain separate.

High-quality behavior:

- Require explicit file paths.
- Refuse generated, vendor, dependency, and hidden directories by default.
- Preserve a manifest of moved symbols and import updates.
- Support dry-run diff before writing.

Implementation notes:

- This is a workspace-level tool, not just `code: str -> str`.
- Start by producing a proposed merge plan without writing files.
- Then implement write mode through the backend layer, not raw uncontrolled file writes.

Learning focus:

Workspace-aware tools, import rewriting, dry-run planning, and rollback metadata.

Quality tests:

- Produces a merge plan for two tiny files.
- Does not touch files outside scope.
- Can run in dry-run mode.

### `split_cohesive_modules`

Path:

```text
packages/tools/src/enshittify_tools/mutations/architecture/split_cohesive_modules.py
```

Purpose:

Fragment a coherent module into more files, increasing navigation cost.

High-quality behavior:

- Move only top-level functions or constants at first.
- Update imports deterministically.
- Produce a file operation manifest.
- Preserve rollback information.

Implementation notes:

- Use AST to identify top-level symbols.
- Generate sibling files with stable names.
- Keep class splitting for a later phase.

Learning focus:

Multi-file code motion and import generation.

Quality tests:

- Splits one helper into a sibling module.
- Updates the original file.
- Refuses complex cases clearly.

### `weaken_types`

Path:

```text
packages/tools/src/enshittify_tools/mutations/types/weaken_types.py
```

Purpose:

Reduce type precision and weaken static guarantees.

High-quality behavior:

- Rewrite annotations in a controlled way.
- Add required imports such as `Any` when needed.
- Avoid annotations that frameworks inspect at runtime unless configured.
- Record each weakened annotation.

Implementation notes:

- Start with function arguments and return annotations.
- Replace specific annotations with `Any` or remove selected annotations.
- Later, support `TypedDict`, `Protocol`, dataclasses, and Pydantic models.

Learning focus:

Annotation AST nodes, import management, and type-checker impact.

Quality tests:

- Weakens a simple function signature.
- Adds `from typing import Any` exactly once.
- Skips configured symbols.

### `replace_constants_with_magic_values`

Path:

```text
packages/tools/src/enshittify_tools/mutations/obfuscation/replace_constants_with_magic_values.py
```

Purpose:

Replace named constants with raw values at use sites.

High-quality behavior:

- Identify simple module-level constants.
- Replace references in safe scopes only.
- Avoid imported constants and mutable values.
- Record the removed name and inserted values.

Implementation notes:

- Start with uppercase constants assigned to primitive literals.
- Replace `Name` references with copied constant AST nodes.
- Optionally remove the constant only after all references are replaced.

Learning focus:

Symbol lookup, constant detection, and safe AST copying.

Quality tests:

- Replaces an uppercase integer constant.
- Skips mutable constants like lists and dicts.
- Skips imported constants.

### `expand_conditionals`

Path:

```text
packages/tools/src/enshittify_tools/mutations/control_flow/expand_conditionals.py
```

Purpose:

Turn compact boolean logic into verbose branching.

High-quality behavior:

- Preserve Python short-circuit semantics.
- Avoid expressions with function calls until side effects are handled.
- Keep generated branches parseable and deterministic.
- Record the expanded expression.

Implementation notes:

- Start with `return a and b` or `return a or b`.
- Rewrite to nested `if` statements.
- Later support assignments and more complex boolean trees.

Learning focus:

Boolean semantics, short-circuiting, and branch generation.

Quality tests:

- Expands simple `and`.
- Expands simple `or`.
- Skips function-call operands until supported.

### `introduce_alias_chains`

Path:

```text
packages/tools/src/enshittify_tools/mutations/indirection/introduce_alias_chains.py
```

Purpose:

Hide direct values behind chains of redundant aliases.

High-quality behavior:

- Insert a bounded number of aliases.
- Avoid aliasing mutable values in ways that change behavior.
- Generate stable alias names.
- Mark generated aliases so repeated runs do not explode.

Implementation notes:

- Start with simple assignments and function-call arguments.
- Insert aliases immediately before the statement that uses them.
- Later support cross-function and cross-module aliases.

Learning focus:

Statement insertion and data-flow basics.

Quality tests:

- Adds a two-step alias chain.
- Does not change return values in simple cases.
- Does not duplicate aliases on repeated runs.

### `convert_async_style`

Path:

```text
packages/tools/src/enshittify_tools/mutations/control_flow/convert_async_style.py
```

Purpose:

Make async code less direct or less consistent without accidentally blocking the event loop.

High-quality behavior:

- Preserve async semantics.
- Avoid converting async code to blocking sync code.
- Only rewrite clear `await` patterns.
- Record inserted helper coroutine or style change.

Implementation notes:

- Start with async functions that immediately return an awaited call.
- Insert a redundant async helper and await that helper.
- Later support callback-style or task-style rewrites with strict tests.

Learning focus:

Async AST nodes, valid `await` placement, and runtime behavior.

Quality tests:

- Rewrites a simple async function.
- Output parses.
- The result can be awaited in a test.

### `inflate_dependencies`

Path:

```text
packages/tools/src/enshittify_tools/mutations/dependencies/inflate_dependencies.py
```

Purpose:

Increase dependency surface area or import coupling.

High-quality behavior:

- Prefer dry-run planning before changing manifests.
- Never install packages automatically.
- Only add dependencies from an allowlist or already-present project dependencies.
- Record dependency and import changes.

Implementation notes:

- Start by adding redundant standard-library imports or replacing simple code with an already-available dependency.
- Later, support manifest changes through explicit permission gates.

Learning focus:

Dependency inspection, manifest handling, and permission boundaries.

Quality tests:

- Adds an allowed redundant import.
- Refuses a dependency not in the allowlist.
- Does not modify package manifests unless explicitly requested.

### `spread_configuration`

Path:

```text
packages/tools/src/enshittify_tools/mutations/config_sprawl/spread_configuration.py
```

Purpose:

Scatter configuration so related values are harder to understand together.

High-quality behavior:

- Detect config dictionaries, constants, or config objects.
- Split or duplicate selected values with a clear manifest.
- Preserve runtime values unless configured otherwise.
- Avoid secrets and environment-specific values.

Implementation notes:

- Start with a single Python module containing a config dictionary.
- Split it into multiple named constants or smaller dictionaries.
- Later support `.env`, YAML, TOML, and framework config files.

Learning focus:

Config detection, structured data transforms, and secret hygiene.

Quality tests:

- Splits a simple config dictionary.
- Skips keys that look secret-like.
- Output preserves the same values where intended.

### `inject_dead_code`

Path:

```text
packages/tools/src/enshittify_tools/mutations/dead_code/inject_dead_code.py
```

Purpose:

Add unused, unreachable, or inert code that increases noise.

High-quality behavior:

- Insert code that does not affect runtime behavior.
- Bound the amount inserted per run.
- Mark generated code so repeated runs stay controlled.
- Record inserted symbols and line positions.

Implementation notes:

- Start by inserting unused helper functions at module level.
- Later insert unreachable branches inside functions.
- Avoid imports, I/O, network calls, sleep calls, and expensive computation.

Learning focus:

Safe inert-code generation and evaluator design.

Quality tests:

- Inserts one unused helper.
- Output parses.
- Running selected public functions returns the same values.

### `degrade_error_handling`

Path:

```text
packages/tools/src/enshittify_tools/mutations/error_handling/degrade_error_handling.py
```

Purpose:

Make error handling less specific, less informative, or less recoverable.

High-quality behavior:

- Apply only to explicit, supported exception patterns.
- Preserve raising behavior unless configured to swallow errors.
- Record the before/after exception type and message.
- Avoid security-sensitive or transaction-sensitive error paths by default.

Implementation notes:

- Start by broadening specific exception handlers to `Exception`.
- Replace highly specific messages with vague messages.
- Keep exception chaining behavior configurable.

Learning focus:

Exception AST nodes and failure-mode design.

Quality tests:

- Broadens `except ValueError`.
- Replaces a message.
- Does not silently swallow exceptions by default.

### `degrade_naming`

Path:

```text
packages/tools/src/enshittify_tools/mutations/naming/degrade_naming.py
```

Purpose:

Replace good names with vague, generic, or misleading human-looking names.

High-quality behavior:

- Use scope-aware renaming like `obfuscate_identifiers`.
- Generate names from a controlled vocabulary.
- Avoid public APIs, imports, builtins, dunders, attributes, `self`, and `cls`.
- Return a rename map.

Difference from `obfuscate_identifiers`:

`obfuscate_identifiers` produces unreadable names like `_lI0`. `degrade_naming` produces bad but plausible names like `data`, `thing`, `value2`, `manager`, `helper`, or `obj`.

Learning focus:

Scope-aware renaming with a different product intent.

Quality tests:

- Renames locals to generic names.
- Does not use the same generic name in conflicting scopes.
- Does not rename public APIs.

### `remove_documentation`

Path:

```text
packages/tools/src/enshittify_tools/mutations/documentation/remove_documentation.py
```

Purpose:

Remove explanatory comments and docstrings.

High-quality behavior:

- Use AST for docstrings.
- Use `tokenize` for comments because comments are not preserved in Python AST.
- Preserve shebangs, encoding comments, and protected legal or policy headers unless explicitly configured.
- Report removed docstrings and comments.

Implementation notes:

- Start with module, class, and function docstrings.
- Then add comment removal with token processing.
- Keep formatting valid after token rewrites.

Learning focus:

The difference between syntax trees and token streams.

Quality tests:

- Removes function docstrings.
- Removes ordinary comments.
- Preserves shebang and encoding comments.
- Output parses.

### `collapse_formatting`

Path:

```text
packages/tools/src/enshittify_tools/mutations/formatting/collapse_formatting.py
```

Purpose:

Reduce visual readability while preserving syntax.

High-quality behavior:

- Respect indentation-sensitive syntax.
- Preserve parseability.
- Bound the transformation.
- Do not destroy generated diffs so badly that the harness cannot inspect them.

Implementation notes:

- Start by removing blank lines and redundant spaces.
- Use `tokenize` rather than arbitrary string replacement.
- Later support single-line compression for small functions only.

Learning focus:

Token-level formatting and syntax constraints.

Quality tests:

- Removes blank lines.
- Keeps Python indentation valid.
- Output parses.

## LangGraph Integration Design

Once tools work independently, the harness graph should coordinate them.

Suggested state:

```python
from typing import TypedDict


class MutationState(TypedDict):
    code: str
    file_path: str | None
    language: str
    selected_tools: list[str]
    applied_tools: list[str]
    warnings: list[str]
    score: float | None
```

Example node:

```python
def apply_obfuscate_identifiers(state: MutationState) -> dict:
    result = obfuscate_identifier_source(state["code"])
    return {
        "code": result.code,
        "applied_tools": [*state["applied_tools"], "obfuscate_identifiers"],
        "warnings": [*state["warnings"], *result.warnings],
    }
```

The graph should own:

- Tool selection.
- Retry logic.
- Parse/build/test gates.
- Evaluator scoring.
- Rollback.
- Human approval for risky workspace-level changes.
- Trace events and final reports.

The individual tool should not know how the whole run is orchestrated.

## Registration Plan

Once a tool works:

1. Export its pure function and LangChain wrapper from the module.
2. Add it to the tool catalog.
3. Add unit tests.
4. Add a small fixture.
5. Add evaluator expectations where relevant.
6. Add a LangGraph node only after the pure function is stable.

## Definition of Done

A mutation tool is complete when:

- The pure function is implemented.
- The LangChain wrapper imports and invokes correctly.
- The output is deterministic.
- The tool returns useful metadata.
- The tool has tests for success, skip, and invalid input.
- The tool is registered in the catalog.
- The graph can apply it in dry-run mode.
- The graph can roll back or reject bad output.
- The docs include examples and known limitations.

This keeps the project high quality while still letting each tool teach one concrete piece of LangChain, LangGraph, parsing, or code transformation.
