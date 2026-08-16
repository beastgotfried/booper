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
- `--provider none|groq`: select deterministic execution or GroqCloud.
- `--model MODEL`: override the provider's default production model.
- `--mode auto|deterministic|agent|hybrid`: choose the execution strategy.
- `--api-key-env NAME`: read the provider key from this environment variable.
- `--temperature FLOAT`: model sampling temperature; defaults to `0` for tool reliability.
- `--provider-timeout SECONDS`: timeout for each model call.
- `--provider-max-retries N`: provider retry limit.
- `--provider-max-tokens N`: completion-token limit per call.
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

## Live Groq Smoke Test

The ordinary suite uses scripted chat models and never contacts Groq. After exporting a real key,
run:

```bash
make live-groq
```

The smoke test uses a temporary source repository, a two-action budget, and an isolated output
directory. Set `ENSHITTIFY_GROQ_MODEL` to test a different Groq model. The key is not printed.
