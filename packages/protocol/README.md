# Protocol

Shared Pydantic contracts used across provider, tool, core, SDK, CLI, and report boundaries.

The implemented model-harness contracts are:

- `ProviderDescriptor`: provider name, model ID, and capability names without credentials.
- `ModelUsage`: aggregate input, output, and total tokens.
- `AgentAction`: one budgeted mutation or rewrite receipt.
- `AgentRunSummary`: provider metadata, stop reason, usage, fallback state, actions, and warnings.

Contracts use `extra="forbid"` so accidental fields, especially provider secrets, cannot silently
enter serialized artifacts.
