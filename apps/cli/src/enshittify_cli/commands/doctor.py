"""Runtime dependency diagnostics."""

from __future__ import annotations

import argparse
import importlib.metadata
import shutil
import sys


def configure(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("doctor", help="Check runtime requirements.")
    parser.set_defaults(handler=handle)


def _distribution_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def handle(_args: argparse.Namespace) -> int:
    checks = [
        ("python", sys.version.split()[0], sys.version_info >= (3, 11)),
        ("git", shutil.which("git") or "not found", shutil.which("git") is not None),
    ]
    for distribution in ("langchain", "langgraph"):
        version = _distribution_version(distribution)
        checks.append((distribution, version or "not installed", version is not None))
    for name, detail, passed in checks:
        print(f"{'ok' if passed else 'fail':<4}  {name:<10} {detail}")
    return 0 if all(passed for _, _, passed in checks) else 1
