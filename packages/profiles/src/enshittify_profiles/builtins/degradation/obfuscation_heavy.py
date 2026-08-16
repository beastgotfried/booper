from enshittify_profiles.degradation_profile import DegradationProfile

PROFILE = DegradationProfile(
    name="obfuscation-heavy",
    description="Identifier, literal, formatting, documentation, and control-flow obfuscation.",
    tools=(
        "obfuscate_identifiers",
        "encode_literals",
        "replace_constants_with_magic_values",
        "rewrite_control_flow",
        "introduce_alias_chains",
        "remove_documentation",
        "collapse_formatting",
    ),
)
