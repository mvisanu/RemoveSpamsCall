# Privacy Tool — Claude Code Prompt

> **Usage:** Place this file in your project root and run:
> `claude code --prompt prompt.md`

---

You are a senior security-focused Python automation engineer. Build a production-ready Python CLI tool for personal data removal and privacy protection.

## MANDATORY WORKFLOW

1. First generate a detailed implementation plan and save it as `PLAN.md`:
   - Architecture overview
   - Module structure
   - SQLite data model/schema
   - Connector/plugin pattern
   - CLI command flow
   - Security design (encryption + PII handling)
   - Risk & compliance considerations
   - Test strategy
   - Full file tree

2. After `PLAN.md` is complete, implement the full repository exactly as planned.

3. If any changes are needed mid-build, update `PLAN.md` before modifying code.

---

## CORE FEATURES

### 1 — Search Engine De-indexing
- Discover PII exposure across Google, Bing, DuckDuckGo, Yandex, and Yahoo
- Use SerpAPI + Google Custom Search API for discovery
- Detect PII matches: name, email, phone, address, usernames
- Generate per-engine removal request packets
- Support cache removal request generation
- Generate Wayback Machine exclusion requests
- Track all URLs with a full status lifecycle and confirmation IDs

### 2 — Data Broker Opt-Out
- Maintain `data/brokers.yaml` with ~50 major data broker/people-search sites
- Use a connector plugin pattern per broker with two modes:
  - `assisted` (default) — guides user through manual steps
  - `auto` — only when safe and legally permitted
- Provide FTC Do Not Call assisted workflow
- Parse `List-Unsubscribe` headers from `.eml` files for email opt-outs
- Log every submission attempt to the database

### 3 — Legal Removal Letters
- Generate GDPR Article 17, CCPA/CPRA, and general deletion request letters
- Use Jinja2 templates stored in `templates/letters/*.j2`
- Output both `.txt` and `.pdf` (ReportLab)
- Populate with user PII, target URLs, and appropriate legal basis
- Include a jurisdiction selector and legal disclaimer in each letter

### 4 — Tracking Dashboard
- SQLite database with schema:
  ```
  id, target_type, site, url, discovered_on,
  action_type, status, confirmation_id,
  last_attempt, follow_up_due, follow_up_count, notes
  ```
- Rich-powered CLI views (tables, progress bars, status colors)
- Automatic 30-day follow-up reminders
- Export to CSV and JSON

---

## PII CONFIGURATION

- API keys stored in `.env`
- PII stored in separate encrypted profile files:
  ```
  profiles/default.pii.env
  profiles/jane.pii.env
  ```

Supported profile variables:
```env
FULL_NAME=""
EMAILS="a@example.com,b@example.com"
PHONES="+18005551234,800-555-1234"
ADDRESSES=""
USERNAMES=""
DOB=""
```

Security requirements:
- Validate all email addresses
- Normalize phones to E.164 format using the `phonenumbers` library
- Redact PII in all console output and logs by default
- `--show-pii` flag must require explicit user confirmation before displaying
- Never write plaintext PII to logs or the database
- Encrypt all PII config at rest using a passphrase-derived key (PBKDF2) or OS keychain if available
- `.env` and `*.pii.env` must be listed in `.gitignore`

---

## CLI COMMANDS

```
privacytool init                          # First-time setup wizard
privacytool config set                    # Set/update config values
privacytool config use-profile <name>     # Switch active PII profile

privacytool scan --pii-profile default    # Scan all engines and brokers for PII
privacytool review                        # Interactive review of scan findings

privacytool act --target engine|broker \
               --mode assisted|auto \
               --dry-run                  # Execute removal actions

privacytool status                        # View full tracking dashboard
privacytool resolve --id <id>             # Mark a record as resolved
privacytool followups                     # List items due for follow-up
privacytool export --format csv|json      # Export all records
```

---

## TECH STACK

```
Python 3.11+
selenium (headless Chrome)
requests
tenacity
google-api-python-client
serpapi
sqlite3 (stdlib)
reportlab
jinja2
rich
cryptography
phonenumbers
pytest
```

---

## ARCHITECTURE REQUIREMENTS

- Modular `src/` layout with clear separation of concerns
- Connector plugin system for both search engines and data brokers
- Full type hints throughout (`typing`, `dataclasses`)
- Central job runner with rate limiting and retry logic (tenacity)
- Dry-run mode that simulates all actions without submitting anything
- Structured logging (no plaintext PII ever in logs)
- Rich progress UI for long-running scans

---

## SECURITY & COMPLIANCE RULES — MUST FOLLOW

- Do **NOT** bypass CAPTCHAs, paywalls, or authentication systems
- Default to `assisted` mode whenever automation safety is unclear
- Never claim a successful submission without a verifiable confirmation
- Do not store plaintext PII or secrets anywhere in logs or the database
- Local-first only — no PII is ever sent to external storage or third-party services
- Include `SECURITY.md` with threat model and compliance notes
- Include compliance notes in `README.md`

---

## DELIVERABLES CHECKLIST

- [ ] `PLAN.md` — generated first, before any code
- [ ] `src/` — all Python modules
- [ ] `data/brokers.yaml` — ~50 structured broker entries
- [ ] `templates/letters/*.j2` — Jinja2 letter templates (GDPR, CCPA, general)
- [ ] SQLite initialization script / migration
- [ ] `pyproject.toml` with pinned dependencies
- [ ] `README.md` — full setup, API key instructions, usage guide
- [ ] `SECURITY.md` — threat model, compliance, responsible use
- [ ] `LICENSE`
- [ ] `tests/` — basic pytest tests covering core modules
- [ ] Dry-run support on all `act` commands

---

## BEGIN

Start by generating `PLAN.md` in full before writing any code.