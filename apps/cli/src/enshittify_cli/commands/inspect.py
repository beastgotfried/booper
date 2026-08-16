"""Read-only repository inspection command."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from enshittify_backends import prepare_workspace
from enshittify_languages import inspect_repository

from enshittify_cli.ui.console import human_bytes, print_json


def configure(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "inspect", help="Inspect a local or Git repository without mutating it."
    )
    parser.add_argument("source", help="Local directory or GitHub/Git repository URL.")
    parser.add_argument("--ref", help="Branch, tag, or commit to fetch for a Git URL.")
    parser.add_argument(
        "--max-file-bytes",
        type=int,
        default=1_000_000,
        help="Threshold for eligible Python files.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="enshittify-inspect-") as temporary:
        workspace = prepare_workspace(
            args.source,
            output_root=Path(temporary) / "runs",
            ref=args.ref,
        )
        inspection = inspect_repository(
            workspace.working_dir, max_file_bytes=args.max_file_bytes
        )
        payload = {
            "source": workspace.source,
            "source_kind": workspace.source_kind,
            "revision": workspace.revision,
            "inspection": inspection.to_dict(),
        }

    if args.json:
        print_json(payload)
        return 0

    print(f"source:       {payload['source']}")
    print(f"kind:         {payload['source_kind']}")
    if payload["revision"]:
        print(f"revision:     {payload['revision']}")
    print(f"files:        {inspection.total_files}")
    print(f"size:         {human_bytes(inspection.total_bytes)}")
    print(f"python files: {len(inspection.python_files)}")
    if inspection.languages:
        languages = ", ".join(
            f"{name} ({count})" for name, count in inspection.languages.items()
        )
        print(f"languages:    {languages}")
    if inspection.skipped_large_python_files:
        print(f"large skips:  {len(inspection.skipped_large_python_files)}")
    return 0
