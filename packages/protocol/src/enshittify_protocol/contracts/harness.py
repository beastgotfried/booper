"""Contracts emitted by the model-directed harness."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from enshittify_protocol.contracts.model import ModelUsage, ProviderDescriptor


class AgentAction(BaseModel):
    """One budgeted workspace mutation requested by the model or fallback."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=1)
    actor: Literal["model", "fallback"]
    kind: Literal["mutation", "rewrite"]
    path: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    rationale: str = ""
    status: Literal["changed", "unchanged", "planned", "rejected"]
    summary: str
    edit_count: int = Field(default=0, ge=0)
    warnings: tuple[str, ...] = ()
    before_sha256: str | None = None
    after_sha256: str | None = None


class AgentRunSummary(BaseModel):
    """Serializable trace metadata for one model-directed run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["agent", "hybrid"]
    provider: ProviderDescriptor
    model_calls: int = Field(default=0, ge=0)
    usage: ModelUsage = Field(default_factory=ModelUsage)
    final_message: str = ""
    stopped_reason: str = "completed"
    fallback_used: bool = False
    actions: tuple[AgentAction, ...] = ()
    warnings: tuple[str, ...] = ()
