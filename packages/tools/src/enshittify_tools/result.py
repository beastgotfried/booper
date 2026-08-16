"""Shared result contracts for tool execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MutationEdit:
    kind: str
    before: str
    after: str
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MutationResult:
    code: str
    changed: bool
    summary: str
    edits: list[MutationEdit]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "changed": self.changed,
            "summary": self.summary,
            "edits": [edit.to_dict() for edit in self.edits],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ToolRun:
    name: str
    result: MutationResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "result": self.result.to_dict(),
        }


@dataclass(frozen=True)
class ToolChainResult:
    code: str
    runs: list[ToolRun]

    @property
    def changed(self) -> bool:
        return any(run.result.changed for run in self.runs)

    @property
    def warnings(self) -> list[str]:
        return [
            warning
            for run in self.runs
            for warning in run.result.warnings
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "changed": self.changed,
            "runs": [run.to_dict() for run in self.runs],
            "warnings": self.warnings,
        }
