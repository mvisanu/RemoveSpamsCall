"""Unit tests for PII redaction in log output."""

from privacytool.core.logger import _redact


def test_redacts_email():
    assert "[REDACTED]" in _redact("Contact user@example.com for info")
    assert "user@example.com" not in _redact("Contact user@example.com")


def test_redacts_phone():
    result = _redact("Call +18005551234 now")
    assert "+18005551234" not in result
    assert "[REDACTED]" in result


def test_passes_safe_text():
    safe = "Scanning site whitepages - no PII here"
    assert _redact(safe) == safe


def test_multiple_redactions():
    text = "Email: test@test.com Phone: +18005551234"
    result = _redact(text)
    assert "test@test.com" not in result
    assert "+18005551234" not in result
    assert result.count("[REDACTED]") >= 2
