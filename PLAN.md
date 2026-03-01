# PLAN.md — Privacy Tool Implementation Plan

## 1. Architecture Overview

The tool is a Python CLI application (`privacytool`) that helps individuals discover and remove their personal information from the internet. It operates entirely locally — no PII ever leaves the machine except as part of user-initiated removal requests.

Three primary subsystems:

```
┌─────────────────────────────────────────────────────┐
│                   CLI Layer (Typer)                  │
│  init | config | scan | review | act | status | ...  │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│               Core Services                          │
│  Config/Crypto | Job Runner | DB | Logger | Letters  │
└──────┬──────────────────────────────────┬───────────┘
       │                                  │
┌──────▼──────┐                  ┌────────▼────────────┐
│  Connectors │                  │   Templates / PDF    │
│  (plugins)  │                  │   (Jinja2+ReportLab) │
│  Engines    │                  └─────────────────────┘
│  Brokers    │
└─────────────┘
```

All PII is encrypted at rest using a passphrase-derived key (PBKDF2-HMAC-SHA256 → Fernet). API keys live in `.env`. PII profiles live in `profiles/*.pii.enc` (encrypted).

---

## 2. Module Structure

```
src/privacytool/
├── __init__.py
├── cli/
│   ├── __init__.py
│   ├── main.py          # Typer app root, command registration
│   ├── cmd_init.py      # `privacytool init` wizard
│   ├── cmd_config.py    # `privacytool config set|use-profile`
│   ├── cmd_scan.py      # `privacytool scan`
│   ├── cmd_review.py    # `privacytool review`
│   ├── cmd_act.py       # `privacytool act`
│   ├── cmd_status.py    # `privacytool status`
│   ├── cmd_resolve.py   # `privacytool resolve`
│   ├── cmd_followups.py # `privacytool followups`
│   └── cmd_export.py    # `privacytool export`
├── core/
│   ├── __init__.py
│   ├── config.py        # App config, .env loading, profile management
│   ├── crypto.py        # PBKDF2 key derivation, Fernet encrypt/decrypt
│   ├── db.py            # SQLite schema, CRUD helpers
│   ├── logger.py        # Structured logging, PII redactor
│   ├── models.py        # Dataclasses: PiiProfile, TrackedRecord, BrokerEntry
│   ├── pii.py           # PII validation, email validation, E.164 normalization
│   └── runner.py        # Job runner with rate limiting (tenacity) + dry-run
├── connectors/
│   ├── __init__.py
│   ├── base.py          # Abstract BaseConnector
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── google.py    # SerpAPI + Google Custom Search
│   │   ├── bing.py      # Bing search via requests
│   │   ├── duckduckgo.py
│   │   ├── yandex.py
│   │   └── yahoo.py
│   └── brokers/
│       ├── __init__.py
│       ├── loader.py    # Loads brokers.yaml, instantiates connectors
│       ├── base_broker.py
│       ├── assisted.py  # Generic assisted-mode workflow
│       └── auto.py      # Generic auto-mode skeleton (safe only)
├── letters/
│   ├── __init__.py
│   └── generator.py     # Jinja2 render + ReportLab PDF output
└── dashboard/
    ├── __init__.py
    └── views.py         # Rich tables, follow-up alerts, progress bars
```

---

## 3. SQLite Data Model / Schema

Database file: `~/.privacytool/tracker.db` (or `$PRIVACYTOOL_DB_PATH`).

```sql
CREATE TABLE IF NOT EXISTS records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type     TEXT NOT NULL,          -- 'engine' | 'broker' | 'letter'
    site            TEXT NOT NULL,          -- e.g. 'google', 'whitepages'
    url             TEXT,                   -- discovered URL (hashed if PII present)
    discovered_on   TEXT NOT NULL,          -- ISO-8601 datetime
    action_type     TEXT,                   -- 'deindex' | 'optout' | 'letter'
    status          TEXT NOT NULL DEFAULT 'discovered',
                                            -- discovered|pending|submitted|confirmed|resolved|failed
    confirmation_id TEXT,                   -- opaque confirmation token
    last_attempt    TEXT,                   -- ISO-8601 datetime
    follow_up_due   TEXT,                   -- ISO-8601 datetime (discovered_on + 30 days)
    follow_up_count INTEGER NOT NULL DEFAULT 0,
    notes           TEXT                    -- freeform, never contains plaintext PII
);

CREATE INDEX IF NOT EXISTS idx_status ON records(status);
CREATE INDEX IF NOT EXISTS idx_follow_up_due ON records(follow_up_due);
CREATE INDEX IF NOT EXISTS idx_site ON records(site);
```

Status lifecycle:
```
discovered → pending → submitted → confirmed → resolved
                   ↘ failed ↗
```

---

## 4. Connector / Plugin Pattern

Every connector (engine or broker) inherits from `BaseConnector`:

```python
class BaseConnector(ABC):
    name: str
    mode: Literal["assisted", "auto"]

    @abstractmethod
    def discover(self, profile: PiiProfile, dry_run: bool) -> list[TrackedRecord]: ...

    @abstractmethod
    def act(self, record: TrackedRecord, dry_run: bool) -> ActionResult: ...
```

**Engine connectors** use SerpAPI or raw HTTP requests to search for PII and return `TrackedRecord` instances.

**Broker connectors** are driven by entries in `data/brokers.yaml`:

```yaml
- id: whitepages
  name: Whitepages
  url: https://www.whitepages.com
  opt_out_url: https://www.whitepages.com/suppression_requests/new
  mode: assisted
  steps:
    - "Go to opt_out_url"
    - "Search for your name and location"
    - "Click 'Remove me'"
    - "Confirm via email"
  auto_supported: false
  jurisdiction: US
  category: people-search
```

The `loader.py` reads the YAML and wires up either `AssistedBrokerConnector` or `AutoBrokerConnector` depending on `mode` and `auto_supported`.

---

## 5. CLI Command Flow

```
privacytool init
  └─► Prompt passphrase → derive key → create ~/.privacytool/
      → prompt PII fields → encrypt & write profiles/default.pii.enc
      → write skeleton .env

privacytool scan --pii-profile default
  └─► Decrypt profile → load PII → run all engine connectors (rate-limited)
      → run broker discovery → write TrackedRecords to DB
      → show Rich summary table

privacytool review
  └─► Query DB for status='discovered' → interactive Rich table
      → user can mark skip/accept per record

privacytool act --target engine --mode assisted
  └─► Query DB for accepted records → run connector.act()
      → in dry-run: log actions, skip submission
      → update status in DB

privacytool status
  └─► Rich table: all records, status colors, follow-up countdown

privacytool resolve --id <id>
  └─► Update record status to 'resolved'

privacytool followups
  └─► Query WHERE follow_up_due <= now() AND status NOT IN ('resolved','confirmed')

privacytool export --format csv|json
  └─► Dump all records, PII fields excluded/hashed
```

---

## 6. Security Design

### Encryption

- Master passphrase → PBKDF2-HMAC-SHA256 (600 000 iterations, random 16-byte salt) → 32-byte key
- Key wrapped in `cryptography.fernet.Fernet`
- Salt stored alongside ciphertext in `profiles/*.pii.enc`: `salt(16) + iv(16) + ciphertext`
- Passphrase never stored on disk; prompted at startup or cached in-process only

### PII Handling

- `PiiProfile` dataclass holds decrypted PII **in memory only**
- All log calls pass through `PiiRedactor` — a regex-based filter that replaces emails, phones, addresses with `[REDACTED]`
- Database stores URLs as SHA-256 hashes when they contain PII; human-readable form shown only during interactive `review`
- `--show-pii` flag prompts an explicit "Are you sure?" confirmation before revealing any PII in terminal output

### OS Keychain (optional)

- If `keyring` library is available, master key can be stored in OS keychain after first unlock (opt-in during `init`)

### .gitignore requirements

```
.env
profiles/
*.pii.enc
*.pii.env
~/.privacytool/
__pycache__/
*.pyc
.pytest_cache/
dist/
*.egg-info/
```

---

## 7. Risk & Compliance Considerations

| Risk | Mitigation |
|---|---|
| Automated CAPTCHA bypass | Strictly prohibited; all automation stops at CAPTCHA |
| PII exfiltration | Local-first; no external API receives raw PII |
| Legal exposure (sending letters) | Jurisdiction selector + legal disclaimer in every letter |
| False positives in PII scan | User `review` step required before `act` |
| Data broker TOS violations | `assisted` mode default; `auto` only where explicitly safe |
| Key loss / profile loss | Warn user to back up `profiles/` directory |

Compliance scope:
- **GDPR Art. 17** — Right to Erasure (EU residents or EU-operated sites)
- **CCPA/CPRA** — Right to Delete (California residents)
- **CAN-SPAM / FTC DNC** — assisted opt-out workflow only

---

## 8. Test Strategy

```
tests/
├── unit/
│   ├── test_crypto.py       # Key derivation, encrypt/decrypt round-trip
│   ├── test_pii.py          # E.164 normalization, email validation
│   ├── test_db.py           # Schema creation, CRUD, status transitions
│   ├── test_runner.py       # Dry-run mode, retry logic
│   ├── test_letter_gen.py   # Template rendering, PDF output
│   └── test_redactor.py     # PII redaction in log output
├── integration/
│   └── test_cli.py          # CLI init wizard, config, export (no network)
└── conftest.py              # Fixtures: tmp DB, mock PiiProfile, mock connectors
```

All tests use `pytest`. Network calls are mocked with `pytest-mock` / `responses`. No real API keys required for tests.

---

## 9. Full File Tree

```
RemoveSpamsCall/
├── PLAN.md
├── README.md
├── SECURITY.md
├── LICENSE
├── .gitignore
├── pyproject.toml
├── .env.example
├── profiles/                    # gitignored; encrypted PII profiles live here
│   └── .gitkeep
├── data/
│   └── brokers.yaml             # ~50 broker entries
├── templates/
│   └── letters/
│       ├── gdpr_article17.j2
│       ├── ccpa_deletion.j2
│       └── general_deletion.j2
├── src/
│   └── privacytool/
│       ├── __init__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── cmd_init.py
│       │   ├── cmd_config.py
│       │   ├── cmd_scan.py
│       │   ├── cmd_review.py
│       │   ├── cmd_act.py
│       │   ├── cmd_status.py
│       │   ├── cmd_resolve.py
│       │   ├── cmd_followups.py
│       │   └── cmd_export.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── crypto.py
│       │   ├── db.py
│       │   ├── logger.py
│       │   ├── models.py
│       │   ├── pii.py
│       │   └── runner.py
│       ├── connectors/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── engines/
│       │   │   ├── __init__.py
│       │   │   ├── google.py
│       │   │   ├── bing.py
│       │   │   ├── duckduckgo.py
│       │   │   ├── yandex.py
│       │   │   └── yahoo.py
│       │   └── brokers/
│       │       ├── __init__.py
│       │       ├── loader.py
│       │       ├── base_broker.py
│       │       ├── assisted.py
│       │       └── auto.py
│       ├── letters/
│       │   ├── __init__.py
│       │   └── generator.py
│       └── dashboard/
│           ├── __init__.py
│           └── views.py
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_crypto.py
    │   ├── test_pii.py
    │   ├── test_db.py
    │   ├── test_runner.py
    │   ├── test_letter_gen.py
    │   └── test_redactor.py
    └── integration/
        └── test_cli.py
```

---

*Plan complete. Implementation begins below.*
