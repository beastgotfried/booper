"""Shared protocol contracts."""

from enshittify_protocol.contracts.harness import AgentAction, AgentRunSummary
from enshittify_protocol.contracts.model import ModelUsage, ProviderDescriptor

__all__ = [
    "AgentAction",
    "AgentRunSummary",
    "ModelUsage",
    "ProviderDescriptor",
]
