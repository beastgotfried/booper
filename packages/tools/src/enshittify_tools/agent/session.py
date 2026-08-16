"""Validated state and pure operations behind model-facing workspace tools."""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from threading import RLock
from typing import Any

from enshittify_protocol import AgentAction

from enshittify_tools.executor import execute_tool


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True)


@dataclass
class AgentWorkspaceSession:
    """A single isolated repository session shared by the agent's tools."""

    workspace_root: Path
    original_root: Path
    candidate_paths: list[Path]
    inspection: dict[str, Any]
    allowed_mutations: tuple[str, ...]
    mutation_descriptions: dict[str, str]
    profile: str
    intensity: str
    budget: int
    dry_run: bool = False
    allow_rewrites: bool = True
    max_read_chars: int = 24_000
    max_rewrite_chars: int = 100_000
    max_diff_chars: int = 32_000
    actions: list[AgentAction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _candidates: dict[str, Path] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self.workspace_root = self.workspace_root.resolve()
        self.original_root = self.original_root.resolve()
        if self.budget < 1:
            raise ValueError("Agent mutation budget must be at least 1.")
        if self.max_read_chars < 1 or self.max_rewrite_chars < 1:
            raise ValueError("Agent source limits must be positive.")
        for path in self.candidate_paths:
            resolved = path.resolve()
            if not resolved.is_relative_to(self.workspace_root):
                raise ValueError(f"Candidate is outside the workspace: {path}")
            relative = resolved.relative_to(self.workspace_root).as_posix()
            self._candidates[relative] = resolved

    @property
    def used_budget(self) -> int:
        return len(self.actions)

    @property
    def remaining_budget(self) -> int:
        return max(0, self.budget - self.used_budget)

    @property
    def candidate_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._candidates))

    def inspect_workspace(self) -> str:
        with self._lock:
            candidates = []
            for relative, path in sorted(self._candidates.items()):
                content = path.read_text(encoding="utf-8")
                candidates.append(
                    {
                        "path": relative,
                        "bytes": path.stat().st_size,
                        "lines": len(content.splitlines()),
                    }
                )
            mutations = [
                {
                    "name": name,
                    "description": self.mutation_descriptions.get(name, ""),
                }
                for name in self.allowed_mutations
            ]
            return _json(
                {
                    "ok": True,
                    "profile": self.profile,
                    "intensity": self.intensity,
                    "dry_run": self.dry_run,
                    "allow_rewrites": self.allow_rewrites,
                    "budget": {
                        "limit": self.budget,
                        "used": self.used_budget,
                        "remaining": self.remaining_budget,
                    },
                    "repository": self.inspection,
                    "candidate_files": candidates,
                    "available_mutations": mutations,
                }
            )

    def read_source(self, path: str) -> str:
        with self._lock:
            resolved = self._candidate(path)
            if resolved is None:
                return self._path_error(path)
            try:
                content = resolved.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                return _json(
                    {"ok": False, "error": f"Could not read `{path}`: {error}"}
                )
            truncated = len(content) > self.max_read_chars
            visible = content[: self.max_read_chars]
            return _json(
                {
                    "ok": True,
                    "path": self._relative(resolved),
                    "content": visible,
                    "truncated": truncated,
                    "visible_chars": len(visible),
                    "total_chars": len(content),
                }
            )

    def apply_mutation(
        self,
        path: str,
        mutation: str,
        rationale: str = "",
        *,
        actor: str = "model",
    ) -> str:
        with self._lock:
            resolved = self._candidate(path)
            if resolved is None:
                return self._path_error(path)
            if mutation not in self.allowed_mutations:
                return _json(
                    {
                        "ok": False,
                        "error": f"Mutation `{mutation}` is not available in this run.",
                        "available_mutations": list(self.allowed_mutations),
                    }
                )
            if self.remaining_budget == 0:
                return self._budget_error()

            relative = self._relative(resolved)
            try:
                before = resolved.read_text(encoding="utf-8")
                result = execute_tool(mutation, before)
                after = self._normalize_source(result.code, before)
                ast.parse(after, filename=relative)
            except Exception as error:  # noqa: BLE001 - tool failures become agent observations
                action = self._record_action(
                    actor=actor,
                    kind="mutation",
                    path=relative,
                    tool=mutation,
                    rationale=rationale,
                    status="rejected",
                    summary=f"Mutation `{mutation}` failed validation.",
                    warnings=(f"{type(error).__name__}: {error}",),
                )
                self.warnings.extend(action.warnings)
                return _json({"ok": False, "action": action.model_dump(mode="json")})

            changed = after != before
            status = (
                "planned"
                if self.dry_run and changed
                else "changed"
                if changed
                else "unchanged"
            )
            if changed and not self.dry_run:
                resolved.write_text(after, encoding="utf-8")
            action = self._record_action(
                actor=actor,
                kind="mutation",
                path=relative,
                tool=mutation,
                rationale=rationale,
                status=status,
                summary=result.summary,
                edit_count=len(result.edits),
                warnings=tuple(result.warnings),
                before_sha256=_sha256(before),
                after_sha256=_sha256(after),
            )
            self.warnings.extend(result.warnings)
            return _json(
                {
                    "ok": True,
                    "action": action.model_dump(mode="json"),
                    "budget_remaining": self.remaining_budget,
                }
            )

    def rewrite_source(self, path: str, code: str, rationale: str) -> str:
        with self._lock:
            resolved = self._candidate(path)
            if resolved is None:
                return self._path_error(path)
            if not self.allow_rewrites:
                return _json(
                    {"ok": False, "error": "LLM source rewrites are disabled."}
                )
            if self.remaining_budget == 0:
                return self._budget_error()

            relative = self._relative(resolved)
            before = resolved.read_text(encoding="utf-8")
            warning: str | None = None
            after = self._normalize_source(code, before)
            if len(after) > self.max_rewrite_chars:
                warning = (
                    f"Rewrite contains {len(after)} characters; limit is "
                    f"{self.max_rewrite_chars}."
                )
            elif "```" in after:
                warning = (
                    "Rewrite must contain raw Python source without Markdown fences."
                )
            else:
                try:
                    ast.parse(after, filename=relative)
                except SyntaxError as error:
                    warning = f"SyntaxError on line {error.lineno}: {error.msg}"

            if warning:
                action = self._record_action(
                    actor="model",
                    kind="rewrite",
                    path=relative,
                    tool="llm_rewrite",
                    rationale=rationale,
                    status="rejected",
                    summary="LLM rewrite failed source validation.",
                    warnings=(warning,),
                    before_sha256=_sha256(before),
                    after_sha256=_sha256(after),
                )
                self.warnings.append(warning)
                return _json({"ok": False, "action": action.model_dump(mode="json")})

            changed = after != before
            status = (
                "planned"
                if self.dry_run and changed
                else "changed"
                if changed
                else "unchanged"
            )
            if changed and not self.dry_run:
                resolved.write_text(after, encoding="utf-8")
            action = self._record_action(
                actor="model",
                kind="rewrite",
                path=relative,
                tool="llm_rewrite",
                rationale=rationale,
                status=status,
                summary="Applied a model-generated, syntax-validated source rewrite.",
                edit_count=1 if changed else 0,
                before_sha256=_sha256(before),
                after_sha256=_sha256(after),
            )
            return _json(
                {
                    "ok": True,
                    "action": action.model_dump(mode="json"),
                    "budget_remaining": self.remaining_budget,
                }
            )

    def review_diff(self, path: str | None = None) -> str:
        with self._lock:
            if self.dry_run:
                return _json(
                    {
                        "ok": True,
                        "dry_run": True,
                        "planned_actions": [
                            action.model_dump(mode="json") for action in self.actions
                        ],
                    }
                )

            names = [path] if path else list(self.candidate_names)
            chunks: list[str] = []
            reviewed: list[str] = []
            for name in names:
                resolved = self._candidate(name)
                if resolved is None:
                    return self._path_error(name)
                relative = self._relative(resolved)
                before = (self.original_root / relative).read_text(encoding="utf-8")
                after = resolved.read_text(encoding="utf-8")
                if before == after:
                    continue
                reviewed.append(relative)
                chunks.extend(
                    difflib.unified_diff(
                        before.splitlines(keepends=True),
                        after.splitlines(keepends=True),
                        fromfile=f"a/{relative}",
                        tofile=f"b/{relative}",
                    )
                )
            content = "".join(chunks)
            truncated = len(content) > self.max_diff_chars
            return _json(
                {
                    "ok": True,
                    "paths": reviewed,
                    "diff": content[: self.max_diff_chars],
                    "truncated": truncated,
                    "budget_remaining": self.remaining_budget,
                }
            )

    def changed_paths(self) -> list[str]:
        changed = []
        for relative, path in sorted(self._candidates.items()):
            original = self.original_root / relative
            if original.read_bytes() != path.read_bytes():
                changed.append(relative)
        return changed

    def _candidate(self, path: str) -> Path | None:
        normalized = PurePosixPath(path.replace("\\", "/"))
        if normalized.is_absolute() or ".." in normalized.parts:
            return None
        return self._candidates.get(normalized.as_posix())

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.workspace_root).as_posix()

    def _record_action(
        self,
        *,
        actor: str,
        kind: str,
        path: str,
        tool: str,
        rationale: str,
        status: str,
        summary: str,
        edit_count: int = 0,
        warnings: tuple[str, ...] = (),
        before_sha256: str | None = None,
        after_sha256: str | None = None,
    ) -> AgentAction:
        action = AgentAction(
            sequence=len(self.actions) + 1,
            actor=actor,
            kind=kind,
            path=path,
            tool=tool,
            rationale=rationale[:2_000],
            status=status,
            summary=summary,
            edit_count=edit_count,
            warnings=warnings,
            before_sha256=before_sha256,
            after_sha256=after_sha256,
        )
        self.actions.append(action)
        return action

    def _normalize_source(self, code: str, previous: str) -> str:
        if previous.endswith("\n") and not code.endswith("\n"):
            return code + "\n"
        return code

    def _path_error(self, path: str) -> str:
        return _json(
            {
                "ok": False,
                "error": f"Path `{path}` is not an eligible source file.",
                "candidate_files": list(self.candidate_names),
            }
        )

    def _budget_error(self) -> str:
        return _json(
            {
                "ok": False,
                "error": "Mutation budget is exhausted; review the diff and finish.",
                "budget_remaining": 0,
            }
        )
