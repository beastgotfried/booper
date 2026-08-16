"""Provider-neutral model metadata and usage contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelUsage(BaseModel):
    """Aggregated token usage from one harness run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)

    def plus(self, other: ModelUsage) -> ModelUsage:
        input_tokens = self.input_tokens + other.input_tokens
        output_tokens = self.output_tokens + other.output_tokens
        total_tokens = self.total_tokens + other.total_tokens
        return ModelUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens or input_tokens + output_tokens,
        )


class ProviderDescriptor(BaseModel):
    """Safe provider metadata suitable for reports and logs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    model: str = Field(min_length=1)
    capabilities: tuple[str, ...] = ()
