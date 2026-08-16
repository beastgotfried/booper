"""Model-provider discovery command."""

from __future__ import annotations

import argparse

from enshittify_providers import list_provider_specs

from enshittify_cli.ui.console import print_json


def configure(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("providers", help="Discover model providers.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    specs = list_provider_specs()
    if args.json:
        print_json(
            [
                {
                    "name": spec.name,
                    "description": spec.description,
                    "default_model": spec.default_model,
                    "api_key_env": spec.api_key_env,
                }
                for spec in specs
            ]
        )
        return 0

    width = max(len(spec.name) for spec in specs)
    for spec in specs:
        model = spec.default_model or "deterministic"
        print(f"{spec.name:<{width}}  {model:<28}  {spec.description}")
    return 0
