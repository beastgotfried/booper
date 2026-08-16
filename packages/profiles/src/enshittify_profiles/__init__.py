"""Named mutation strategies."""

from enshittify_profiles.degradation_profile import DegradationProfile
from enshittify_profiles.registry import get_profile, list_profiles

__all__ = ["DegradationProfile", "get_profile", "list_profiles"]
