"""Built-in degradation profile registry."""

from __future__ import annotations

from enshittify_profiles.builtins.degradation.chaotic import PROFILE as CHAOTIC
from enshittify_profiles.builtins.degradation.dependency_bloat import (
    PROFILE as DEPENDENCY_BLOAT,
)
from enshittify_profiles.builtins.degradation.enterprise import PROFILE as ENTERPRISE
from enshittify_profiles.builtins.degradation.maximum import PROFILE as MAXIMUM
from enshittify_profiles.builtins.degradation.obfuscation_heavy import (
    PROFILE as OBFUSCATION_HEAVY,
)
from enshittify_profiles.builtins.degradation.subtle import PROFILE as SUBTLE
from enshittify_profiles.degradation_profile import DegradationProfile

PROFILES = {
    profile.name: profile
    for profile in (
        SUBTLE,
        OBFUSCATION_HEAVY,
        ENTERPRISE,
        DEPENDENCY_BLOAT,
        CHAOTIC,
        MAXIMUM,
    )
}

ALIASES = {
    "enterprise": "enterprise-sprawl",
    "max": "maximum",
    "obfuscation": "obfuscation-heavy",
}


def list_profiles() -> list[DegradationProfile]:
    return list(PROFILES.values())


def get_profile(name: str) -> DegradationProfile:
    resolved_name = ALIASES.get(name, name)
    try:
        return PROFILES[resolved_name]
    except KeyError as error:
        choices = ", ".join(PROFILES)
        raise ValueError(
            f"Unknown profile `{name}`. Choose from: {choices}."
        ) from error
