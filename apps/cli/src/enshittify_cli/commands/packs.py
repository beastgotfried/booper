"""Tool and profile discovery commands."""

from __future__ import annotations

import argparse

from enshittify_profiles import list_profiles
from enshittify_tools.catalog import iter_mutation_tool_specs

from enshittify_cli.ui.console import print_json


def configure_tools(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("tools", help="Discover mutation tools.")
    commands = parser.add_subparsers(dest="tools_command", required=True)
    list_parser = commands.add_parser("list", help="List registered mutation tools.")
    list_parser.add_argument("--pack", help="Only show tools from one pack.")
    list_parser.add_argument("--json", action="store_true", help="Print JSON output.")
    list_parser.set_defaults(handler=handle_tools_list)


def configure_profiles(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("profiles", help="Discover degradation profiles.")
    commands = parser.add_subparsers(dest="profiles_command", required=True)
    list_parser = commands.add_parser("list", help="List built-in profiles.")
    list_parser.add_argument("--json", action="store_true", help="Print JSON output.")
    list_parser.set_defaults(handler=handle_profiles_list)


def handle_tools_list(args: argparse.Namespace) -> int:
    specs = [
        spec
        for spec in iter_mutation_tool_specs()
        if args.pack is None or spec.pack == args.pack
    ]
    if args.json:
        print_json(
            [
                {"name": spec.name, "pack": spec.pack, "description": spec.description}
                for spec in specs
            ]
        )
        return 0
    if not specs:
        print("No tools matched.")
        return 0
    width = max(len(spec.name) for spec in specs)
    for spec in specs:
        print(f"{spec.name:<{width}}  {spec.pack:<16}  {spec.description}")
    return 0


def handle_profiles_list(args: argparse.Namespace) -> int:
    profiles = list_profiles()
    if args.json:
        print_json(
            [
                {
                    "name": profile.name,
                    "description": profile.description,
                    "tools": list(profile.tools),
                }
                for profile in profiles
            ]
        )
        return 0
    width = max(len(profile.name) for profile in profiles)
    for profile in profiles:
        print(
            f"{profile.name:<{width}}  {len(profile.tools):>2} tools  {profile.description}"
        )
    return 0
