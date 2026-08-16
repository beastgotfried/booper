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
- `--include-tests`: include test files, excluded by default.
- `--dry-run`: inspect and plan without invoking tools.
- `--output workspace|patch|archive`: choose the primary artifact.
- `--output-dir PATH`: choose the persistent run root.
- `--json`: print the complete result object.

## Discovery

```bash
enshittify tools list [--pack PACK] [--json]
enshittify profiles list [--json]
```

## Inspection And Reports

```bash
enshittify inspect SOURCE [--ref REF] [--json]
enshittify report RUN_OR_REPORT_PATH [--json]
```

## Diagnostics

`enshittify doctor` checks Python, Git, LangChain, and LangGraph availability.
