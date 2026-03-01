# Contributing to privacytool

## Getting Started

```bash
git clone https://github.com/mvisanu/RemoveSpamsCall.git
cd RemoveSpamsCall
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest                        # all tests
pytest tests/unit/ -v         # unit tests only
pytest tests/unit/test_crypto.py  # single file
pytest --cov=src/privacytool  # with coverage
```

All tests must pass before submitting a PR. CI runs automatically on every push.

## Project Structure

```
src/privacytool/
├── cli/          # One file per CLI command (cmd_*.py)
├── core/         # Config, crypto, DB, logger, models, runner
├── connectors/   # Search engine and broker plugins
├── letters/      # Legal letter generation
└── dashboard/    # Rich UI views
data/brokers.yaml # Broker registry — no code needed to add a broker
templates/letters/ # Jinja2 letter templates
```

## Adding a Data Broker

No code required — just add an entry to `data/brokers.yaml`:

```yaml
- id: my_broker
  name: My Broker
  url: https://www.mybroker.com
  opt_out_url: https://www.mybroker.com/optout
  mode: assisted
  auto_supported: false
  jurisdiction: US
  category: people-search
  steps:
    - "Go to the opt-out URL"
    - "Search for your name"
    - "Submit the removal form"
```

## Adding a Search Engine Connector

1. Create `src/privacytool/connectors/engines/myengine.py` subclassing `BaseConnector`
2. Implement `discover()` and `act()`
3. Register it in `cmd_scan.py` and `cmd_act.py`
4. Add tests in `tests/unit/`

## Security Rules

These must never be violated:

- Never log, store, or transmit plaintext PII
- Never bypass CAPTCHAs, paywalls, or authentication
- Default to `assisted` mode; only use `auto` when `auto_supported: true`
- Keep `.env` and `profiles/` out of all commits

## Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Include or update tests for any changed behaviour
- Run `pytest` locally before pushing
- Reference any related issue in the PR description
