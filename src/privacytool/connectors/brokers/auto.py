"""Auto-mode broker connector — headless Chrome form submission.

Only used for brokers where auto_supported=true in brokers.yaml.
Falls back to assisted mode on any CAPTCHA, missing element, or error.

Security constraints (SECURITY.md):
  - NEVER bypass CAPTCHAs — detect and fall back.
  - NEVER claim success without a verifiable confirmation.
  - NEVER store or log PII.
"""

from __future__ import annotations

import unicodedata
from datetime import datetime

from privacytool.connectors.brokers.base_broker import BaseBrokerConnector
from privacytool.connectors.brokers.webdriver_session import (
    CaptchaDetected,
    detect_captcha,
    get_driver,
)
from privacytool.core.logger import get_logger
from privacytool.core.models import ActionResult, BrokerEntry, PiiProfile, TrackedRecord

log = get_logger(__name__)


class AutoBrokerConnector(BaseBrokerConnector):
    """Automated opt-out using headless Chrome.  Falls back to assisted on CAPTCHA."""

    mode = "auto"

    def __init__(self, entry: BrokerEntry, profile: PiiProfile | None = None) -> None:
        super().__init__(entry)
        self._profile = profile

    # ------------------------------------------------------------------
    # discover() — find the user's actual listing URL on the broker site
    # ------------------------------------------------------------------

    def discover(self, profile: PiiProfile, dry_run: bool = False) -> list[TrackedRecord]:
        """Try to find the user's listing on the broker site."""
        self._profile = profile

        if not self.entry.search_url_template:
            # No search template — fall back to base class (opt_out_url)
            return super().discover(profile, dry_run)

        if dry_run:
            log.info("[DRY-RUN] Would search %s for listing", self.entry.name)
            return super().discover(profile, dry_run)

        try:
            listing_url = self._find_listing(profile)
            url = listing_url or self.entry.opt_out_url
            return [
                TrackedRecord(
                    target_type="broker",
                    site=self.entry.id,
                    url=url,
                    action_type="optout",
                    discovered_on=datetime.utcnow().isoformat(timespec="seconds"),
                    notes=f"Auto-discovered | broker={self.entry.name}",
                )
            ]
        except CaptchaDetected:
            log.warning("CAPTCHA on %s during discover — using opt_out_url", self.entry.name)
            return super().discover(profile, dry_run)
        except Exception as exc:
            log.warning("Auto-discover failed for %s: %s", self.entry.name, exc)
            return super().discover(profile, dry_run)

    # ------------------------------------------------------------------
    # act() — fill and submit the opt-out form
    # ------------------------------------------------------------------

    def act(self, record: TrackedRecord, dry_run: bool = False) -> ActionResult:
        if not self.entry.auto_supported:
            log.warning(
                "Auto mode requested for %s but auto_supported=false — falling back.",
                self.entry.name,
            )
            return self._fallback(record, dry_run)

        if dry_run:
            return ActionResult(
                success=True,
                message=f"[DRY-RUN] Would auto opt-out for {self.entry.name}",
                dry_run=True,
            )

        if self._profile is None:
            return ActionResult(
                success=False,
                message="No PII profile loaded — cannot fill opt-out form.",
            )

        try:
            return self._run_auto(record)
        except CaptchaDetected:
            log.warning("CAPTCHA detected on %s — falling back to assisted", self.entry.name)
            return self._fallback(record, dry_run)
        except Exception as exc:
            log.warning("Auto opt-out failed for %s: %s", self.entry.name, exc)
            return self._fallback(record, dry_run)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_auto(self, record: TrackedRecord) -> ActionResult:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        driver = get_driver()
        timeout = self.entry.auto_timeout
        target_url = record.url or self.entry.opt_out_url

        # Navigate
        driver.get(target_url)
        if detect_captcha(driver):
            raise CaptchaDetected()

        # If we landed on a listing page and need to click through to the form
        if self.entry.result_selector and self.entry.form_selector:
            try:
                btn = WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, self.entry.result_selector))
                )
                btn.click()
                if detect_captcha(driver):
                    raise CaptchaDetected()
            except CaptchaDetected:
                raise
            except Exception:
                pass  # may already be on the form page

        # Wait for form
        if self.entry.form_selector:
            try:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.entry.form_selector)
                    )
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Form not found on {self.entry.name} ({self.entry.form_selector})"
                ) from exc

        # Fill form fields
        self._fill_form(driver)

        if detect_captcha(driver):
            raise CaptchaDetected()

        # Submit
        submit_el = self._resolve_selector(driver, self.entry.submit_selector)
        if submit_el is None:
            raise RuntimeError(f"Submit button not found on {self.entry.name}")
        submit_el.click()

        # Wait briefly for response
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass

        if detect_captcha(driver):
            raise CaptchaDetected()

        success, confirmation_id = self._verify_confirmation(driver)
        return ActionResult(
            success=success,
            confirmation_id=confirmation_id,
            message=(
                f"Auto opt-out {'succeeded' if success else 'could not be verified'} "
                f"for {self.entry.name}"
            ),
        )

    def _find_listing(self, profile: PiiProfile) -> str | None:
        """Navigate to search_url_template and look for a listing matching the profile."""
        from selenium.webdriver.common.by import By

        # Build first/last name
        parts = profile.full_name.split()
        first = parts[0] if parts else ""
        last = parts[-1] if len(parts) > 1 else ""
        city = profile.addresses[0].split(",")[0].strip() if profile.addresses else ""
        state = profile.addresses[0].split(",")[1].strip()[:2] if profile.addresses and "," in profile.addresses[0] else ""

        url = (
            self.entry.search_url_template
            .replace("{first_name}", first)
            .replace("{last_name}", last)
            .replace("{city}", city)
            .replace("{state}", state)
        )

        driver = get_driver()
        driver.get(url)
        if detect_captcha(driver):
            raise CaptchaDetected()

        if not self.entry.result_selector:
            return None

        try:
            elements = driver.find_elements(By.CSS_SELECTOR, self.entry.result_selector)
            for el in elements:
                text = _normalize(el.text)
                if _normalize(profile.full_name) in text:
                    href = el.get_attribute("href")
                    return href or None
        except Exception:
            pass
        return None

    def _fill_form(self, driver) -> None:
        from selenium.webdriver.support.ui import Select

        profile = self._profile
        if profile is None:
            return

        parts = profile.full_name.split()
        first = parts[0] if parts else ""
        last = parts[-1] if len(parts) > 1 else ""
        city = profile.addresses[0].split(",")[0].strip() if profile.addresses else ""
        state = (
            profile.addresses[0].split(",")[1].strip()[:2]
            if profile.addresses and "," in profile.addresses[0]
            else ""
        )

        value_map = {
            "first_name": first,
            "last_name": last,
            "email": profile.emails[0] if profile.emails else "",
            "city": city,
            "state": state,
            "address": profile.addresses[0] if profile.addresses else "",
            "phone": profile.phones[0] if profile.phones else "",
            "dob": profile.dob,
            "full_name": profile.full_name,
        }

        for purpose, selector_chain in self.entry.form_fields.items():
            value = value_map.get(purpose, "")
            if not value:
                continue
            el = self._resolve_selector(driver, selector_chain)
            if el is None:
                log.warning("Field '%s' not found on %s — skipping", purpose, self.entry.name)
                continue
            try:
                if el.tag_name == "select":
                    sel = Select(el)
                    try:
                        sel.select_by_visible_text(value)
                    except Exception:
                        # Try partial match
                        for opt in sel.options:
                            if value.lower() in opt.text.lower():
                                sel.select_by_visible_text(opt.text)
                                break
                else:
                    el.clear()
                    el.send_keys(value)
            except Exception as exc:
                log.warning("Could not fill field '%s' on %s: %s", purpose, self.entry.name, exc)

    def _resolve_selector(self, driver, selector_chain: str):
        """Try each comma-separated CSS selector in order; return first matching element."""
        from selenium.webdriver.common.by import By

        for selector in selector_chain.split(","):
            selector = selector.strip()
            if not selector:
                continue
            try:
                el = driver.find_element(By.CSS_SELECTOR, selector)
                if el.is_displayed():
                    return el
            except Exception:
                continue
        return None

    def _verify_confirmation(self, driver) -> tuple[bool, str]:
        strategy = self.entry.confirmation_strategy

        if strategy == "page_text":
            text = self.entry.confirmation_text.lower()
            if text and text in driver.page_source.lower():
                return True, "page-text-match"
            return False, ""

        if strategy == "url_change":
            changed = driver.current_url.rstrip("/") != self.entry.opt_out_url.rstrip("/")
            return changed, driver.current_url if changed else ""

        if strategy == "element":
            from selenium.webdriver.common.by import By
            try:
                driver.find_element(By.CSS_SELECTOR, self.entry.confirmation_selector)
                return True, "element-present"
            except Exception:
                return False, ""

        return False, ""

    def _fallback(self, record: TrackedRecord, dry_run: bool) -> ActionResult:
        from privacytool.connectors.brokers.assisted import AssistedBrokerConnector
        return AssistedBrokerConnector(self.entry).act(record, dry_run)


def _normalize(text: str) -> str:
    """Lowercase and strip accents for fuzzy name matching."""
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode().lower()
