from enshittify_profiles.degradation_profile import DegradationProfile

PROFILE = DegradationProfile(
    name="maximum",
    description="Every registered degradation strategy, in a deterministic order.",
    tools=(
        "obfuscate_identifiers",
        "encode_literals",
        "rewrite_control_flow",
        "introduce_indirection",
        "duplicate_logic",
        "extract_trivial_helpers",
        "inline_useful_abstractions",
        "merge_unrelated_modules",
        "split_cohesive_modules",
        "weaken_types",
        "replace_constants_with_magic_values",
        "expand_conditionals",
        "introduce_alias_chains",
        "convert_async_style",
        "inflate_dependencies",
        "spread_configuration",
        "inject_dead_code",
        "degrade_error_handling",
        "degrade_naming",
        "remove_documentation",
        "collapse_formatting",
    ),
)
