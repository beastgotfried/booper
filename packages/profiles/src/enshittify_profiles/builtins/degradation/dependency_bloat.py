from enshittify_profiles.degradation_profile import DegradationProfile

PROFILE = DegradationProfile(
    name="dependency-bloat",
    description="Import inflation and supporting maintenance noise.",
    tools=(
        "inflate_dependencies",
        "introduce_indirection",
        "duplicate_logic",
        "inject_dead_code",
    ),
)
