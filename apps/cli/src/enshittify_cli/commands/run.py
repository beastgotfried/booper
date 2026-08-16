"""The repository mutation command."""

from __future__ import annotations

import argparse

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
    client = Enshittify(output_root=args.output_dir)
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
    )

    if args.json:
        print_json(result.to_dict())
        return 0

    summary = result.report["summary"]
    print(f"enshittify.dev run {result.run_id}")
    print(f"status:      {result.status}")
    print(f"profile:     {result.report['configuration']['profile']}")
    print(
        f"files:       {len(result.changed_files)} changed / {summary['candidate_files']} eligible"
    )
    print(f"invocations: {summary['attempted_tool_invocations']}")
    print(f"badness:     {summary['badness_score']} / 100")
    print(f"workspace:   {display_path(result.workspace_dir)}")
    print(f"patch:       {display_path(result.patch_path)}")
    print(f"report:      {display_path(result.report_path)}")
    if result.archive_path:
        print(f"archive:     {display_path(result.archive_path)}")
    if result.report["warnings"]:
        print(f"warnings:    {len(result.report['warnings'])} (see report)")
    return 0
