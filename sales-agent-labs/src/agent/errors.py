class AgentError(Exception):
    """Base class for all agent-related errors."""

    pass


class ExternalAPIError(AgentError):
    """Raised when an external API returns an error."""

    pass


class DataShapeError(AgentError):
    """Raised when the data shape from an API is not as expected or JSON is missing required fields."""

    pass
