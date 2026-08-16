"""Model-provider capability metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCapabilities:
    tool_calling: bool = True
    structured_output: bool = False
    token_usage: bool = True

    def names(self) -> tuple[str, ...]:
        enabled = []
        if self.tool_calling:
            enabled.append("tool_calling")
        if self.structured_output:
            enabled.append("structured_output")
        if self.token_usage:
            enabled.append("token_usage")
        return tuple(enabled)
