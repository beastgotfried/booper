# enshittify.dev

enshittify.dev is a Python code mutation harness that intentionally makes an isolated copy of a
codebase harder to read and maintain. The harness itself is deterministic, observable, reversible,
and careful with the source repository. The output is the bad part.

The current release accepts local directories and Git URLs, including public GitHub repositories.
It discovers Python files, runs any of 21 LangChain mutation tools through a LangGraph harness, and
produces a mutated workspace with a unified patch and a structured run report.

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

The source is never edited in place. Every run is written beneath `.enshittify/runs` by default.
Use `--output-dir` to place runs elsewhere. Test files are excluded unless `--include-tests` is
provided.

## Commands

```bash
enshittify run --help
enshittify inspect ./repository
enshittify tools list
enshittify profiles list
enshittify report .enshittify/runs/RUN_ID
enshittify doctor
```

Use `--dry-run` to inspect files and record a bounded plan without invoking mutation tools. Use
`--json` on discovery, inspection, run, and report commands for machine-readable output.

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

The deterministic harness does not require an LLM API key. Provider-backed planning can be added
above the same tool and profile contracts without changing repository execution.

## Development

```bash
make install
make test
make smoke
```

The full implementation roadmap and package architecture are in
[`docs/end-to-end-build-plan.md`](docs/end-to-end-build-plan.md).

## Boundaries

Only repositories you own or are authorized to modify should be processed. The CLI does not push,
commit, open pull requests, execute target code, follow repository symlinks, or mutate the source
directory. Git authentication is delegated to the user's configured Git credential helper; secrets
in repository URLs are rejected.
