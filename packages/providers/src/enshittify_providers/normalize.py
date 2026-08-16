"""Provider-name normalization."""

import re

PROVIDER_ALIASES = {
    "disabled": "none",
    "groqcloud": "groq",
    "off": "none",
}


def normalize_provider_name(name: str) -> str:
    normalized = name.strip().lower().replace("_", "-")
    return PROVIDER_ALIASES.get(normalized, normalized)


_SECRET_PATTERNS = (
    re.compile(r"\bgsk_[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
)


def redact_provider_text(value: str) -> str:
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted
