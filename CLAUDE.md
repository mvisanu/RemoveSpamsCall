# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (editable + dev deps)
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/unit/test_crypto.py -v

# Run with coverage
pytest --cov=src/privacytool

# Run the CLI
privacytool --help
privacytool init
privacytool scan --pii-profile default --dry-run
```

## Architecture

**Entry point:** `src/privacytool/cli/main.py` — Typer app that registers all sub-commands from `cmd_*.py` files.

**Three-layer design:**

1. **CLI layer** (`cli/`) — one file per command (`cmd_scan.py`, `cmd_act.py`, etc.), thin orchestration only
2. **Core services** (`core/`) — `config.py` (profile/env), `crypto.py` (PBKDF2+Fernet), `db.py` (SQLite CRUD), `logger.py` (PII-redacting), `runner.py` (rate-limited job runner with tenacity), `models.py` (shared dataclasses), `pii.py` (validation/normalization)
3. **Connectors** (`connectors/`) — plugin pattern via `BaseConnector`; two sub-families:
   - `connectors/engines/` — one file per search engine (Google, Bing, DDG, Yandex, Yahoo)
   - `connectors/brokers/` — driven by `data/brokers.yaml`; `loader.py` instantiates `AssistedBrokerConnector` or `AutoBrokerConnector` per entry

**Key data flow:**
```
scan → connector.discover() → TrackedRecord inserted to DB
review → user accepts/skips records (status: discovered → pending)
act → connector.act() → status updated (pending → submitted/failed)
followups → records where follow_up_due ≤ now and status not terminal
```

**PII security invariants (must never be broken):**
- PII profiles are encrypted at rest using passphrase-derived Fernet key; plaintext only in memory
- All log calls go through `PiiRedactingFilter` — never log raw emails/phones
- URLs in the DB are SHA-256 hashed, not stored in plaintext
- `.env` and `profiles/` are gitignored; never commit them
- Auto connectors must never bypass CAPTCHAs or auth — default to `assisted` mode

**Letter generation:** `letters/generator.py` uses Jinja2 templates from `templates/letters/` and ReportLab for PDF output.

**Dashboard:** `dashboard/views.py` — Rich tables and progress bars; status colors defined in `_STATUS_COLORS`.

**DB schema:** Single `records` table with status lifecycle: `discovered → pending → submitted → confirmed → resolved` (or `failed`). Follow-up due date is set to `discovered_on + 30 days`.

**Adding a new search engine connector:** Subclass `BaseConnector`, implement `discover()` and `act()`, register in `cmd_scan.py` and `cmd_act.py`.

**Adding a new data broker:** Add an entry to `data/brokers.yaml` — no code changes needed.
