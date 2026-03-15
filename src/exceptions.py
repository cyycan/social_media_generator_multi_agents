"""Custom domain exceptions."""


class SocialMediaGeneratorError(Exception):
    """Base exception."""


class ConfigurationError(SocialMediaGeneratorError):
    """Raised when app configuration is invalid or missing."""


class GenerationError(SocialMediaGeneratorError):
    """Raised when LLM post generation fails."""


class DataParsingError(SocialMediaGeneratorError):
    """Raised when uploaded data cannot be parsed."""


class PublishError(SocialMediaGeneratorError):
    """Raised when publishing to a platform fails."""


class APIKeyError(ConfigurationError):
    """Raised when an API key is missing or invalid."""
