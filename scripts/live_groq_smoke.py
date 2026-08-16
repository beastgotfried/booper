"""Opt-in live Groq harness smoke test.

The normal test suite never contacts a hosted provider. Run this script with
GROQ_API_KEY set to verify credentials, model access, tool calling, and artifact generation.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from enshittify_sdk import Enshittify


def main() -> int:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("SKIP: GROQ_API_KEY is not set; no network request was made.")
        return 0

    with tempfile.TemporaryDirectory(prefix="enshittify-groq-smoke-") as temporary:
        root = Path(temporary)
        source = root / "source"
        source.mkdir()
        (source / "main.py").write_text(
            "def calculate_total(readable_value):\n    return readable_value\n",
            encoding="utf-8",
        )
        result = Enshittify(
            output_root=root / "runs",
            provider="groq",
            api_key=api_key,
            model=os.getenv("ENSHITTIFY_GROQ_MODEL"),
            mode="agent",
            max_agent_steps=12,
        ).run_repository(
            str(source),
            tools=["degrade_naming", "inject_dead_code"],
            budget=2,
            output="archive",
            instruction="Make the tiny function needlessly indirect but keep it parseable.",
        )

    if result.status == "failed":
        print("FAIL: Groq harness run failed.")
        for warning in result.report["warnings"]:
            print(f"- {warning}")
        return 1

    agent = result.report.get("agent") or {}
    provider = result.report["configuration"]["provider"]
    print(f"PASS: {provider['name']} / {provider['model']}")
    print(f"- status: {result.status}")
    print(f"- model calls: {agent.get('model_calls', 0)}")
    print(f"- changed files: {len(result.changed_files)}")
    print(f"- actions: {len(agent.get('actions', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
