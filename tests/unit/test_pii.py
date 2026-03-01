"""Unit tests for PII validation and normalisation."""

from privacytool.core.pii import normalize_phone, parse_comma_list, validate_email, pii_env_to_dict


def test_valid_emails():
    assert validate_email("user@example.com")
    assert validate_email("user+tag@sub.domain.org")


def test_invalid_emails():
    assert not validate_email("not-an-email")
    assert not validate_email("@nodomain.com")
    assert not validate_email("user@")


def test_normalize_phone_e164():
    assert normalize_phone("+18005551234") == "+18005551234"
    assert normalize_phone("800-555-1234") == "+18005551234"
    assert normalize_phone("(800) 555-1234") == "+18005551234"


def test_normalize_phone_invalid():
    assert normalize_phone("not-a-phone") is None
    assert normalize_phone("123") is None


def test_parse_comma_list():
    assert parse_comma_list("a, b, c") == ["a", "b", "c"]
    assert parse_comma_list("") == []
    assert parse_comma_list("single") == ["single"]


def test_pii_env_to_dict():
    raw = '''
FULL_NAME="Jane Doe"
EMAILS="jane@example.com,jane2@example.com"
# comment line
PHONES="+18005551234"
DOB=""
'''
    result = pii_env_to_dict(raw)
    assert result["FULL_NAME"] == "Jane Doe"
    assert result["EMAILS"] == "jane@example.com,jane2@example.com"
    assert result["DOB"] == ""
