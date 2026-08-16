"""Public SDK configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from enshittify_providers import CodxProvider, ModelProvider


@dataclass(frozen=True)
class EnshittifyConfig:
    output_root: Path | None = None
    provider: str | ModelProvider | CodxProvider = "none"
    api_key: str | None = field(default=None, repr=False, compare=False)
    model: str | None = None
    temperature: float = 0.0
    provider_timeout: float = 120.0
    provider_max_retries: int = 2
    provider_max_tokens: int = 8192
    mode: str = "auto"
    allow_llm_rewrites: bool = True
    max_agent_steps: int = 24
    max_agent_read_chars: int = 24_000
    codx_command: str | None = None
    codx_timeout: float = 1_800.0
    codx_yolo: bool = True
