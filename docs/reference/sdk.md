# Python SDK Reference

`Enshittify` runs the harness in process without the CLI or app server.

```python
from enshittify_sdk import Enshittify

client = Enshittify(output_root="./enshittify-runs")
result = client.run_repository(
    source="./repository",
    profile="enterprise-sprawl",
    intensity="high",
    budget=100,
    output="workspace",
)
```

The returned result exposes `run_id`, `status`, `run_dir`, `workspace_dir`, `report_path`,
`patch_path`, `archive_path`, `changed_files`, and the complete `report` dictionary.

## Groq

```python
import os

from enshittify_sdk import Enshittify

client = Enshittify(
    output_root="./enshittify-runs",
    provider="groq",
    api_key=os.environ["GROQ_API_KEY"],
    model="openai/gpt-oss-120b",
    mode="hybrid",
    max_agent_steps=24,
)
result = client.run_repository(
    "./repository",
    profile="maximum",
    budget=16,
    instruction="Favor architectural indirection and plausible enterprise ceremony.",
)
```

The plain key is held only in the SDK configuration object with its representation disabled. It is
used to construct the provider and is not copied into reports, manifests, events, or model prompts.

## Custom LangChain Models

Provider switching is based on a small model-provider contract. Wrap any tool-calling LangChain
chat model without changing the harness:

```python
from enshittify_providers import wrap_chat_model
from enshittify_sdk import Enshittify

provider = wrap_chat_model(chat_model, name="internal", model="my-model")
result = Enshittify(provider=provider, mode="agent").run_repository("./repository")
```

Modes are `deterministic`, `agent`, `hybrid`, and `auto`. `auto` selects deterministic mode when
the provider is `none` and hybrid mode for a configured provider.
