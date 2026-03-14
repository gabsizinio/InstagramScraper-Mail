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

## Running

```bash
python main.py
```

There are no tests or linting configured in this project.

## Architecture

The app has three modules and a single entry point:

- **`main.py`** — Orchestrator. Loads config (from `config.json` or environment variables), validates it, then drives the scraper and mailer sequentially.
- **`scraper.py`** — `InstagramScraper` class using Playwright (Chromium). Handles login, profile scraping, and per-post data extraction (caption text + screenshot). Limits to 5 posts per profile. Screenshots are saved to `debug_screenshots/` and cleaned up after a successful email send.
- **`mailer.py`** — Builds an HTML email digest with inline screenshots (CID attachments) and sends it via SMTP with STARTTLS.

### Config loading priority

Environment variables override `config.json`. This is intentional for GitHub Actions, where secrets are injected as env vars. The `PROFILES` env var accepts either a JSON array string or comma-separated URLs.

### GitHub Actions

`.github/workflows/scrape.yml` runs `main.py` on a schedule (default: every Sunday at midnight UTC) using repository secrets mapped to the env vars expected by `main.py`.

### Known quirks

- `scraper.py` contains a duplicate `scrape_post` method definition (lines 257 and 284). The second definition (line 284) is the one that actually runs, as Python uses the last definition. The first is dead code.
- The scraper runs with `headless=False` in `main.py` (visible browser). Change to `headless=True` for CI/server environments.
- Caption extraction uses multiple fallback strategies with Instagram's obfuscated CSS class names (`_a9zr`, `_ap3a`, etc.) that may break when Instagram updates its frontend.
