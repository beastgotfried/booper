# enshittify.dev End-to-End Build Plan

This document is the working implementation guide for turning enshittify.dev into a complete private Python harness.

The final product should accept a target codebase, preferably by GitHub repository URL, clone it into an isolated workspace, run a LangGraph-powered mutation harness, apply tools that intentionally make the codebase worse, and return a reversible artifact such as a patch, branch, pull request, archive, and report.

The product goal is not to build a sloppy tool. The product should be engineered well while the generated output is intentionally terrible. The harness should be deterministic when asked, observable, reversible, testable, and safe to run against a repository the user owns or is authorized to mutate.

## Product Definition

enshittify.dev is a code mutation harness.

The harness has five responsibilities:

1. Ingest a codebase from a local path, GitHub URL, uploaded archive, or SDK input.
2. Inspect the repository and build a structured understanding of files, languages, package managers, tests, and risk boundaries.
3. Select and execute mutation tools using a profile, intensity level, and budget.
4. Validate and score the mutated codebase so the result is bad in the intended way.
5. Return the result as a patch, branch, pull request, archive, or SDK response with a full run report.

The important separation is:

- Tools are the mutation primitives.
- Profiles decide which tools to use, in what order, and how aggressively.
- The harness owns orchestration, state, retries, validation, scoring, and output.
- Backends provide access to repositories, workspaces, GitHub, local files, and artifacts.
- Providers let the harness use any supported LLM when planning or judging mutations.

## Final User Experience

The product should support these paths.

### CLI

```bash
enshittify run https://github.com/acme/example \
  --profile maximum \
  --intensity high \
  --output patch
```

```bash
enshittify run . \
  --profile enterprise-sprawl \
  --budget 40 \
  --dry-run
```

```bash
enshittify tools list
enshittify profiles list
enshittify inspect https://github.com/acme/example
enshittify report ./enshittify-runs/run_123
```

### Server

The app server should expose run orchestration for the proxy, UI, or any external client.

Core endpoints:

- `POST /runs`: create a run.
- `GET /runs/{run_id}`: fetch current run state.
- `GET /runs/{run_id}/events`: stream run events.
- `GET /runs/{run_id}/artifacts`: list patches, reports, archives, logs, and diffs.
- `POST /runs/{run_id}/cancel`: cancel a running mutation.

### SDK

The SDK should let users embed the harness without the app server.

```python
from enshittify_sdk import Enshittify

client = Enshittify(provider="openai", api_key="...")
result = client.run_repository(
    source="https://github.com/acme/example",
    profile="maximum",
    intensity="high",
    output="patch",
)

print(result.report_path)
```

## Safety And Operating Boundaries

This product intentionally degrades code, so the implementation must be careful.

Required boundaries:

- Never mutate a user repository in place by default.
- Always clone or copy into a managed workspace.
- Require explicit confirmation for branch push or pull request creation.
- Never read or print secrets from the target repository.
- Never execute arbitrary target code unless the user enables validation commands.
- Never make network calls from mutated code as a mutation strategy.
- Do not add credential exfiltration, persistence, malware behavior, destructive filesystem operations, or supply-chain attack behavior.
- Preserve rollback data for every run.
- Emit a manifest that explains every file touched and every tool invoked.

Bad output is allowed. Unsafe output is not a product feature.

## Repository Architecture

The current codebase is a Python monorepo. Keep that direction.

```text
apps/
  cli/
    enshittify_cli/
      main.py
      commands/
      output/
  server/
    enshittify_server/
      app.py
      routes/
      workers/

packages/
  core/
    enshittify_core/
      harness/
      runtime/
      state/
      planning/
      reporting/
  tools/
    enshittify_tools/
      mutations/
      catalog.py
      registry.py
      executor.py
      result.py
  backends/
    enshittify_backends/
      workspace/
      git/
      github/
      artifacts/
  languages/
    enshittify_languages/
      python/
      javascript/
      typescript/
      generic/
  profiles/
    enshittify_profiles/
      definitions/
      planner.py
  evaluators/
    enshittify_evaluators/
      metrics/
      scoring.py
  providers/
    enshittify_providers/
      openai.py
      anthropic.py
      grok.py
      local.py
  protocol/
    enshittify_protocol/
      models.py
      events.py
      errors.py
  sdk/
    enshittify_sdk/
      client.py
  testing/
    enshittify_testing/
      fixtures/
      golden/
```

### Package Responsibilities

`apps/cli`

Owns terminal UX, argument parsing, progress output, and local command wiring. It should be thin. It should call `core`, `backends`, and `sdk` instead of implementing mutation logic.

`apps/server`

Owns HTTP APIs, run persistence, background worker dispatch, and streaming events. It should be the integration point for the proxy and future UI.

`packages/core`

Owns the LangGraph harness, run state, mutation loop, planning loop, evaluator loop, report generation, and orchestration contracts.

`packages/tools`

Owns pure mutation tools and tool execution. Tools should be individually testable. Where possible, each tool should expose a pure `mutate_source()` function and a higher-level workspace adapter.

`packages/backends`

Owns IO. This package should know how to clone GitHub repos, create temporary workspaces, write patches, create branches, create pull requests, and store artifacts.

`packages/languages`

Owns language-aware parsing, file selection, syntax checks, import graph helpers, and framework detection. This prevents mutation tools from becoming a pile of fragile string manipulation.

`packages/profiles`

Owns named mutation strategies. Profiles turn a user goal such as `maximum` or `enterprise-sprawl` into a tool plan with intensity, budgets, file targeting, and validation rules.

`packages/evaluators`

Owns scoring. It should measure how much worse the code became by readability, naming quality, indirection, duplication, type strength, dependency bloat, documentation loss, and architectural sprawl.

`packages/providers`

Owns LLM provider clients. The global harness should support OpenAI, Anthropic, Grok, local models, and a no-LLM deterministic mode.

`packages/protocol`

Owns shared data models used by CLI, server, SDK, core, and tests.

`packages/sdk`

Owns the public Python API for embedding enshittify.dev in another app.

`packages/testing`

Owns fixture repositories, golden snapshots, fake GitHub backends, fake providers, and reusable test helpers.

## Core Data Model

The project needs a shared protocol layer so every app speaks the same language.

### RunRequest

Fields:

- `source`: GitHub URL, local path, archive path, or SDK source object.
- `source_type`: `github`, `local`, `archive`, or `inline`.
- `ref`: branch, tag, or commit SHA.
- `profile`: selected profile name.
- `intensity`: `low`, `medium`, `high`, or `maximum`.
- `budget`: maximum number of tool invocations or mutation rounds.
- `provider`: selected LLM provider.
- `provider_config`: model, temperature, key reference, and provider-specific settings.
- `output`: `patch`, `branch`, `pull_request`, `archive`, or `workspace`.
- `dry_run`: whether writes outside the workspace are disabled.
- `validation`: test, lint, typecheck, syntax, or none.

### Workspace

Fields:

- `workspace_id`
- `root_path`
- `source_url`
- `base_ref`
- `base_commit`
- `target_branch`
- `created_at`
- `ignore_rules`
- `artifact_dir`

### RepositoryInspection

Fields:

- `languages`
- `package_managers`
- `frameworks`
- `test_commands`
- `lint_commands`
- `typecheck_commands`
- `entrypoints`
- `source_files`
- `test_files`
- `generated_files`
- `vendor_files`
- `large_files`
- `risk_flags`

### MutationPlan

Fields:

- `profile`
- `intensity`
- `rounds`
- `tool_sequence`
- `target_selectors`
- `file_budget`
- `edit_budget`
- `validation_policy`
- `scoring_targets`

### MutationResult

Fields:

- `tool_name`
- `changed`
- `before_hash`
- `after_hash`
- `edits`
- `warnings`
- `metrics_delta`

### RunReport

Fields:

- `run_id`
- `source`
- `base_commit`
- `profile`
- `intensity`
- `tools_used`
- `files_changed`
- `diff_stats`
- `score_before`
- `score_after`
- `score_delta`
- `validation_results`
- `warnings`
- `artifacts`
- `replay_manifest`

## Harness Runtime

The harness should be implemented as a LangGraph state machine.

### Graph Nodes

`ingest_repository`

Accepts the request source and resolves it into a workspace. For GitHub this means clone, checkout ref, and record base commit.

`inspect_workspace`

Scans the repo and produces `RepositoryInspection`. This node decides what files can be mutated.

`baseline_repository`

Captures initial metrics, optional validation output, file hashes, and git diff baseline.

`select_profile`

Loads the named profile and applies user options such as intensity and budget.

`plan_mutations`

Builds a `MutationPlan`. This can use deterministic rules, an LLM provider, or both.

`apply_mutation_batch`

Selects target files, invokes tools, writes accepted edits to the workspace, and records every result.

`validate_candidate`

Runs configured syntax checks or optional project commands. Validation should be configurable because sometimes the goal is to make code worse while still parseable, and sometimes the goal is full chaos.

`score_degradation`

Calculates badness metrics before and after each round.

`decide_continue`

Stops when the budget is used, the score target is reached, no tools can make progress, or validation fails too hard for the selected mode.

`produce_report`

Writes markdown, JSON, and machine-readable replay artifacts.

`publish_output`

Produces patch, branch, pull request, archive, or leaves the workspace on disk.

### State Shape

The LangGraph state should eventually contain:

```python
class HarnessState(TypedDict):
    run_request: RunRequest
    workspace: Workspace | None
    inspection: RepositoryInspection | None
    baseline: BaselineResult | None
    plan: MutationPlan | None
    current_round: int
    tool_results: list[MutationResult]
    validation_results: list[ValidationResult]
    scores: list[ScoreResult]
    artifacts: list[Artifact]
    report: RunReport | None
    warnings: list[str]
    errors: list[RunError]
```

## GitHub Ingestion

GitHub support should land in layers.

### Phase A: Public Clone

Support:

- `https://github.com/org/repo`
- `https://github.com/org/repo.git`
- optional `--ref`
- shallow clone by default
- full clone when branch output or pull request output is requested

Implementation:

- Use local `git` commands through a backend wrapper.
- Store every run under a managed directory such as `.enshittify/runs/{run_id}` or a system temp path.
- Do not write to the original repo.

### Phase B: Authenticated Clone

Support:

- private repos
- token from environment variable
- token from server-side secret store
- token never logged

Inputs:

- `GITHUB_TOKEN`
- `--github-token-env GITHUB_TOKEN`
- server-side credential reference

### Phase C: Branch And Pull Request Output

Support:

- create branch from base ref
- commit mutated output
- push branch
- optionally create pull request

Required flags:

- `--output branch`
- `--output pull-request`
- `--confirm-publish`

The CLI and server should refuse to push unless the user explicitly chooses a publishing mode.

## Tool System

The tools are the core product surface. They should be built with a strict contract.

### Tool Contract

Every source-level tool should expose:

- a stable tool name
- a short description
- supported languages
- a pure mutation function
- structured edits
- warnings
- deterministic behavior when given a seed
- unit tests

Recommended shape:

```python
def mutate_source(source: str, *, seed: int | None = None) -> MutationResult: ...


def as_langchain_tool(): ...
```

Workspace-level tools should expose:

```python
def mutate_workspace(
    workspace: Workspace, selection: FileSelection, options: ToolOptions
) -> WorkspaceMutationResult: ...
```

The workspace adapter can call the source-level tool over many files.

### Existing Tool Set

These 21 tools are the current core mutation pack:

- `obfuscate_identifiers`
- `encode_literals`
- `rewrite_control_flow`
- `introduce_indirection`
- `duplicate_logic`
- `extract_trivial_helpers`
- `inline_useful_abstractions`
- `merge_unrelated_modules`
- `split_cohesive_modules`
- `weaken_types`
- `replace_constants_with_magic_values`
- `expand_conditionals`
- `introduce_alias_chains`
- `convert_async_style`
- `inflate_dependencies`
- `spread_configuration`
- `inject_dead_code`
- `degrade_error_handling`
- `degrade_naming`
- `remove_documentation`
- `collapse_formatting`

### Tool Categories

Obfuscation:

- `obfuscate_identifiers`: rename local identifiers into unreadable but valid names.
- `encode_literals`: convert simple literals into decoded runtime expressions.
- `collapse_formatting`: compress readable formatting into unpleasant dense code.

Naming damage:

- `degrade_naming`: replace meaningful names with vague names.
- `introduce_alias_chains`: add layers of aliases before reaching real values.

Control-flow damage:

- `rewrite_control_flow`: rewrite simple flow into harder-to-follow equivalents.
- `expand_conditionals`: turn compact conditions into bloated nested branches.
- `convert_async_style`: mix or convert async patterns in awkward ways.

Architecture damage:

- `merge_unrelated_modules`: combine unrelated responsibilities.
- `split_cohesive_modules`: scatter cohesive logic.
- `spread_configuration`: duplicate and relocate configuration.

Abstraction damage:

- `introduce_indirection`: add unnecessary call layers.
- `extract_trivial_helpers`: move tiny expressions into pointless helpers.
- `inline_useful_abstractions`: remove helpful boundaries.

Duplication and dead code:

- `duplicate_logic`: copy useful logic instead of reusing it.
- `inject_dead_code`: add unreachable or unused clutter.

Type and error damage:

- `weaken_types`: remove precise type information.
- `degrade_error_handling`: replace useful error handling with vague behavior.

Dependency damage:

- `inflate_dependencies`: add unnecessary dependencies or imports.

Constant damage:

- `replace_constants_with_magic_values`: inline named values as unexplained literals.

Documentation damage:

- `remove_documentation`: strip comments and docstrings.

## New Tool Ideas

These are additional tools that will make the product more capable.

### Repository Structure Tools

`rename_files_vaguely`

Rename meaningful files to vague names such as `utils2.py`, `helpers_old.py`, or `misc_stuff.py`, while updating imports.

`scatter_related_files`

Move related files into unrelated directories and update imports.

`create_legacy_layer`

Add a compatibility layer that wraps current APIs with older naming and confusing shims.

`deepen_import_paths`

Create nested packages that re-export the real objects through multiple layers.

`barrel_export_everything`

Create broad `__init__.py` or index modules that re-export unrelated symbols.

### State And Side-Effect Tools

`introduce_global_state`

Move local values into module globals or singleton containers.

`add_singleton_manager`

Wrap direct construction in a global manager class.

`hide_inputs_in_context`

Move explicit function arguments into a context object or global config.

`add_mutable_default_args`

For Python only, convert safe defaults into mutable default arguments in low-risk toy contexts.

### Type System Tools

`replace_models_with_dicts`

Turn typed models, dataclasses, or structured objects into plain dictionaries.

`add_any_casts`

Insert `Any`, casts, or ignores to weaken static analysis.

`create_parallel_type_hierarchy`

Duplicate types with slightly different names and unclear conversion functions.

### Testing Damage Tools

`loosen_assertions`

Replace precise test assertions with vague truthiness or broad checks.

`snapshot_noise`

Convert targeted tests into large noisy snapshots.

`add_flaky_waits`

Insert sleeps or timing assumptions in tests only.

`skip_edge_case_tests`

Mark selected edge-case tests as skipped with vague reasons.

### Dependency Tools

`vendor_copy_dependency`

Copy small dependency-like helpers into the repo instead of importing the real package.

`duplicate_package_manager_config`

Add overlapping dependency declarations across config files.

`downgrade_dependency_precision`

Loosen dependency version pins where safe.

### Configuration Tools

`shadow_config_values`

Create multiple config sources where one silently overrides another.

`move_config_to_code`

Inline config into source files.

`move_code_to_config`

Move simple logic into stringly typed config.

### API Design Tools

`invert_boolean_flags`

Rename or invert boolean options so call sites become harder to reason about.

`add_optional_parameter_bloat`

Add many optional parameters with unclear defaults.

`replace_exceptions_with_status_objects`

Turn direct exceptions into inconsistent status dictionaries.

### Performance And Complexity Tools

`add_unnecessary_caching`

Add cache layers around cheap operations.

`replace_comprehensions_with_loops`

Expand concise expressions into verbose manual loops.

`add_redundant_serialization`

Serialize and deserialize data between functions unnecessarily.

### Documentation And Comments Tools

`add_misleading_comments`

Add comments that state obvious facts or stale intent without changing runtime behavior.

`generate_changelog_noise`

Add long internal changelog sections with little value.

## Profiles

Profiles are named strategies. They are not tools.

### `subtle`

Goal: make the repo slightly worse while keeping most tests likely to pass.

Tool bias:

- `degrade_naming`
- `extract_trivial_helpers`
- `replace_constants_with_magic_values`
- `expand_conditionals`
- `remove_documentation`

Validation:

- syntax required
- tests optional

### `obfuscation-heavy`

Goal: make code difficult to read.

Tool bias:

- `obfuscate_identifiers`
- `encode_literals`
- `collapse_formatting`
- `introduce_alias_chains`
- `inject_dead_code`

Validation:

- syntax required
- formatting ignored

### `enterprise-sprawl`

Goal: make a simple repo look like an over-designed internal platform.

Tool bias:

- `introduce_indirection`
- `extract_trivial_helpers`
- `merge_unrelated_modules`
- `split_cohesive_modules`
- `spread_configuration`
- `add_singleton_manager`
- `create_legacy_layer`

Validation:

- syntax required
- import checks preferred

### `dependency-bloat`

Goal: add unnecessary imports, package config noise, and runtime layers.

Tool bias:

- `inflate_dependencies`
- `duplicate_package_manager_config`
- `vendor_copy_dependency`
- `add_redundant_serialization`

Validation:

- syntax required
- install check optional

### `test-rot`

Goal: make tests less useful.

Tool bias:

- `loosen_assertions`
- `snapshot_noise`
- `add_flaky_waits`
- `skip_edge_case_tests`

Validation:

- tests may still pass, but should become weaker

### `maximum`

Goal: use every safe category aggressively.

Tool bias:

- all tools
- repeated rounds
- multi-file operations
- scoring loop

Validation:

- syntax optional depending on user flag
- report required

## Badness Scoring

The evaluator should give the harness feedback. The goal is to maximize badness within the selected constraints.

Suggested metrics:

- Identifier entropy: names become shorter, vaguer, or more random.
- Readability loss: line length, nesting depth, branch count, and expression complexity increase.
- Duplication increase: repeated blocks or similar AST fragments increase.
- Type weakening: annotations, schemas, and precise models decrease.
- Documentation loss: comments and docstrings decrease.
- Indirection increase: call depth and wrapper count increase.
- Dependency bloat: dependency count or import count increases.
- Config sprawl: config values appear in more places.
- File sprawl: related symbols spread across more files.
- Test weakness: assertion specificity decreases.
- Validation damage: optional, only when the selected mode allows breaking behavior.

Each metric should return:

- `name`
- `before`
- `after`
- `delta`
- `weight`
- `explanation`

The final score can be a weighted sum.

## Validation Modes

The user should choose how broken the output may be.

`parseable`

Mutated files must parse. This is the default for a useful demo.

`importable`

Mutated project should still import key modules.

`tests-pass`

The harness tries to make the code worse while keeping tests green.

`chaos`

Syntax, imports, tests, and build quality may break. The report must say what broke.

`dry-run`

No mutation is written. The harness returns a plan and predicted badness.

## Artifact Outputs

Every run should create an artifact directory.

```text
run_123/
  request.json
  inspection.json
  plan.json
  events.jsonl
  report.md
  report.json
  replay_manifest.json
  patch.diff
  changed_files/
  logs/
```

Required artifacts:

- `request.json`: original user request with secrets redacted.
- `inspection.json`: repository scan.
- `plan.json`: chosen tool sequence.
- `events.jsonl`: every state transition and tool result.
- `report.md`: human-readable summary.
- `report.json`: machine-readable summary.
- `replay_manifest.json`: exact replay data.
- `patch.diff`: unified diff from base commit.

Optional artifacts:

- changed archive
- GitHub branch URL
- pull request URL
- validation logs
- score charts

## CLI Design

Use Typer for the CLI unless the project standard changes.

Commands:

```text
enshittify run SOURCE
enshittify inspect SOURCE
enshittify plan SOURCE
enshittify tools list
enshittify tools describe TOOL_NAME
enshittify profiles list
enshittify profiles describe PROFILE_NAME
enshittify report RUN_PATH
```

Important flags for `run`:

```text
--profile TEXT
--intensity low|medium|high|maximum
--budget INTEGER
--provider openai|anthropic|grok|local|none
--model TEXT
--ref TEXT
--output patch|branch|pull-request|archive|workspace
--validation parseable|importable|tests-pass|chaos
--dry-run
--confirm-publish
--seed INTEGER
--include PATTERN
--exclude PATTERN
```

The CLI should stream progress and end with:

- files changed
- tools used
- badness score delta
- validation status
- artifact path
- next command to inspect the report

## Server Design

The server should be a thin orchestration API over the same core runtime.

Recommended stack:

- FastAPI for HTTP routes.
- Background worker abstraction for long runs.
- SQLite for local development run metadata.
- File artifact store for local development.
- Pluggable storage later if deployment needs it.

Server run flow:

1. Receive `RunRequest`.
2. Validate source and credentials.
3. Create run record.
4. Dispatch background job.
5. Stream state events.
6. Expose artifacts.

The server should not contain mutation logic. It should call `core`.

## Provider Strategy

The product should work with one LLM at a time per run, but support multiple providers.

Provider interface:

```python
class Provider:
    name: str

    def complete(self, request: ProviderRequest) -> ProviderResponse: ...
```

Supported provider modes:

- `none`: deterministic tool planning only.
- `groq`: GroqCloud-hosted model through `langchain-groq`.
- `openai`: OpenAI model.
- `anthropic`: Claude model.
- `xai`: xAI/Grok model; this is distinct from GroqCloud.
- `local`: local OpenAI-compatible server.

Use provider calls for:

- selecting mutation strategy from repository inspection
- explaining report results
- judging whether a mutation made code worse
- generating targeted naming or architecture degradation ideas

Do not require an LLM for every mutation. The deterministic tool system should be strong enough to run without one.

## Phase Plan

### Phase 0: Current Baseline

Goal: acknowledge what exists.

Current status:

- Python monorepo exists.
- Core harness package exists.
- Tools package exists.
- 21 source-level mutation tools exist.
- Tool catalog, registry, executor, and shared result objects exist.
- Basic core and tools tests exist.

Exit criteria:

- Existing tests pass.
- Existing docs point to this build plan.

### Phase 1: Protocol Models

Goal: centralize shared models.

Build:

- `RunRequest`
- `Workspace`
- `RepositoryInspection`
- `MutationPlan`
- `MutationResult`
- `WorkspaceMutationResult`
- `ValidationResult`
- `ScoreResult`
- `Artifact`
- `RunReport`
- error models

Tests:

- model serialization
- secret redaction
- backwards-compatible defaults

Exit criteria:

- CLI, server, SDK, and core can import the same protocol models.

### Phase 2: Workspace And Git Backends

Goal: safely ingest local paths and GitHub repos.

Build:

- local workspace copy backend
- GitHub public clone backend
- git diff backend
- patch writer
- artifact directory writer
- ignore rules for vendor, generated, virtualenv, lockfiles, and large files

Tests:

- clone local bare repo fixture
- copy local repo fixture
- create diff
- rollback workspace
- artifact writes

Exit criteria:

- `enshittify inspect SOURCE` can create a workspace and report files without mutating the original source.

### Phase 3: Repository Inspection

Goal: understand what the harness is mutating.

Build:

- language detection
- package manager detection
- test command detection
- source/test/generated/vendor file classification
- file size limits
- Python AST parse check
- generic text fallback

Tests:

- Python repo fixture
- mixed repo fixture
- generated/vendor exclusion
- syntax error handling

Exit criteria:

- inspection produces useful structured data for profiles and tools.

### Phase 4: Tool Contract Upgrade

Goal: make tools usable at repository scale.

Build:

- shared `ToolOptions`
- shared file selection object
- workspace adapter for source-level tools
- deterministic seed support
- tool capability metadata
- per-language support declarations
- common result conversion

Tests:

- every tool can run through the workspace adapter
- every tool reports structured edits
- every tool handles invalid syntax gracefully
- deterministic output with seed

Exit criteria:

- one call can apply selected tools across selected files in a workspace.

### Phase 5: Profiles And Planning

Goal: convert user intent into a mutation plan.

Build:

- profile definitions
- intensity mapping
- tool weights
- file targeting rules
- budget rules
- deterministic planner
- optional LLM-assisted planner

Tests:

- each profile returns a valid plan
- intensity changes budget and aggressiveness
- unsupported tools are excluded for unsupported languages

Exit criteria:

- `enshittify plan SOURCE --profile PROFILE` returns a readable mutation plan.

### Phase 6: LangGraph Harness

Goal: orchestrate the full run.

Build:

- graph nodes listed in this document
- state transitions
- event logging
- retry policy
- continue/stop decision logic
- cancellation hook
- replay manifest

Tests:

- full run on fixture repo
- budget stop
- score stop
- cancellation
- failed tool handling

Exit criteria:

- core can run a complete mutation loop over a local workspace.

### Phase 7: Evaluators And Scoring

Goal: measure how bad the result became.

Build:

- readability metrics
- duplication metrics
- type weakening metrics
- documentation metrics
- import/dependency metrics
- badness score
- score explanations

Tests:

- score increases for known bad fixture
- score remains stable for no-op
- metrics serialize into report

Exit criteria:

- every run gets before/after scores and a clear explanation.

### Phase 8: CLI

Goal: expose the product locally.

Build:

- Typer CLI app
- `run`
- `inspect`
- `plan`
- `tools list`
- `tools describe`
- `profiles list`
- `profiles describe`
- `report`
- terminal progress output

Tests:

- command parsing
- local repo run
- GitHub fixture run through local bare repo
- dry run
- output modes

Exit criteria:

- user can run the harness from the terminal against a local path or GitHub URL.

### Phase 9: Server

Goal: expose the harness as an app server.

Build:

- FastAPI app
- run creation
- run state polling
- event stream
- artifact download
- cancellation
- local run database
- background worker

Tests:

- API contract tests
- background run test
- event stream test
- artifact retrieval test
- cancellation test

Exit criteria:

- proxy or UI can create and observe mutation runs.

### Phase 10: GitHub Publishing

Goal: turn mutated output into branch or pull request.

Build:

- authenticated clone
- branch creation
- commit writer
- push branch
- pull request creation
- publish confirmation guard

Tests:

- branch creation against local remote fixture
- commit content test
- dry-run refuses publish
- token redaction test

Exit criteria:

- authorized users can create a branch or PR with enshittified changes.

### Phase 11: SDK

Goal: expose a stable Python API.

Build:

- `Enshittify` client
- sync run methods
- provider configuration
- artifact access
- typed return objects
- examples

Tests:

- SDK local run
- SDK GitHub run with fake backend
- SDK no-LLM mode

Exit criteria:

- another Python app can use enshittify.dev without shelling out to the CLI.

### Phase 12: Quality And Hardening

Goal: make the product reliable enough to demo and keep building.

Build:

- golden fixture repositories
- snapshot reports
- replay tests
- stress tests on larger repos
- structured logs
- timeout handling
- cleanup jobs
- docs examples

Tests:

- e2e happy path
- e2e dry run
- e2e chaos mode
- e2e branch output
- e2e server run

Exit criteria:

- the product can repeatedly mutate real sample repos and produce useful artifacts.

## Implementation Order

Build in this order:

1. Protocol models.
2. Workspace and git backends.
3. Repository inspection.
4. Workspace adapter for current tools.
5. Profiles and deterministic planner.
6. Core LangGraph run loop.
7. Report and artifact generation.
8. CLI `inspect`, `plan`, and `run`.
9. Evaluators and score loop.
10. Server API.
11. GitHub branch and pull request publishing.
12. SDK polish.
13. New advanced tools.

This order gives a usable CLI before the server is complete.

## Testing Strategy

Testing should be treated as a core feature because mutation tools are easy to break.

Unit tests:

- pure mutation functions
- result serialization
- profile planning
- scoring functions
- provider adapters with fake responses

Contract tests:

- every tool follows the same metadata contract
- every tool can be found in the catalog
- every profile references real tools
- every protocol model redacts secrets correctly

Integration tests:

- local workspace run
- GitHub clone using a local bare repo fixture
- tool chain over multiple files
- report generation
- patch generation

End-to-end tests:

- CLI run against fixture repo
- server run against fixture repo
- SDK run against fixture repo
- chaos mode run
- parseable mode run
- branch output run

Golden tests:

- known fixture input
- known plan
- known diff shape
- known report fields

## First Milestone Definition

The first serious milestone should be:

```bash
enshittify run ./examples/fixture-python \
  --profile obfuscation-heavy \
  --validation parseable \
  --output patch
```

Expected behavior:

- creates isolated workspace
- inspects Python files
- applies at least five tools
- writes patch
- writes report
- prints score delta
- original fixture remains unchanged

## Second Milestone Definition

The second milestone should be:

```bash
enshittify run https://github.com/org/repo \
  --profile maximum \
  --intensity high \
  --output archive
```

Expected behavior:

- clones public GitHub repo
- runs workspace-level tool loop
- mutates multiple files
- writes archive and patch
- writes report
- does not push anything

## Third Milestone Definition

The third milestone should be:

```bash
enshittify run https://github.com/org/repo \
  --profile enterprise-sprawl \
  --output pull-request \
  --confirm-publish
```

Expected behavior:

- authenticates with GitHub
- creates branch
- commits mutated output
- opens pull request
- includes report summary in PR body

## Documentation To Create Next

After this plan, fill these docs:

- `docs/architecture.md`: detailed architecture and package boundaries.
- `docs/concepts/harness.md`: LangGraph harness design.
- `docs/concepts/tools.md`: tool contract and authoring guide.
- `docs/concepts/profiles.md`: profile design and strategy examples.
- `docs/concepts/backends.md`: workspace, git, GitHub, and artifact backends.
- `docs/concepts/evaluators.md`: metrics and badness scoring.
- `docs/concepts/security.md`: safety boundaries and credential handling.
- `docs/reference/cli.md`: exact command reference.
- `docs/reference/sdk.md`: SDK API reference.
- `docs/development/testing.md`: fixture and golden test strategy.

## Non-Negotiables

- The real product must be well designed.
- Mutations must be observable and reversible.
- GitHub publishing must be explicit.
- Tool results must be structured.
- Provider calls must be optional.
- The CLI must work before the server needs to be fancy.
- Every new tool needs tests.
- Every run needs a report.
- The codebase being mutated can become awful. The enshittify.dev codebase should not.
