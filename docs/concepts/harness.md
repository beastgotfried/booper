# Harness

The harness is the system around the model, not the model itself. In enshittify.dev it owns source
staging, context limits, prompts, tool schemas, path permissions, mutation budgets, the model/tool
loop, deterministic fallback, validation, event recording, and artifacts.

## Run Topology

1. `enshittify_backends` clones or copies the source into separate `original` and `workspace` trees.
2. `enshittify_languages` identifies eligible Python files and excludes tests unless requested.
3. A profile resolves to an ordered allowlist drawn from the 21 mutation tools.
4. Deterministic mode applies that list directly through the existing LangGraph chain.
5. Agent and hybrid modes use either a LangChain agent compiled to LangGraph or the Codx adapter;
   both receive the same five workspace-scoped tools.
6. Every mutation is budgeted and every resulting Python file is parsed before it is written.
7. Hybrid mode spends any remaining budget through the deterministic engine.
8. The shared reporter writes hashes, actions, events, patch, report, manifest, and optional archive.

## Model Tool Surface

- `inspect_workspace`: repository metadata, eligible files, budget, and mutation allowlist.
- `read_source`: a bounded source read for one exact eligible path.
- `apply_mutation`: one deterministic allowlisted mutation against one exact path.
- `rewrite_source`: one complete model-generated replacement, bounded and syntax-validated.
- `review_diff`: the accumulated diff or the action list during a dry run.

These tools close over one `AgentWorkspaceSession`. The model never receives a root path, arbitrary
filesystem primitive, shell, Git credentials, or direct access to the source repository.

## Modes

`deterministic` is repeatable and requires no provider. `agent` gives the provider control of the
tool loop. `hybrid` combines context-aware model decisions with guaranteed deterministic budget
fill. `auto` is a client-level convenience that selects deterministic or hybrid based on whether a
provider exists.

The provider is deliberately smaller than the harness. Native providers supply a tool-calling
LangChain chat model plus safe metadata. Codx supplies an authorized external process through
`codx exec --json` and stdio MCP. All policy and execution behavior stays provider-neutral.
