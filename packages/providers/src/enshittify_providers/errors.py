"""Provider configuration and runtime errors."""


class ProviderError(RuntimeError):
    """Base error for model-provider failures."""


class ProviderConfigurationError(ValueError, ProviderError):
    """Raised when a provider cannot be configured securely."""


class ProviderDependencyError(ProviderConfigurationError):
    """Raised when an optional provider integration is unavailable."""
