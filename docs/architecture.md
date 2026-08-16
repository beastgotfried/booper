# Architecture

```text
CLI / Python SDK
        |
        v
provider resolution -----> Groq ChatGroq or custom LangChain chat model
        |
        v
repository workspace ----> untouched original + isolated mutable workspace
        |
        v
RepositoryHarness
  | deterministic: fixed LangGraph tool chain
  | agent: LangChain agent compiled to LangGraph + five workspace tools
  | hybrid: agent path + deterministic remaining-budget fill
        |
        v
shared validation, action ledger, events, patch, manifest, JSON/Markdown report
```

Package ownership:

- `enshittify_protocol`: serializable provider, usage, action, and agent-run contracts.
- `enshittify_providers`: provider registry, generic LangChain wrapper, and Groq adapter.
- `enshittify_tools`: deterministic mutations and session-bound model tool definitions.
- `enshittify_core`: LangGraph loops, execution strategies, budgets, and artifact reporting.
- `enshittify_backends`: isolated local/Git workspaces and artifact persistence.
- `enshittify_sdk`: stable in-process configuration and provider resolution.
- `enshittify_cli`: argument parsing and terminal rendering only.

The outer repository harness and inner model agent are both graphs at different levels. The inner
graph handles repeated model/tool turns. The outer runtime owns repository-level policy and always
produces artifacts, including when a provider fails and hybrid fallback takes over.
