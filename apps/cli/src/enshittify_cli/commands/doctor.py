"""Runtime dependency diagnostics."""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import shutil
import subprocess
import sys

from enshittify_providers import CODX_COMMAND_ENV, DEFAULT_CODX_COMMAND


def configure(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("doctor", help="Check runtime requirements.")
    parser.add_argument(
        "--provider",
        choices=("none", "codx", "groq"),
        default="none",
        help="Also check requirements for this provider.",
    )
    parser.add_argument(
        "--codx-command",
        help="Codx wrapper executable or absolute path (default: codx or ENSHITTIFY_CODX_COMMAND).",
    )
    parser.set_defaults(handler=handle)


def _distribution_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def handle(args: argparse.Namespace) -> int:
    checks = [
        ("python", sys.version.split()[0], sys.version_info >= (3, 11)),
        ("git", shutil.which("git") or "not found", shutil.which("git") is not None),
    ]
    for distribution in ("langchain", "langgraph"):
        version = _distribution_version(distribution)
        checks.append((distribution, version or "not installed", version is not None))
    if args.provider == "groq":
        version = _distribution_version("langchain-groq")
        checks.append(
            ("langchain-groq", version or "not installed", version is not None)
        )
        key_is_set = bool(os.getenv("GROQ_API_KEY"))
        checks.append(("GROQ_API_KEY", "set" if key_is_set else "not set", key_is_set))
    if args.provider == "codx":
        command = (
            args.codx_command or os.getenv(CODX_COMMAND_ENV) or DEFAULT_CODX_COMMAND
        )
        executable = shutil.which(command)
        checks.append(("codx", executable or "not found", executable is not None))
        if executable is not None:
            try:
                result = subprocess.run(
                    [executable, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                checks.append(("codx version", type(error).__name__, False))
            else:
                lines = (result.stdout or result.stderr).strip().splitlines()
                detail = lines[0] if lines else "no version output"
                checks.append(("codx version", detail, result.returncode == 0))
    for name, detail, passed in checks:
        print(f"{'ok' if passed else 'fail':<4}  {name:<10} {detail}")
    return 0 if all(passed for _, _, passed in checks) else 1
