"""Headless Chrome session manager with CAPTCHA detection.

A single driver is reused across all auto-mode broker connectors in one
CLI invocation.  Call quit_driver() in a finally block after run_act().

CAPTCHA policy (SECURITY.md):
  - We detect CAPTCHAs and raise CaptchaDetected.
  - We never attempt to solve or bypass them.
  - On detection the connector falls back to assisted mode.
"""

from __future__ import annotations

from privacytool.core.logger import get_logger

log = get_logger(__name__)

_driver = None

_CAPTCHA_SIGNALS = [
    "recaptcha",
    "hcaptcha",
    "cf-turnstile",
    "captcha",
    "i am not a robot",
    "are you a human",
    "challenge-form",
    "ray id",              # Cloudflare block page
    "please verify you are a human",
    "ddos-guard",
]


class CaptchaDetected(Exception):
    """Raised when a CAPTCHA or bot-challenge is found on the current page."""


def get_driver():
    """Return a process-level headless Chrome WebDriver (lazy singleton)."""
    global _driver
    if _driver is not None:
        return _driver

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError as exc:
        raise ImportError(
            "selenium and webdriver-manager are required for auto mode. "
            "Run: pip install -e '.[dev]'"
        ) from exc

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    _driver = webdriver.Chrome(service=service, options=opts)
    _driver.set_page_load_timeout(30)
    log.info("Headless Chrome started")
    return _driver


def quit_driver() -> None:
    """Quit and release the shared WebDriver if it was started."""
    global _driver
    if _driver is not None:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None
        log.info("Headless Chrome stopped")


def detect_captcha(driver) -> bool:
    """Return True if any CAPTCHA / bot-challenge signal is found on the current page."""
    try:
        page_lower = driver.page_source.lower()
        for signal in _CAPTCHA_SIGNALS:
            if signal in page_lower:
                return True
        from selenium.webdriver.common.by import By
        for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
            src = (iframe.get_attribute("src") or "").lower()
            if any(s in src for s in ("recaptcha", "hcaptcha", "turnstile")):
                return True
    except Exception:
        pass
    return False
