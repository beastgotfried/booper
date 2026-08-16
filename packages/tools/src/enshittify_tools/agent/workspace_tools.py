"""LangChain tool definitions bound to one isolated workspace session."""

from __future__ import annotations

from langchain.tools import BaseTool, tool
from pydantic import BaseModel, ConfigDict, Field

from enshittify_tools.agent.session import AgentWorkspaceSession


class ReadSourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="Exact relative path from inspect_workspace.")


class ApplyMutationInput(ReadSourceInput):
    mutation: str = Field(description="Exact mutation name from available_mutations.")
    rationale: str = Field(
        default="",
        description="Short reason this mutation makes the selected file harder to maintain.",
    )


class RewriteSourceInput(ReadSourceInput):
    code: str = Field(
        description="Complete replacement Python source without Markdown fences."
    )
    rationale: str = Field(
        description="Short explanation of the targeted degradation strategy."
    )


class ReviewDiffInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str | None = Field(
        default=None,
        description="Optional exact candidate path; omit to review all changed files.",
    )


def build_workspace_tools(session: AgentWorkspaceSession) -> list[BaseTool]:
    """Build the minimal tool surface exposed to the coding agent."""

    @tool
    def inspect_workspace() -> str:
        """Inspect eligible files, repository metadata, budget, and available mutations."""
        return session.inspect_workspace()

    @tool(args_schema=ReadSourceInput)
    def read_source(path: str) -> str:
        """Read one eligible Python file before choosing a targeted mutation or rewrite."""
        return session.read_source(path)

    @tool(args_schema=ApplyMutationInput)
    def apply_mutation(path: str, mutation: str, rationale: str = "") -> str:
        """Apply one allowlisted deterministic mutation to one eligible source file."""
        return session.apply_mutation(path, mutation, rationale)

    @tool(args_schema=RewriteSourceInput)
    def rewrite_source(path: str, code: str, rationale: str) -> str:
        """Replace one file with targeted Python that is size-limited and syntax-validated."""
        return session.rewrite_source(path, code, rationale)

    @tool(args_schema=ReviewDiffInput)
    def review_diff(path: str | None = None) -> str:
        """Review the accumulated unified diff, or the dry-run action plan, before finishing."""
        return session.review_diff(path)

    return [inspect_workspace, read_source, apply_mutation, rewrite_source, review_diff]
