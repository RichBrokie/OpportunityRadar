# OpportunityRadar

A personalized CS opportunity discovery platform, built for LaunchPad Hacks 2026.
This first version is a local Streamlit foundation for browsing **explicitly fictional DEMO opportunities** and saving a student profile.

## Run locally

Requires Python 3.11 or newer (validated with Python 3.12).

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Run these commands from the repository root. Streamlit displays the local address in your terminal.
No API key, paid service, or email configuration is required.

```bash
python -m pytest -q
```

The tests use temporary databases, including the Streamlit interaction test.
Dependencies are bounded in `requirements.txt`; this foundation does not yet use a fully locked dependency set.

## What works

- Dashboard with collection statistics and sample cards.
- A single student profile with country, education level, academic year, CS interests, and remote/funded preferences, persisted in SQLite.
- Opportunity cards with title, organization, category, example deadline, summary, interests, funding/remote information, placeholder source URL, and eligibility status.
- Combined category, keyword, interest, remote, and funded filters. Multiple interests use **any-match** semantics. Keyword search covers title, organization, and summary.
- Saved profile preferences initialize browsing filters; users can adjust them. Country is free text; use the country spelling shown in example criteria (case is ignored).
- Basic eligibility checks for deadline, country, and education. Academic year is stored but not used for eligibility. “Potential match” is only a rule comparison, never verified eligibility.
- A standalone duplicate helper for future imports: a normalized nonempty source URL, or matching title, organization, and deadline, counts as a duplicate. It removes tracking parameters and fragments while retaining meaningful query parameters. It does not perform fuzzy matching or fetch sources.

## Demo boundaries

All six opportunities, organizations, dates, and eligibility criteria are invented demonstration data. Every card is labeled **DEMO**. Source links point to `example.com`; they are placeholders and cannot be used to apply. Fixed example deadlines will eventually show “Deadline passed.”

There is no online discovery, live application verification, email delivery, or scheduling. Tavily, Resend, and GitHub Actions scheduling are future work. No API clients or secret values are included.

This is a **single-user local app**, without accounts or authentication. Anyone who can access the running app shares its profile. Do not deploy it as a public multi-user service without adding authentication and per-user storage.

## Architecture

```text
app.py                        Streamlit navigation, forms, cards, and styling
opportunityradar/
  catalog.py                  Fictional dataset, filtering, eligibility rules
  storage.py                  SQLite initialization and profile/catalog persistence
  duplicates.py               Pure duplicate-detection helper
.streamlit/config.toml        Theme and local server defaults
tests/test_core.py            Filtering, duplicates, eligibility, storage tests
tests/test_app.py             Streamlit navigation and profile/filter interaction test
requirements.txt             Runtime and testing dependencies
.env.example                 Optional database setting; no credentials
AGENTS.md                    Guidance for future development
```

On first launch, `storage.initialize()` creates `data/radar.sqlite3` and seeds six demo records. Subsequent launches retain the profile and do not duplicate the seed records. Tables store each small record as JSON to keep this prototype easy to follow. `app.py` calls the pure catalog functions to filter records and explain matches.

The database and virtual environment are ignored by Git. Set `OPPORTUNITYRADAR_DB` in your shell to choose another database path; `.env` files are **not automatically loaded**. To reset your local demo, stop the app and delete `data/radar.sqlite3` (this also deletes your saved profile), then restart it.

## Development notes

This foundation was developed with **OpenAI Codex assistance**, including implementation, documentation, and automated tests. Human review is recommended before extending or publishing it. Keep fictional fixtures labeled DEMO and never commit secrets or user data.
