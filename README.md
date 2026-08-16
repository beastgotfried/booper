# enshittify.dev

enshittify.dev is a Python code mutation harness that intentionally makes an isolated copy of a
codebase harder to read and maintain. It can run deterministically or let an LLM inspect the copied
workspace, choose tools, perform targeted rewrites, and review the resulting diff. The harness
itself remains observable, reversible, and careful with the source repository. The output is the
bad part.

The current release accepts local directories and Git URLs, including public GitHub repositories.
It discovers Python files, exposes five workspace-scoped tools to either a LangChain agent compiled
to LangGraph or an authorized local Codx process through MCP, and provides 21 deterministic mutation
tools as its execution engine. Every run produces a mutated workspace, unified patch, event log,
manifest, and structured report.

## Install

Python 3.11 or newer and Git are required.

```bash
python -m pip install -e .
enshittify doctor
```

The package installs the `enshittify` executable. An editable install is appropriate while working
in this private repository; a wheel can be built with `python -m build` after installing the `dev`
extra.

## Run It

Mutate a local repository:

```bash
enshittify run ./path/to/repository \
  --profile maximum \
  --intensity high
```

Clone and mutate a GitHub repository:

```bash
enshittify run https://github.com/owner/repository.git \
  --ref main \
  --profile obfuscation-heavy \
  --intensity maximum \
  --output archive
```

Run an exact tool chain instead of a profile:

```bash
enshittify run . \
  --tool obfuscate_identifiers \
  --tool encode_literals \
  --tool collapse_formatting \
  --budget 30
```

Run the Groq-backed hybrid harness:

```bash
export GROQ_API_KEY="your-key"
enshittify doctor --provider groq
enshittify run . \
  --provider groq \
  --mode hybrid \
  --model openai/gpt-oss-120b \
  --profile maximum \
  --budget 16
```

`hybrid` lets the model inspect files, invoke allowlisted mutations, submit syntax-validated source
rewrites, and review its diff. Any budget the model leaves unused is filled by the deterministic
engine. Use `--mode agent` for a model-only mutation loop or `--no-llm-rewrites` to allow model tool
selection without whole-file rewrites.

Run through an authorized local Codx wrapper:

```bash
enshittify doctor --provider codx
enshittify run . \
  --provider codx \
  --mode hybrid \
  --profile maximum \
  --budget 16
```

The Codx adapter invokes `codx --yolo exec --json` and registers a short-lived enshittify stdio
MCP server. Codx chooses when to inspect, read, mutate, rewrite, and review; the MCP server keeps
the path allowlist, mutation budget, AST validation, isolated workspace, and action ledger. It does
not use a private model endpoint or copy Codx credentials. A bare interactive `codx --yolo` command
can wait for an Enter press, but the `exec` subcommand used here is non-interactive and receives the
task through stdin. `--codx-no-yolo` is available for environments that provide their own approval
policy; destructive MCP calls may otherwise be cancelled by Codx.

The source is never edited in place. Every run is written beneath `.enshittify/runs` by default.
Use `--output-dir` to place runs elsewhere. Test files are excluded unless `--include-tests` is
provided.

## Commands

```bash
enshittify run --help
enshittify inspect ./repository
enshittify tools list
enshittify profiles list
enshittify providers --json
enshittify report .enshittify/runs/RUN_ID
enshittify doctor
```

Use `--dry-run` to record a bounded plan without changing the copied workspace. An agent dry run
still calls the configured model. Use `--json` on discovery, inspection, run, and report commands
for machine-readable output.

## Harness Modes

- `deterministic`: apply the selected profile tools directly; no model or API key is required.
- `agent`: let the provider drive the inspect/read/mutate/rewrite/review loop.
- `hybrid`: run the agent first, then spend remaining mutation budget deterministically.
- `auto`: SDK and CLI default; resolves to deterministic for provider `none`, otherwise hybrid.

GroqCloud and xAI/Grok are different providers. This release includes GroqCloud through
`langchain-groq`. The provider contract accepts any caller-supplied LangChain chat model, so future
OpenAI, Anthropic, xAI, local, or OpenAI-compatible adapters do not change the core harness.

## Run Artifacts

Each run has this layout:

```text
run-RUN_ID/
  original/                 untouched baseline
  workspace/                mutated working copy
  artifacts/
    events.jsonl            ordered lifecycle events
    manifest.json           source, tool plan, files, and hashes
    patch.diff              reversible unified patch
    report.json             complete machine-readable result
    report.md               compact human-readable report
    codx-session.json        MCP session configuration for Codx runs
    codx-session-state.json  persisted MCP action ledger for Codx runs
    codx-last-message.txt    final Codx response when available
    mutated-workspace.zip   present when --output archive is used
```

## Profiles

- `subtle`: small readability and maintenance regressions.
- `obfuscation-heavy`: identifiers, literals, documentation, formatting, and control flow.
- `enterprise-sprawl`: indirection, configuration sprawl, weak types, and architecture theater.
- `dependency-bloat`: redundant imports and supporting maintenance noise.
- `chaotic`: a broad mixture of structural and source-level degradation.
- `maximum`: all 21 registered mutation tools.

Run `enshittify profiles list --json` for the exact ordered tool lists.

## Python SDK

```python
from enshittify_sdk import Enshittify

result = Enshittify(output_root="./runs").run_repository(
    "https://github.com/owner/repository.git",
    profile="maximum",
    intensity="high",
    output="archive",
)

print(result.workspace_dir)
print(result.patch_path)
print(result.report_path)
```

Use Groq through the SDK:

```python
import os

from enshittify_sdk import Enshittify

client = Enshittify(
    provider="groq",
    api_key=os.environ["GROQ_API_KEY"],
    model="openai/gpt-oss-120b",
    mode="hybrid",
)
result = client.run_repository("./repository", budget=16)
```

Use the local Codx wrapper through the SDK:

```python
from enshittify_sdk import Enshittify

client = Enshittify(
    output_root="./runs",
    provider="codx",
    mode="hybrid",
    codx_timeout=1800,
)
result = client.run_repository("./repository", budget=16, output="archive")
```

The SDK does not need a Codx API key. The configured wrapper supplies its own authenticated
session; `codx_command` can override the executable path and `codx_yolo=False` can opt out of the
default unattended approval flag.

## Development

```bash
make install
make test
make smoke
make live-groq  # opt-in; skips unless GROQ_API_KEY is set
make live-codx  # opt-in; uses the local codx wrapper when available
```

The full implementation roadmap and package architecture are in
[`docs/end-to-end-build-plan.md`](docs/end-to-end-build-plan.md).

## Boundaries

Only repositories you own or are authorized to modify should be processed. The CLI does not push,
commit, open pull requests, execute target code, follow repository symlinks, or mutate the source
directory. Git authentication is delegated to the user's configured Git credential helper; secrets
in repository URLs are rejected. Model-backed runs send bounded repository metadata and source
content read through agent tools to the selected provider. API keys are never included in reports,
events, manifests, prompts, or command-line arguments.

Codx runs inherit the wrapper's existing local authentication. The wrapper is an external agent
process, so its own network and account policy still applies; enshittify only exposes the isolated
workspace through the registered MCP server.
