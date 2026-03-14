# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

For local execution, copy and fill in the config:

```bash
cp config.example.json config.json
# Edit config.json with real credentials
```

Optionally generate a saved session to avoid the login flow:

```bash
python save_session.py
```

If `instagram_session.json` is present in the project root, `main.py` will use it automatically and skip the login step.

## Running

```bash
python main.py
```

There are no tests or linting configured in this project.

## Architecture

The app has three modules, one local utility script, and a single entry point:

- **`main.py`** — Orchestrator. Loads config (from `config.json` or environment variables), validates it, then drives the scraper and mailer sequentially. If `instagram_session.json` exists (or `INSTAGRAM_SESSION_FILE` env var points to one), it passes it to the scraper and skips the login step.
- **`scraper.py`** — `InstagramScraper` class using Playwright (Chromium). Handles optional session restore, login, profile scraping, and per-post data extraction (caption text + screenshot). Limits posts per profile to `max_posts` (default 5). Screenshots are saved to `debug_screenshots/` and cleaned up after a successful email send.
- **`mailer.py`** — Builds an HTML email digest with inline screenshots (CID attachments) and sends it via SMTP with STARTTLS.
- **`save_session.py`** — Local-only utility. Opens a visible browser so the user can log in manually, then saves the Playwright storage state to `instagram_session.json`. Run once to generate the session; re-run when the session expires.

### Config loading priority

Environment variables override `config.json`. This is intentional for GitHub Actions, where secrets are injected as env vars. The `PROFILES` env var accepts either a JSON array string or comma-separated URLs.

### Session-based authentication

Instagram blocks automated logins from data center IPs (e.g. GitHub Actions). The recommended approach is to generate `instagram_session.json` locally via `save_session.py` and store its contents as the `INSTAGRAM_SESSION` repository secret. The workflow writes the secret to a file before running `main.py`.

Session priority in `main.py`:
1. If `instagram_session.json` exists → use it, skip login
2. Otherwise → fall back to username/password login

### GitHub Actions

`.github/workflows/scrape.yml` runs `main.py` on a schedule (default: every Sunday at midnight UTC). It writes the `INSTAGRAM_SESSION` secret to `instagram_session.json` before execution, and maps all other secrets to the env vars expected by `main.py`.

### Known quirks

- Caption extraction uses multiple fallback strategies with Instagram's obfuscated CSS class names (`_a9zr`, `_ap3a`, etc.) that may break when Instagram updates its frontend.
- Saved sessions expire (typically weeks to months). When the scraper stops collecting posts, re-run `save_session.py` and update the `INSTAGRAM_SESSION` secret.
