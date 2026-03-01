# privacytool

[![Tests](https://github.com/mvisanu/RemoveSpamsCall/actions/workflows/tests.yml/badge.svg)](https://github.com/mvisanu/RemoveSpamsCall/actions/workflows/tests.yml)
![Tests](https://img.shields.io/badge/tests-33%20passed-brightgreen)

A production-ready Python CLI for personal data removal and privacy protection.
Discovers PII exposure across major search engines and data brokers, generates
legal removal letters, and tracks every submission — all locally, without sending
your data to any external service.

---

## Features

| Feature | Details |
|---|---|
| Search engine de-indexing | Google (SerpAPI/CSE), Bing, DuckDuckGo, Yandex, Yahoo |
| Data broker opt-out | ~50 brokers via assisted or auto mode |
| Legal letters | GDPR Art. 17, CCPA/CPRA, general deletion (.txt + .pdf) |
| Tracking dashboard | Rich-powered tables, follow-up reminders, CSV/JSON export |
| Local-first security | All PII encrypted at rest; nothing leaves your machine |

---

## Requirements

- Python 3.11+
- Chrome (for Selenium-based auto connectors, when implemented)
- `pip` / `venv` or any compatible package manager

---

## Installation

```bash
git clone <repo-url>
cd RemoveSpamsCall
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

---

## API Key Setup

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

| Variable | Where to get it |
|---|---|
| `SERP_API_KEY` | [serpapi.com](https://serpapi.com) — free tier available |
| `GOOGLE_CSE_API_KEY` | [console.cloud.google.com](https://console.cloud.google.com) → Custom Search API |
| `GOOGLE_CSE_ID` | [programmablesearchengine.google.com](https://programmablesearchengine.google.com) |

If no API keys are configured, engine connectors will fall back to direct web requests
(rate-limited, results may vary).

---

## First-time Setup

```bash
privacytool init
```

The wizard will:
1. Create a master passphrase-encrypted PII profile (`profiles/default.pii.enc`)
2. Initialize the SQLite tracking database (`~/.privacytool/tracker.db`)
3. Create `.env` from `.env.example` if not present

---

## Usage

### Scan for PII exposure

```bash
privacytool scan --pii-profile default
privacytool scan --engines-only        # search engines only
privacytool scan --brokers-only        # data brokers only
privacytool scan --dry-run             # simulate, do not save
```

### Review findings

```bash
privacytool review
# Interactive prompt: accept (mark pending) or skip each record
```

### Act on pending records

```bash
privacytool act                        # assisted mode (default)
privacytool act --mode auto            # auto mode (supported brokers only)
privacytool act --target engine        # engine records only
privacytool act --dry-run              # simulate, do not submit
```

### Track status

```bash
privacytool status
privacytool status --status submitted
privacytool followups                  # records due for 30-day follow-up
privacytool resolve --id 42            # mark record #42 as resolved
```

### Generate legal letters

```bash
# Letters are generated via `act` for records with action_type=letter,
# or directly through the Python API:
from privacytool.letters.generator import generate_letter
generate_letter("gdpr", profile, "example.com", ["https://..."], "output/")
```

### Export records

```bash
privacytool export --format csv
privacytool export --format json --output my_export
```

### Profile management

```bash
privacytool config set SERP_API_KEY mykey123
privacytool config use-profile work
privacytool config list-profiles
```

---

## Running Tests

```bash
pytest                        # all tests
pytest tests/unit/            # unit tests only
pytest tests/unit/test_crypto.py -v
pytest --cov=src/privacytool  # with coverage
```

---

## Security & Compliance

See [SECURITY.md](SECURITY.md) for the full threat model and compliance notes.

Key points:
- PII profiles are encrypted with PBKDF2-HMAC-SHA256 (600 000 iterations) + Fernet
- All log output has PII redacted automatically
- URLs stored in the database are SHA-256 hashed
- `.env` and `profiles/` are gitignored — **never commit them**
- The tool does **not** bypass CAPTCHAs, paywalls, or authentication

---

## Project Structure

```
src/privacytool/
├── cli/          # Typer CLI commands
├── core/         # Config, crypto, DB, logger, runner
├── connectors/   # Search engine + broker plugins
├── letters/      # Jinja2 letter generator + ReportLab PDF
└── dashboard/    # Rich views and progress bars
data/
└── brokers.yaml  # ~50 broker entries
templates/letters/ # Jinja2 letter templates
tests/            # pytest unit + integration tests
```

---

## License

MIT — see [LICENSE](LICENSE).
