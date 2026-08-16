from enshittify_profiles.degradation_profile import DegradationProfile

PROFILE = DegradationProfile(
    name="chaotic",
    description="A broad mixture of noisy structural and source-level degradation.",
    tools=(
        "rewrite_control_flow",
        "duplicate_logic",
        "extract_trivial_helpers",
        "inline_useful_abstractions",
        "introduce_alias_chains",
        "expand_conditionals",
        "inject_dead_code",
        "degrade_error_handling",
        "degrade_naming",
        "encode_literals",
        "inflate_dependencies",
        "collapse_formatting",
    ),
)
