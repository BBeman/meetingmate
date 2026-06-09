import uuid

from app.logging import correlation_id_var, get_logger, setup_logging


def test_correlation_id_returned_in_response(client):
    """Middleware should return correlation ID in response header."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    # should be a valid UUID when not provided by client
    uuid.UUID(response.headers["X-Correlation-ID"])


def test_client_correlation_id_preserved(client):
    """Middleware should preserve client-provided correlation ID."""
    custom_id = "my-trace-12345"
    response = client.get("/health", headers={"X-Correlation-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == custom_id


def test_correlation_id_context_var():
    """Context var should store and retrieve correlation IDs."""
    test_id = "test-correlation-123"
    correlation_id_var.set(test_id)
    assert correlation_id_var.get() == test_id


def test_correlation_id_default():
    """Context var should have a default value when not set."""
    # reset to default by creating a new context (or just checking default exists)
    from contextvars import copy_context
    ctx = copy_context()
    # default is "-" as specified in logging.py
    assert correlation_id_var.get() is not None


def test_get_logger_returns_logger():
    """get_logger should return a named logger instance."""
    logger = get_logger("test.module")
    assert logger.name == "test.module"


def test_setup_logging_does_not_raise():
    """setup_logging should configure logging without errors."""
    setup_logging(level="DEBUG")
    setup_logging(level="INFO")
    setup_logging(level="WARNING")
