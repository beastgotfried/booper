# enshittify SDK

The SDK runs the repository harness in-process. It supports the deterministic
pipeline, a model-directed agent, and hybrid execution with deterministic
fallbacks.

## Deterministic run

```python
from enshittify_sdk import Enshittify

result = Enshittify(mode="deterministic").run_repository(
    "./my-repository",
    profile="maximum",
    intensity="high",
    output="archive",
)
print(result.workspace_dir)
```

## Groq-backed agent run

Keep the key outside source control and pass it at runtime:

```python
import os

from enshittify_sdk import Enshittify

result = Enshittify(
    provider="groq",
    api_key=os.environ["GROQ_API_KEY"],
    model="openai/gpt-oss-120b",
    mode="hybrid",
).run_repository(
    "https://github.com/example/project.git",
    budget=12,
    instruction="Prefer confusing but syntax-valid maintainability regressions.",
)
```

`mode="agent"` uses only model-directed actions. `mode="hybrid"` lets the
model choose targeted actions and fills unused mutation budget with the
deterministic tools. The harness writes only to its isolated workspace and
returns a machine-readable report, patch, and optional archive.

## Codx-backed agent run

Use the authorized local Codx wrapper without supplying an API key:

```python
from enshittify_sdk import Enshittify

result = Enshittify(
    provider="codx",
    mode="hybrid",
    codx_timeout=1800,
).run_repository(
    "./my-repository",
    budget=12,
    output="archive",
)
```

The SDK starts the wrapper's non-interactive `exec --json` path and connects a short-lived
enshittify MCP server. A manually launched interactive `codx --yolo` command may ask for Enter;
that prompt is not used by this adapter.

## Custom LangChain models

Any compatible LangChain chat model can be adapted without changing the core
harness:

```python
from enshittify_providers import wrap_chat_model
from enshittify_sdk import Enshittify

provider = wrap_chat_model(
    my_chat_model,
    name="internal",
    model="internal-model-v1",
)
result = Enshittify(provider=provider, mode="agent").run_repository("./repo")
```

The SDK does not log API keys. Provider errors are redacted before they are
stored in reports.
