"""Unit tests for auto-mode broker connector and webdriver session helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from privacytool.connectors.brokers.auto import AutoBrokerConnector, _normalize
from privacytool.core.models import ActionResult, BrokerEntry, PiiProfile, TrackedRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(**kwargs) -> BrokerEntry:
    defaults = dict(
        id="testbroker",
        name="Test Broker",
        url="https://example.com",
        opt_out_url="https://example.com/optout",
        mode="auto",
        auto_supported=True,
        search_url_template="https://example.com/search?name={first_name}+{last_name}",
        result_selector="a.person",
        form_selector="form#optout",
        form_fields={"email": "input[type='email']", "first_name": "input#fname"},
        submit_selector="button[type='submit']",
        confirmation_strategy="page_text",
        confirmation_text="successfully removed",
        auto_timeout=5,
    )
    defaults.update(kwargs)
    return BrokerEntry(**defaults)


def _make_profile() -> PiiProfile:
    return PiiProfile(
        name="default",
        full_name="Jane Doe",
        emails=["jane@example.com"],
        phones=["+12025550001"],
        addresses=["Springfield, IL"],
        dob="1990-01-15",
    )


def _make_record(entry: BrokerEntry) -> TrackedRecord:
    return TrackedRecord(
        target_type="broker",
        site=entry.id,
        url=entry.opt_out_url,
        action_type="optout",
    )


# ---------------------------------------------------------------------------
# _normalize helper
# ---------------------------------------------------------------------------

def test_normalize_lowercases():
    assert _normalize("Jane") == "jane"


def test_normalize_strips_accents():
    assert _normalize("Hélo") == "helo"


def test_normalize_handles_empty():
    assert _normalize("") == ""


# ---------------------------------------------------------------------------
# AutoBrokerConnector.act — dry_run
# ---------------------------------------------------------------------------

def test_act_dry_run_returns_success():
    entry = _make_entry()
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    record = _make_record(entry)
    result = connector.act(record, dry_run=True)
    assert result.success is True
    assert result.dry_run is True
    assert "DRY-RUN" in result.message


def test_act_dry_run_no_profile_still_succeeds():
    """Dry-run should succeed even without a profile (no real form submission)."""
    entry = _make_entry()
    connector = AutoBrokerConnector(entry, profile=None)
    record = _make_record(entry)
    result = connector.act(record, dry_run=True)
    assert result.success is True


# ---------------------------------------------------------------------------
# AutoBrokerConnector.act — no profile
# ---------------------------------------------------------------------------

def test_act_without_profile_returns_failure():
    entry = _make_entry()
    connector = AutoBrokerConnector(entry, profile=None)
    record = _make_record(entry)
    result = connector.act(record, dry_run=False)
    assert result.success is False
    assert "profile" in result.message.lower()


# ---------------------------------------------------------------------------
# AutoBrokerConnector.act — auto_supported=false fallback
# ---------------------------------------------------------------------------

def test_act_falls_back_when_not_auto_supported():
    entry = _make_entry(auto_supported=False)
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    record = _make_record(entry)
    with patch.object(
        connector,
        "_fallback",
        return_value=ActionResult(success=True, message="assisted"),
    ) as mock_fb:
        result = connector.act(record, dry_run=False)
    mock_fb.assert_called_once()
    assert result.success is True


# ---------------------------------------------------------------------------
# AutoBrokerConnector.act — CAPTCHA fallback
# ---------------------------------------------------------------------------

def test_act_falls_back_on_captcha():
    from privacytool.connectors.brokers.webdriver_session import CaptchaDetected

    entry = _make_entry()
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    record = _make_record(entry)

    with patch.object(connector, "_run_auto", side_effect=CaptchaDetected()), \
         patch.object(connector, "_fallback",
                      return_value=ActionResult(success=True, message="fallback")) as mock_fb:
        result = connector.act(record, dry_run=False)

    mock_fb.assert_called_once()
    assert result.success is True


# ---------------------------------------------------------------------------
# AutoBrokerConnector.act — generic exception fallback
# ---------------------------------------------------------------------------

def test_act_falls_back_on_generic_exception():
    entry = _make_entry()
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    record = _make_record(entry)

    with patch.object(connector, "_run_auto", side_effect=RuntimeError("boom")), \
         patch.object(connector, "_fallback",
                      return_value=ActionResult(success=False, message="fallback")) as mock_fb:
        result = connector.act(record, dry_run=False)

    mock_fb.assert_called_once()
    assert result.success is False


# ---------------------------------------------------------------------------
# AutoBrokerConnector._verify_confirmation — page_text
# ---------------------------------------------------------------------------

def test_verify_confirmation_page_text_match():
    entry = _make_entry(confirmation_strategy="page_text", confirmation_text="successfully removed")
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    driver = MagicMock()
    driver.page_source = "Your record was successfully removed from our database."
    success, cid = connector._verify_confirmation(driver)
    assert success is True
    assert cid == "page-text-match"


def test_verify_confirmation_page_text_no_match():
    entry = _make_entry(confirmation_strategy="page_text", confirmation_text="successfully removed")
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    driver = MagicMock()
    driver.page_source = "An error occurred. Please try again."
    success, cid = connector._verify_confirmation(driver)
    assert success is False
    assert cid == ""


# ---------------------------------------------------------------------------
# AutoBrokerConnector._verify_confirmation — url_change
# ---------------------------------------------------------------------------

def test_verify_confirmation_url_change_detected():
    entry = _make_entry(
        confirmation_strategy="url_change",
        opt_out_url="https://example.com/optout",
    )
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    driver = MagicMock()
    driver.current_url = "https://example.com/confirmation"
    success, cid = connector._verify_confirmation(driver)
    assert success is True
    assert cid == "https://example.com/confirmation"


def test_verify_confirmation_url_no_change():
    entry = _make_entry(
        confirmation_strategy="url_change",
        opt_out_url="https://example.com/optout",
    )
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    driver = MagicMock()
    driver.current_url = "https://example.com/optout"
    success, cid = connector._verify_confirmation(driver)
    assert success is False
    assert cid == ""


# ---------------------------------------------------------------------------
# AutoBrokerConnector._verify_confirmation — element
# ---------------------------------------------------------------------------

def test_verify_confirmation_element_found():
    entry = _make_entry(
        confirmation_strategy="element",
        confirmation_selector=".success-banner",
    )
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    driver = MagicMock()
    # find_element succeeds (does not raise)
    driver.find_element.return_value = MagicMock()
    success, cid = connector._verify_confirmation(driver)
    assert success is True
    assert cid == "element-present"


def test_verify_confirmation_element_not_found():
    from selenium.common.exceptions import NoSuchElementException

    entry = _make_entry(
        confirmation_strategy="element",
        confirmation_selector=".success-banner",
    )
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    driver = MagicMock()
    driver.find_element.side_effect = NoSuchElementException("nope")
    success, cid = connector._verify_confirmation(driver)
    assert success is False
    assert cid == ""


# ---------------------------------------------------------------------------
# AutoBrokerConnector._verify_confirmation — unknown strategy
# ---------------------------------------------------------------------------

def test_verify_confirmation_unknown_strategy():
    entry = _make_entry(confirmation_strategy="magic")
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    driver = MagicMock()
    success, cid = connector._verify_confirmation(driver)
    assert success is False


# ---------------------------------------------------------------------------
# AutoBrokerConnector.discover — dry_run
# ---------------------------------------------------------------------------

def test_discover_dry_run_returns_record():
    entry = _make_entry()
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    records = connector.discover(_make_profile(), dry_run=True)
    assert len(records) == 1
    assert records[0].site == entry.id
    assert records[0].action_type == "optout"


# ---------------------------------------------------------------------------
# AutoBrokerConnector.discover — no search template
# ---------------------------------------------------------------------------

def test_discover_no_search_template_uses_base():
    entry = _make_entry(search_url_template="")
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    with patch(
        "privacytool.connectors.brokers.base_broker.BaseBrokerConnector.discover",
        return_value=[],
    ) as mock_base:
        result = connector.discover(_make_profile(), dry_run=False)
    mock_base.assert_called_once()
    assert result == []


# ---------------------------------------------------------------------------
# AutoBrokerConnector._resolve_selector
# ---------------------------------------------------------------------------

def test_resolve_selector_returns_first_visible():
    entry = _make_entry()
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    driver = MagicMock()
    mock_el = MagicMock()
    mock_el.is_displayed.return_value = True
    driver.find_element.return_value = mock_el
    result = connector._resolve_selector(driver, "input#email, input[name=email]")
    assert result is mock_el


def test_resolve_selector_skips_hidden_element():
    entry = _make_entry()
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    driver = MagicMock()
    mock_el = MagicMock()
    mock_el.is_displayed.return_value = False
    driver.find_element.return_value = mock_el
    result = connector._resolve_selector(driver, "input#hidden")
    assert result is None


def test_resolve_selector_returns_none_on_exception():
    from selenium.common.exceptions import NoSuchElementException

    entry = _make_entry()
    connector = AutoBrokerConnector(entry, profile=_make_profile())
    driver = MagicMock()
    driver.find_element.side_effect = NoSuchElementException("not found")
    result = connector._resolve_selector(driver, "input.missing")
    assert result is None
