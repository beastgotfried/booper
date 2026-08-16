"""Opt-in live smoke test for the authorized local Codx wrapper.

This uses the non-interactive ``codx exec`` path. A bare ``codx --yolo`` session
may prompt for Enter; the harness does not start that interactive mode.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from enshittify_sdk import Enshittify


def main() -> int:
    command = os.getenv("ENSHITTIFY_CODX_COMMAND", "codx")
    executable = shutil.which(command)
    if executable is None:
        print(f"SKIP: {command!r} is not on PATH; no provider process was started.")
        return 0

    timeout = float(os.getenv("ENSHITTIFY_CODX_TIMEOUT", "1800"))
    with tempfile.TemporaryDirectory(prefix="enshittify-codx-smoke-") as temporary:
        root = Path(temporary)
        source = root / "source"
        source.mkdir()
        (source / "main.py").write_text(
            "def calculate_total(readable_value):\n    return readable_value\n",
            encoding="utf-8",
        )
        result = Enshittify(
            output_root=root / "runs",
            provider="codx",
            codx_command=executable,
            codx_timeout=timeout,
            mode="agent",
            max_agent_steps=8,
        ).run_repository(
            str(source),
            tools=["degrade_naming", "inject_dead_code"],
            budget=2,
            output="archive",
            instruction=(
                "Inspect the workspace, apply one or two available mutations to main.py, "
                "then review the diff. Use the enshittify MCP tools only."
            ),
        )

        agent = result.report.get("agent") or {}
        provider = result.report["configuration"]["provider"]
        print(f"provider: {provider['name']} / {provider['model']}")
        print(f"status: {result.status}")
        print(f"model calls: {agent.get('model_calls', 0)}")
        print(f"changed files: {len(result.changed_files)}")
        print(f"actions: {len(agent.get('actions', []))}")
        print(f"run directory: {result.run_dir}")
        codx_artifacts = result.report["artifacts"]
        print(f"codx session: {codx_artifacts.get('codx_session')}")
        print(f"codx state: {codx_artifacts.get('codx_state')}")
        if not all(
            Path(codx_artifacts[name]).is_file()
            for name in ("codx_session", "codx_state", "codx_last_message")
        ):
            print("FAIL: Codx artifacts were not persisted.")
            return 1
        if result.report["warnings"]:
            print("warnings:")
            for warning in result.report["warnings"]:
                print(f"- {warning}")

        return 1 if result.status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
