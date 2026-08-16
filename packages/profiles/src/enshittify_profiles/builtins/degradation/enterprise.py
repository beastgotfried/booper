from enshittify_profiles.degradation_profile import DegradationProfile

PROFILE = DegradationProfile(
    name="enterprise-sprawl",
    description="Indirection, configuration sprawl, weakened types, and architecture theater.",
    tools=(
        "introduce_indirection",
        "extract_trivial_helpers",
        "introduce_alias_chains",
        "spread_configuration",
        "weaken_types",
        "merge_unrelated_modules",
        "split_cohesive_modules",
        "degrade_error_handling",
        "inflate_dependencies",
        "duplicate_logic",
    ),
)
