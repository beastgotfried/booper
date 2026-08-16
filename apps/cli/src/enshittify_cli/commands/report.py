"""Saved run report command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from enshittify_cli.ui.console import print_json


def configure(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("report", help="Read a saved run report.")
    parser.add_argument(
        "path", help="Run directory, artifacts directory, or report.json."
    )
    parser.add_argument(
        "--json", action="store_true", help="Print the full JSON report."
    )
    parser.set_defaults(handler=handle)


def _resolve_report_path(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    candidates = (
        path,
        path / "report.json",
        path / "artifacts" / "report.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Could not find report.json from: {path}")


def handle(args: argparse.Namespace) -> int:
    report_path = _resolve_report_path(args.path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if args.json:
        print_json(report)
        return 0

    summary = report["summary"]
    print(f"run:         {report['run_id']}")
    print(f"status:      {report['status']}")
    print(f"source:      {report['source']['display']}")
    print(f"profile:     {report['configuration']['profile']}")
    print(f"mode:        {report['configuration'].get('mode', 'deterministic')}")
    provider = report["configuration"].get("provider", {"name": "none", "model": None})
    if provider["name"] != "none":
        print(f"provider:    {provider['name']} / {provider['model']}")
    print(
        f"files:       {len(summary['changed_files'])} changed / {summary['candidate_files']} eligible"
    )
    print(f"invocations: {summary['attempted_tool_invocations']}")
    print(f"badness:     {summary['badness_score']} / 100")
    if report.get("agent"):
        usage = report["agent"]["usage"]
        print(
            f"model calls: {report['agent']['model_calls']} "
            f"({usage['total_tokens']} tokens)"
        )
    print(f"workspace:   {report['artifacts']['workspace']}")
    print(f"patch:       {report['artifacts']['patch']}")
    return 0
