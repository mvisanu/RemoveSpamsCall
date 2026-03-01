"""Load brokers.yaml and instantiate the appropriate connector for each entry."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml

from privacytool.connectors.brokers.assisted import AssistedBrokerConnector
from privacytool.connectors.brokers.auto import AutoBrokerConnector
from privacytool.connectors.brokers.base_broker import BaseBrokerConnector
from privacytool.core.models import BrokerEntry, PiiProfile

_DEFAULT_YAML = Path(__file__).parents[4] / "data" / "brokers.yaml"


def load_brokers(
    yaml_path: str | Path = _DEFAULT_YAML,
    mode_override: Literal["assisted", "auto"] | None = None,
    profile: PiiProfile | None = None,
) -> list[BaseBrokerConnector]:
    """Return a list of broker connectors instantiated from *yaml_path*."""
    path = Path(yaml_path)
    if not path.exists():
        return []

    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or []

    connectors: list[BaseBrokerConnector] = []
    for item in raw:
        entry = BrokerEntry(
            id=item["id"],
            name=item["name"],
            url=item.get("url", ""),
            opt_out_url=item.get("opt_out_url", ""),
            mode=item.get("mode", "assisted"),
            steps=item.get("steps", []),
            auto_supported=item.get("auto_supported", False),
            jurisdiction=item.get("jurisdiction", "US"),
            category=item.get("category", "people-search"),
            notes=item.get("notes", ""),
            search_url_template=item.get("search_url_template", ""),
            result_selector=item.get("result_selector", ""),
            form_selector=item.get("form_selector", ""),
            form_fields=item.get("form_fields", {}),
            submit_selector=item.get("submit_selector", ""),
            confirmation_selector=item.get("confirmation_selector", ""),
            confirmation_strategy=item.get("confirmation_strategy", "page_text"),
            confirmation_text=item.get("confirmation_text", ""),
            auto_timeout=item.get("auto_timeout", 15),
        )
        effective_mode = mode_override or entry.mode
        if effective_mode == "auto" and entry.auto_supported:
            connectors.append(AutoBrokerConnector(entry, profile=profile))
        else:
            connectors.append(AssistedBrokerConnector(entry))

    return connectors
