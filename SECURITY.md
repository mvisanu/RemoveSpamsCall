# SECURITY.md — Threat Model, Compliance & Responsible Use

## Threat Model

### Assets

| Asset | Sensitivity | Storage |
|---|---|---|
| PII profile (name, email, phone, address) | Critical | Encrypted at rest (`profiles/*.pii.enc`) |
| Master passphrase | Critical | Memory only (never stored) |
| API keys (SerpAPI, Google) | High | `.env` (gitignored) |
| Tracking database | Medium | `~/.privacytool/tracker.db` |

### Threats & Mitigations

| Threat | Mitigation |
|---|---|
| Plaintext PII in logs | `PiiRedactingFilter` strips emails and phones from all log output |
| Plaintext PII in database | URLs stored as SHA-256 hashes; notes never contain PII |
| Passphrase brute-force | PBKDF2-HMAC-SHA256, 600 000 iterations, 16-byte random salt |
| Secrets in version control | `.env` and `profiles/` are gitignored; `.gitignore` ships with the repo |
| PII exfiltration via API | No raw PII is included in any outbound API request (search terms only) |
| Accidental `--show-pii` in shared terminal | Flag requires explicit interactive confirmation before displaying any PII |
| CAPTCHA bypass / unauthorized automation | Strictly prohibited; automation stops at any CAPTCHA or auth prompt |
| Data broker TOS violations | `assisted` mode is default; `auto` only where `auto_supported: true` and documented |
| Key loss | Users are warned to back up `profiles/` during `init`; no recovery without passphrase |

---

## Encryption Design

- **Key derivation:** PBKDF2-HMAC-SHA256, 600 000 iterations (OWASP-recommended minimum as of 2023), 16-byte random salt per file
- **Cipher:** `cryptography.fernet.Fernet` (AES-128-CBC + HMAC-SHA256)
- **On-disk format:** `salt(16 bytes) || Fernet token`
- **Passphrase caching:** Passphrase is held in-process memory only for the duration of a single CLI invocation; it is never written to disk, environment variables, or log files
- **OS Keychain (opt-in):** After first unlock, users may opt in to storing the derived key in the OS keychain (`keyring` library) — controlled by `USE_KEYCHAIN=1` in `.env`

---

## Compliance Scope

### GDPR (EU) — General Data Protection Regulation

- The tool generates **Article 17 Right to Erasure** request letters
- Targets EU-operated websites or EU residents' data
- 30-day response deadline is tracked per record
- Users are responsible for verifying they have a valid legal basis for each request

### CCPA / CPRA (California, USA)

- The tool generates **Section 1798.105 Right to Delete** request letters
- 45-day response window is noted in generated letters
- Do Not Sell / Do Not Share requests are included in generated letters

### CAN-SPAM / FTC Do Not Call

- The tool provides **assisted-mode** guidance for FTC DNC registration only
- No automated calls or messages are made

---

## Responsible Use

**This tool is designed for personal use — to remove your own information.**

By using this tool you agree to:

1. **Only submit removal requests for your own personal information** or information you are legally authorized to act upon
2. **Not bypass CAPTCHAs, paywalls, or authentication mechanisms** — the tool is designed to prevent this
3. **Verify each removal request before submission** — the `review` step exists for this purpose
4. **Respect the terms of service** of each search engine and data broker
5. **Consult a qualified attorney** before sending legal letters in contested situations

**The generated legal letters are templates, not legal advice.** Their effectiveness depends on your jurisdiction, the data controller's location, and the specifics of your situation.

---

## Reporting Vulnerabilities

If you discover a security vulnerability in this tool, please report it by opening a GitHub issue marked **[SECURITY]** or by contacting the maintainer directly. Do not include sensitive personal data in bug reports.

---

## Data Retention

- The tracking database (`~/.privacytool/tracker.db`) persists indefinitely until you delete it
- To wipe all local data: `rm -rf ~/.privacytool/ profiles/`
- Exported CSV/JSON files should be treated with the same care as the database

---

*Last reviewed: 2026-03-01*
