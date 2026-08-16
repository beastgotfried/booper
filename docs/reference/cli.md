# CLI Reference

## `enshittify run SOURCE`

Copies a local directory or clones a Git URL into an isolated run, applies Python mutation tools,
and writes a workspace, patch, manifest, event log, and reports.

Key options:

- `--ref REF`: Git branch, tag, or commit.
- `--profile NAME`: built-in profile; defaults to `maximum`.
- `--intensity low|medium|high|maximum`: controls profile selection.
- `--tool NAME`: bypass profile selection; repeat for an ordered chain.
- `--budget N`: cap tool invocations across files.
- `--provider none|codx|groq`: select deterministic execution, the local Codx wrapper, or GroqCloud.
- `--model MODEL`: override the provider's default production model.
- `--mode auto|deterministic|agent|hybrid`: choose the execution strategy.
- `--api-key-env NAME`: read the provider key from this environment variable.
- `--temperature FLOAT`: model sampling temperature; defaults to `0` for tool reliability.
- `--provider-timeout SECONDS`: timeout for each model call.
- `--provider-max-retries N`: provider retry limit.
- `--provider-max-tokens N`: completion-token limit per call.
- `--codx-command PATH`: Codx wrapper executable; defaults to `codx` or `ENSHITTIFY_CODX_COMMAND`.
- `--codx-timeout SECONDS`: maximum duration of a non-interactive Codx run; defaults to `1800`.
- `--codx-no-yolo`: omit Codx's unattended approval flag.
- `--agent-steps N`: model/tool loop limit.
- `--agent-read-chars N`: source-content limit per read tool call.
- `--no-llm-rewrites`: expose deterministic mutations but disable whole-file LLM rewrites.
- `--instruction TEXT`: add a run-specific degradation objective.
- `--include-tests`: include test files, excluded by default.
- `--dry-run`: inspect and plan without invoking tools.
- `--output workspace|patch|archive`: choose the primary artifact.
- `--output-dir PATH`: choose the persistent run root.
- `--json`: print the complete result object.

Groq keys are read from `GROQ_API_KEY` by default:

```bash
export GROQ_API_KEY="..."
enshittify run ./repository --provider groq --mode hybrid --budget 16
```

Codx uses the local wrapper session rather than an API key:

```bash
enshittify doctor --provider codx
enshittify run ./repository --provider codx --mode hybrid --budget 16
```

The runner starts `codx exec --json`, not the interactive bare command. Therefore it does not need
the Enter press that a manually launched `codx --yolo` session may display. Codx receives one
short-lived stdio MCP server named `enshittify`; only that server's five session-bound tools can
change the staged workspace.

The CLI intentionally has no `--api-key` argument because command arguments are commonly retained
in shell history and visible to local process inspection.

## Discovery

```bash
enshittify tools list [--pack PACK] [--json]
enshittify profiles list [--json]
enshittify providers [--json]
```

## Inspection And Reports

```bash
enshittify inspect SOURCE [--ref REF] [--json]
enshittify report RUN_OR_REPORT_PATH [--json]
```

## Diagnostics

`enshittify doctor` checks Python, Git, LangChain, and LangGraph availability.
`enshittify doctor --provider groq` also checks `langchain-groq` and whether `GROQ_API_KEY` is set.
`enshittify doctor --provider codx` checks the configured wrapper and runs its `--version` command.
Pass `--codx-command PATH` when the wrapper is not on `PATH`.

## Live Groq Smoke Test

The ordinary suite uses scripted chat models and never contacts Groq. After exporting a real key,
run:

```bash
make live-groq
```

The smoke test uses a temporary source repository, a two-action budget, and an isolated output
directory. Set `ENSHITTIFY_GROQ_MODEL` to test a different Groq model. The key is not printed.

For the local wrapper, run `make live-codx`. It skips when `codx` is unavailable and otherwise uses
the current wrapper authentication. The test uses `exec`, so it does not wait for interactive input.
