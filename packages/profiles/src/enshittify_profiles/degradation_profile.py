"""Degradation profile contracts."""

from __future__ import annotations

import math
from dataclasses import dataclass

INTENSITY_FRACTIONS = {
    "low": 0.25,
    "medium": 0.5,
    "high": 0.75,
    "maximum": 1.0,
}


@dataclass(frozen=True)
class DegradationProfile:
    name: str
    description: str
    tools: tuple[str, ...]

    def select_tools(self, intensity: str = "high") -> list[str]:
        try:
            fraction = INTENSITY_FRACTIONS[intensity]
        except KeyError as error:
            choices = ", ".join(INTENSITY_FRACTIONS)
            raise ValueError(
                f"Unknown intensity `{intensity}`. Choose from: {choices}."
            ) from error
        if not self.tools:
            return []
        count = max(1, math.ceil(len(self.tools) * fraction))
        return list(self.tools[:count])
