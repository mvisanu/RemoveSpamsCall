"""Auto-mode broker connector skeleton.

Auto-mode is only used for brokers where it is explicitly safe and legally
permitted (auto_supported: true in brokers.yaml).  In all other cases the
assisted connector is used.

The auto connector MUST NOT:
- Bypass CAPTCHAs, paywalls, or authentication systems
- Submit requests without verifiable confirmation
"""

from __future__ import annotations

from privacytool.connectors.brokers.base_broker import BaseBrokerConnector
from privacytool.core.logger import get_logger
from privacytool.core.models import ActionResult, TrackedRecord

log = get_logger(__name__)


class AutoBrokerConnector(BaseBrokerConnector):
    """Automated opt-out for explicitly supported brokers only."""

    mode = "auto"

    def act(self, record: TrackedRecord, dry_run: bool = False) -> ActionResult:
        if not self.entry.auto_supported:
            log.warning(
                "Auto mode requested for %s but auto_supported=false — "
                "falling back to assisted guidance.",
                self.entry.name,
            )
            return ActionResult(
                success=False,
                message=(
                    f"Auto mode is not supported for {self.entry.name}. "
                    f"Please use assisted mode: privacytool act --mode assisted"
                ),
            )

        if dry_run:
            return ActionResult(
                success=True,
                message=f"[DRY-RUN] Would attempt auto opt-out for {self.entry.name}",
                dry_run=True,
            )

        # Placeholder — real implementations would use requests/selenium
        # only for brokers with a documented, CAPTCHA-free API or form.
        log.info("Auto opt-out not yet implemented for %s", self.entry.name)
        return ActionResult(
            success=False,
            message=(
                f"Auto opt-out for {self.entry.name} is declared supported but "
                "implementation is pending. Use assisted mode."
            ),
        )
