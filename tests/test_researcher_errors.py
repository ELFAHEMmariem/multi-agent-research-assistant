
from app.tools.search import classify_tool_error


class FakeRateLimitError(Exception):
    status_code = 429


class FakeTimeoutError(TimeoutError):
    pass


def test_rate_limit_classification():
    error = FakeRateLimitError("Too many requests")

    assert classify_tool_error(error) == "rate_limited"


def test_timeout_classification():
    error = FakeTimeoutError("Request timed out")

    assert classify_tool_error(error) == "timeout"


def test_unknown_error():
    error = RuntimeError("Unexpected failure")

    assert classify_tool_error(error) == "error"
