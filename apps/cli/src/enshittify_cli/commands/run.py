"""The repository mutation command."""

from __future__ import annotations

import argparse
import os

from enshittify_sdk import Enshittify

from enshittify_cli.ui.console import display_path, print_json


def configure(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "run",
        help="Mutate an isolated copy of a local or Git repository.",
        description=(
            "Clone or copy SOURCE into a run directory, apply mutation tools, and emit "
            "a reversible workspace, patch, and report."
        ),
    )
    parser.add_argument("source", help="Local directory or GitHub/Git repository URL.")
    parser.add_argument("--ref", help="Branch, tag, or commit to fetch for a Git URL.")
    parser.add_argument(
        "--profile", default="maximum", help="Named degradation profile."
    )
    parser.add_argument(
        "--intensity",
        choices=("low", "medium", "high", "maximum"),
        default="high",
        help="Fraction of the profile's tools to use.",
    )
    parser.add_argument(
        "--budget", type=int, help="Maximum tool invocations across the repository."
    )
    parser.add_argument(
        "--provider",
        choices=("none", "codx", "groq"),
        default="none",
        help="LLM provider; `none` is deterministic and `codx` uses the local wrapper.",
    )
    parser.add_argument(
        "--model", help="Provider model ID; defaults to the provider's stable model."
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "deterministic", "agent", "hybrid"),
        default="auto",
        help="Execution strategy; auto selects hybrid when a provider is configured.",
    )
    parser.add_argument(
        "--api-key-env",
        metavar="NAME",
        help="Environment variable containing the provider key (default: GROQ_API_KEY).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Provider sampling temperature; zero favors reliable tool calls.",
    )
    parser.add_argument(
        "--provider-timeout",
        type=float,
        default=120.0,
        help="Timeout in seconds for each native provider request.",
    )
    parser.add_argument(
        "--provider-max-retries",
        type=int,
        default=2,
        help="Maximum provider retries for transient failures.",
    )
    parser.add_argument(
        "--provider-max-tokens",
        type=int,
        default=8192,
        help="Maximum completion tokens per model call.",
    )
    parser.add_argument(
        "--codx-command",
        help="Codx wrapper executable or absolute path (default: codx or ENSHTTIFY_CODX_COMMAND).",
    )
    parser.add_argument(
        "--codx-timeout",
        type=float,
        default=1_800.0,
        help="Maximum seconds for one non-interactive Codx run.",
    )
    parser.add_argument(
        "--codx-no-yolo",
        action="store_true",
        help="Do not pass Codex --yolo; mutation calls may require interactive approval.",
    )
    parser.add_argument(
        "--agent-steps",
        type=int,
        default=24,
        help="Maximum model/tool loop iterations before stopping.",
    )
    parser.add_argument(
        "--agent-read-chars",
        type=int,
        default=24_000,
        help="Maximum source characters returned by a read tool call.",
    )
    parser.add_argument(
        "--no-llm-rewrites",
        action="store_true",
        help="Restrict the model to deterministic mutation tools.",
    )
    parser.add_argument(
        "--instruction",
        help="Additional run objective supplied to the degradation agent.",
    )
    parser.add_argument(
        "--tool",
        action="append",
        dest="tools",
        help="Use an exact tool; repeat to define an ordered custom tool chain.",
    )
    parser.add_argument(
        "--include-tests", action="store_true", help="Allow mutation of test files."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect and plan without invoking tools or changing the copied workspace.",
    )
    parser.add_argument(
        "--output",
        choices=("workspace", "patch", "archive"),
        default="workspace",
        help="Primary output artifact; patch and workspace metadata are always retained.",
    )
    parser.add_argument(
        "--output-dir", help="Directory that will contain persistent run directories."
    )
    parser.add_argument(
        "--max-file-bytes",
        type=int,
        default=1_000_000,
        help="Skip Python source files larger than this size.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Print the full JSON result."
    )
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    api_key = None
    if args.provider == "groq" and args.mode != "deterministic":
        api_key_env = args.api_key_env or "GROQ_API_KEY"
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(
                f"Provider `{args.provider}` requires an API key in environment variable "
                f"`{api_key_env}`."
            )

    client = Enshittify(
        output_root=args.output_dir,
        provider=args.provider,
        api_key=api_key,
        model=args.model,
        temperature=args.temperature,
        provider_timeout=args.provider_timeout,
        provider_max_retries=args.provider_max_retries,
        provider_max_tokens=args.provider_max_tokens,
        codx_command=args.codx_command,
        codx_timeout=args.codx_timeout,
        codx_yolo=not args.codx_no_yolo,
        mode=args.mode,
        allow_llm_rewrites=not args.no_llm_rewrites,
        max_agent_steps=args.agent_steps,
        max_agent_read_chars=args.agent_read_chars,
    )
    result = client.run_repository(
        args.source,
        ref=args.ref,
        profile=args.profile,
        intensity=args.intensity,
        budget=args.budget,
        include_tests=args.include_tests,
        dry_run=args.dry_run,
        tools=args.tools,
        output=args.output,
        max_file_bytes=args.max_file_bytes,
        instruction=args.instruction,
    )

    exit_code = 1 if result.status == "failed" else 0
    if args.json:
        print_json(result.to_dict())
        return exit_code

    summary = result.report["summary"]
    print(f"enshittify.dev run {result.run_id}")
    print(f"status:      {result.status}")
    print(f"profile:     {result.report['configuration']['profile']}")
    print(f"mode:        {result.report['configuration']['mode']}")
    provider = result.report["configuration"]["provider"]
    if provider["name"] != "none":
        print(f"provider:    {provider['name']} / {provider['model']}")
    print(
        f"files:       {len(result.changed_files)} changed / {summary['candidate_files']} eligible"
    )
    print(f"invocations: {summary['attempted_tool_invocations']}")
    print(f"badness:     {summary['badness_score']} / 100")
    if result.report["agent"]:
        usage = result.report["agent"]["usage"]
        print(
            f"model calls: {result.report['agent']['model_calls']} "
            f"({usage['total_tokens']} tokens)"
        )
    print(f"workspace:   {display_path(result.workspace_dir)}")
    print(f"patch:       {display_path(result.patch_path)}")
    print(f"report:      {display_path(result.report_path)}")
    if result.archive_path:
        print(f"archive:     {display_path(result.archive_path)}")
    if result.report["warnings"]:
        print(f"warnings:    {len(result.report['warnings'])} (see report)")
    return exit_code
