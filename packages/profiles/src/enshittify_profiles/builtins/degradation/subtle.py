from enshittify_profiles.degradation_profile import DegradationProfile

PROFILE = DegradationProfile(
    name="subtle",
    description="Small, plausibly deniable readability and maintenance regressions.",
    tools=(
        "degrade_naming",
        "expand_conditionals",
        "remove_documentation",
        "inject_dead_code",
    ),
)
