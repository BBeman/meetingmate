from fastapi import status


class MeetingMateException(Exception):
    """Base exception for all MeetingMate errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(MeetingMateException):
    """Raised when authentication fails (invalid credentials, expired token, etc)."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(MeetingMateException):
    """Raised when user lacks permission for a resource."""

    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class NotFoundError(MeetingMateException):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", status.HTTP_404_NOT_FOUND)


class ConflictError(MeetingMateException):
    """Raised when a resource already exists (duplicate email, etc)."""

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status.HTTP_409_CONFLICT)


class ValidationError(MeetingMateException):
    """Raised when input validation fails beyond Pydantic checks."""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, 422)


class ExternalServiceError(MeetingMateException):
    """Raised when an external API call fails (Anthropic, Voyage, etc)."""

    def __init__(self, service: str, message: str = "Service unavailable"):
        super().__init__(f"{service}: {message}", status.HTTP_503_SERVICE_UNAVAILABLE)


class DatabaseError(MeetingMateException):
    """Raised when a database operation fails unexpectedly."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)


class RateLimitError(MeetingMateException):
    """Raised when rate limits are exceeded."""

    def __init__(self, message: str = "Too many requests"):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS)


class AgentError(MeetingMateException):
    """Raised when the agent loop fails to complete."""

    def __init__(self, message: str = "Agent failed to process request"):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)
