# Providers

This package adapts tool-calling LangChain chat models to a small provider-neutral contract.

Built-in modes:

- `none`: no model, resolved by the SDK to deterministic execution.
- `groq`: `ChatGroq` from `langchain-groq`, defaulting to `openai/gpt-oss-120b`.

`wrap_chat_model` accepts any caller-created LangChain chat model. Provider objects expose only a
safe descriptor to reports; API keys remain inside the underlying provider client and are not part
of the contract.

GroqCloud is not xAI/Grok. A future xAI adapter belongs in `adapters/xai.py` and can use the same
contract without changing core execution.
