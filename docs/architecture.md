# Architecture

```text
CLI / Python SDK
        |
        v
provider resolution -----> Groq/custom LangChain model or local Codx process
        |
        v
repository workspace ----> untouched original + isolated mutable workspace
        |
        v
RepositoryHarness
  | deterministic: fixed LangGraph tool chain
  | agent: LangChain agent compiled to LangGraph + five workspace tools
  | agent: Codx `exec --json` + short-lived stdio MCP server + five workspace tools
  | hybrid: agent path + deterministic remaining-budget fill
        |
        v
shared validation, action ledger, events, patch, manifest, JSON/Markdown report
```

Package ownership:

- `enshittify_protocol`: serializable provider, usage, action, and agent-run contracts.
- `enshittify_providers`: provider registry, generic LangChain wrapper, Groq adapter, and Codx
  process adapter.
- `enshittify_tools`: deterministic mutations and session-bound model tool definitions.
- `enshittify_core`: LangGraph loops, execution strategies, budgets, and artifact reporting.
- `enshittify_backends`: isolated local/Git workspaces and artifact persistence.
- `enshittify_sdk`: stable in-process configuration and provider resolution.
- `enshittify_cli`: argument parsing and terminal rendering only.

The outer repository harness and inner model agent are both graphs at different levels for native
LangChain providers. Codx supplies the outer agent loop through JSONL events while the MCP server
reuses the same session policy and mutation executor. The outer runtime owns repository-level
policy and always produces artifacts, including when a provider fails and hybrid fallback takes
over.
