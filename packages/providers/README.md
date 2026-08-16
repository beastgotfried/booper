# Providers

This package adapts tool-calling LangChain chat models to a small provider-neutral contract.

Built-in modes:

- `none`: no model, resolved by the SDK to deterministic execution.
- `codx`: an authorized local Codx CLI wrapper connected through a short-lived stdio MCP server.
- `groq`: `ChatGroq` from `langchain-groq`, defaulting to `openai/gpt-oss-120b`.

`wrap_chat_model` accepts any caller-created LangChain chat model. Provider objects expose only a
safe descriptor to reports; API keys remain inside the underlying provider client and are not part
of the contract.

GroqCloud is not xAI/Grok. A future xAI adapter belongs in `adapters/xai.py` and can use the same
contract without changing core execution.

## Codx boundary

Codx is an external coding agent, not a LangChain `BaseChatModel`, so it has a dedicated adapter.
The core harness starts `codx exec --json`, configures an MCP server whose process is owned by
enshittify, and parses Codx's JSONL lifecycle events for model-call and usage metadata. The MCP
server delegates to the same `AgentWorkspaceSession` used by the native LangChain loop. This keeps
provider-specific process details out of mutation tools while preserving one budget and action
ledger.

The adapter never reads or copies Codx authentication files. It inherits the authenticated wrapper
environment. The default `--yolo` flag is intentional because mutation tools are destructive MCP
operations; the target is still an isolated staged workspace and the original source is outside
that writable boundary. Use `codx_yolo=False` or `--codx-no-yolo` when an external approval policy
is available.
