"""enshittify.dev command-line entry point."""

from __future__ import annotations

import argparse
import sys

from enshittify_backends import WorkspaceError

from enshittify_cli.commands import doctor, inspect, packs, providers, report, run
from enshittify_cli.ui.console import print_error

VERSION = "0.1.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="enshittify",
        description="Make a copied Python codebase dramatically worse, with receipts.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run.configure(subparsers)
    inspect.configure(subparsers)
    packs.configure_tools(subparsers)
    packs.configure_profiles(subparsers)
    providers.configure(subparsers)
    report.configure(subparsers)
    doctor.configure(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args) or 0)
    except (FileNotFoundError, KeyError, OSError, ValueError, WorkspaceError) as error:
        print_error(str(error))
        return 2
    except KeyboardInterrupt:
        print_error("Interrupted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
