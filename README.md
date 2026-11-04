# OpportunityRadar

A personalized CS opportunity discovery platform, built for LaunchPad Hacks 2026.
A local Streamlit app for saving a student profile, browsing fictional DEMO opportunities, and explicitly searching for real web results with Tavily. Discovered results are unverified leads, not confirmed opportunities.

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
Demo browsing requires no credentials. Optional discovery uses Tavily (see configuration below); no email configuration is required.

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

Optional Tavily discovery is available in a separate **Discovered** collection. There is no live application verification, email delivery, or scheduling. Resend and GitHub Actions scheduling remain future work. No secret values are included.

This is a **single-user local app**, without accounts or authentication. Anyone who can access the running app shares its profile. Do not deploy it as a public multi-user service without adding authentication and per-user storage.

## Architecture

```text
app.py                        Streamlit navigation, forms, cards, and styling
opportunityradar/
  catalog.py                  Fictional dataset, filtering, eligibility rules
  storage.py                  SQLite initialization and profile/catalog persistence
  duplicates.py               Pure duplicate-detection helper
  discovery.py                Tavily queries, conservative extraction, safe errors
  quality.py                  Deterministic snippet cleaning and relevance classification
  components.py               Shared Streamlit cards, forms and discovery status
  presentation.py             Escaped card markup and compact formatting
  ranking.py                  Explainable sorting within each classification
.streamlit/config.toml        Theme and local server defaults
tests/test_core.py            Filtering, duplicates, eligibility, storage tests
tests/test_app.py             Streamlit navigation, profile, filters and explicit discovery tests
tests/test_discovery.py       Mocked API, cache, quota, parsing and failure tests
requirements.txt             Runtime and testing dependencies
.env.example                 Optional database setting; no credentials
AGENTS.md                    Guidance for future development
```

On first launch, `storage.initialize()` creates `data/radar.sqlite3` and seeds six demo records. Subsequent launches retain the profile and do not duplicate the seed records. Tables store each small record as JSON to keep this prototype easy to follow. `app.py` calls the pure catalog functions to filter records and explain matches.

The database and virtual environment are ignored by Git. Set `OPPORTUNITYRADAR_DB` in your shell to choose another database path; `.env` files are **not automatically loaded**. Keep your existing database when upgrading. To experiment with a fresh workspace, choose a different database path; do not delete your saved profile and discoveries.

## Development notes

This foundation and Phase 2 discovery were developed with **OpenAI Codex assistance**, including implementation, documentation, and automated tests. Human review is recommended before extending or publishing it. Keep fictional fixtures labeled DEMO and never commit secrets or user data.


## Live discovery setup and manual check

Install the updated requirements. The official `tavily-python` SDK (tested with 0.8.5) supports limited keyless search. No network search happens at startup or on ordinary Streamlit reruns.

Choose one configuration method:

- Set `TAVILY_API_KEY` in the process environment using your platform's secure environment settings.
- Or add `TAVILY_API_KEY = "your-key"` to `.streamlit/secrets.toml` locally, or to Streamlit Cloud's secrets settings. This file is ignored by Git. Environment keys take precedence.
- For limited development without a key, explicitly select **Allow limited keyless development** in the app. Tavily controls availability and limits; no anonymous quota is guaranteed. Configured keys take precedence over this option.

Do not paste keys into chat, source code, or commits. `.env.example` documents settings; the app does not load `.env` automatically. Allow HTTPS access to `api.tavily.com` if your environment restricts network destinations.

1. Save a profile. Country, education (including undergraduate), interests, and remote/funded preferences shape queries. These profile fields are sent to Tavily when searching.
2. Open **Opportunities → Discovered**, choose one of the six search topics, and click **Discover opportunities**. Each click searches one topic: internships, summer research, scholarships, fellowships, hackathons, or remote software development.
3. Check the search counts and the **Likely opportunity**, **Needs review**, and **Irrelevant** views. Open **More details** for raw snippets, classification reasons, UTC discovery timestamps and original URLs. Results are saved in SQLite and persist across sessions.
4. Repeat the same query within 15 minutes to check the cache. Change a filter or navigate away/back: this must not make an API request.
5. Switch to **Demo** to see the separate fictional collection. Unknown remote/funding or interest values do not pass strict filters; clear filters if nothing appears.

Each uncached search uses basic search, at most five results, a 20-second timeout, no generated answer, and no raw-content extraction. There are at most **12 API attempts per rolling hour per local database**, including failed calls. The limit and 15-minute query cache persist across reruns/restarts and are shared by this single-user app. They are not a provider billing cap; deleting/changing the database resets them. Keyed calls may consume Tavily credits. There are no automatic retries. Empty valid results are cached too; failures are not cached.

## What discovery does and does not verify

The SDK supplies titles, snippets, and URLs. The app stores the original source URL and labels each discovered card **Unverified**. Search results can include stale pages, listing aggregators, or irrelevant results. A source link is not evidence that applications are open. Actions say **View source**, never Apply.

Organization, location, funding, and eligibility are captured only from explicit `Organization:`, `Location:`, `Funding:`, and `Eligibility:` lines in the snippet. Only exact `remote` / `in-person` and `funded` / `unfunded` values become booleans; other values remain unknown. These fields are still unverified snippet claims. Interests use literal matches against the supported interest names. Category is the selected search topic, not a verified classification. No organization is inferred from a domain name.

This phase does not verify source pages, so **verified deadlines always remain unknown**, `verified` stays false, and country/education requirements stay unknown. Any date mentioned in the snippet remains unverified description text. Eligibility always says **Unverified** for discovered records, even with a matching profile. Confirm current deadlines, eligibility, funding and authenticity on the original site.

Storage adds `discovered`, `search_cache`, and `search_attempts` tables without deleting or rewriting existing profiles/demo records. Duplicate URLs (ignoring tracking parameters and fragments) or complete title/organization/deadline matches are skipped. Null fields never establish a duplicate on their own. A duplicate preserves its first discovery timestamp; this phase does not refresh old records automatically. Cache entries contain result data, never API keys. Existing `opportunities` records remain the separate demo catalog.

## Validation

Run `python -m pytest -q`. All API tests use mocked clients and temporary SQLite databases, including invalid keys, keyless limits, rate limits, network failures, empty/malformed responses, missing fields, malformed dates, duplicates, cache expiry and the persistent local request limit. Streamlit tests check that only the discovery button can initiate a search. Automated tests do not consume live API credits. Live provider availability must be checked with the manual workflow above.

## Redesigned student workspace

The light theme uses restrained blue accents, a compact sidebar, and responsive layouts. The dashboard includes an explicit keyword discovery form, real saved-result statistics, category shortcuts, and the three most recently discovered records. Demo records are never counted as real discoveries.

The Opportunities page uses a single-column list with consistent collapsed card bodies. Descriptions are cleaned and shortened to fewer than 180 characters and clamped to two lines on desktop and mobile. Each card shows category, one unobtrusive Unverified label, organization, location, deadline and funding, plus **View source**. Unknown fields explicitly say “Unknown.” Full titles, raw snippets, original URLs, discovery timestamps, detailed eligibility, classification explanations and ranking hints are accessible under **More details**. Demo cards remain explicitly fictional in their separate collection.

Use **Search this collection** for local filtering. **Personalize filters** retains profile interest/remote/funded filters. Sort by Recommended, Recently discovered, Deadline soonest (unknown dates last), or Title A–Z. The discovery form is separate: only its submit button invokes Tavily. Keyword input combines with your chosen topic and saved profile. Keyless access and usage guidance are under **Search settings**. Loading, empty, success and error states remain visible without repeating technical metadata on every card.

Recommended ordering within each classification uses transparent heuristics: application/careers/registration paths and academic domains receive a boost; guide/roundup titles, social domains, older title years, past deadlines and weak topic relevance receive penalties. Queries request official organizer/application pages. These signals do **not** prove a source is official, current, relevant or verified. No companies, deadlines or eligibility requirements are invented. Ranking applies to existing saved records as well as new results.

UI helpers live in `opportunityradar/components.py`; escaped card formatting in `presentation.py`; static responsive CSS in `assets/style.css`; pure ranking/sorting helpers in `ranking.py`. External strings are escaped before entering card markup; full snippets use plain text, and source buttons accept only valid HTTP(S) URLs. No API secrets appear in markup.

Validation includes mocked discovery/profile/navigation regressions, dashboard submit and quick-category flows, sort behavior, source-quality heuristics, malformed dates, and HTML-escaping checks. Browser tooling is not an app dependency. The redesign and result-quality improvements were implemented with OpenAI Codex assistance. No email automation was added.

## Result quality and review boundaries

New records store the untouched provider text in `raw_snippet`, separately from the cleaned `summary`. Deterministic Python rules remove markup (including script/style content), embedded URLs, repeated sentences, explicit metadata lines, common navigation and boilerplate. Summaries repeat neither the title nor organization when they occur as standalone snippet text. Truncation preserves words where possible; the full raw text remains available as plain text. Cleaning does not generate facts or call an LLM.

Classification is conservative and independent of ranking:

- **Likely opportunity** requires a specific singular position/programme/event title, supporting snippet detail, and a direct application, jobs, programme or registration URL signal. This estimates relevance only; it does not establish authenticity or current availability.
- **Needs review** retains sparse results, broad directories, uncertain listings and editorial pages with possible leads. A plausible title, academic domain or application URL alone is insufficient.
- **Irrelevant** retains obvious guides, advice/listicles, social discussions and off-topic results separately. They never appear in the likely list or dashboard cards.

Rules use English words and URL patterns. They can miss valid listings, misunderstand snippets, or accept misleading pages. A “likely” result can be old, closed or fraudulent. No page is labeled official. Dates mentioned in text remain unverified; verified deadlines and unprovided eligibility, location and funding stay unknown. Inspect the original source before making decisions. Category is still the chosen search topic, not an inferred fact.

Search status counts up to five provider rows as **results found**, including duplicates and invalid rows. **Accepted as likely**, **sent for review**, and **saved as irrelevant** count only newly saved, nonduplicate records. Their sum is the number added. Duplicates within the response or already in the database are skipped and counted once per row, and malformed rows/unsafe URLs are counted as invalid. Thus `found = accepted + review + irrelevant + duplicates + invalid`. Cache replay normally adds zero records and reports duplicates; it does not spend another API attempt. Saved-collection counts are unique records before browsing filters; the “shown” count reflects active classification and filters. Demo records are excluded from all discovery counts.

No database reset or destructive migration is required. Legacy discovered JSON is adapted on load: its saved summary becomes the raw-snippet fallback, and current cleaning/classification rules are applied on a copy. Old payloads, first-discovery timestamps, profile, demo catalog and request history remain intact. Text truncated by older versions cannot be recovered. New inserts store raw and derived fields plus a quality-rule version. Existing list-shaped cache entries still work until normal expiry; new cache envelopes also retain the original row count. Invalid rows discarded by old caches cannot be counted retrospectively. Duplicate records keep their original content and timestamps.

For a manual check, search explicitly, inspect each classification, switch category and discovery-date sorting, open More details, then repeat the search to check duplicate/cache counts. Test desktop and a narrow mobile viewport, including long titles and snippets. All automated discovery tests use mocked Tavily responses and temporary SQLite databases; they do not require credentials or verify live provider availability.

Result-quality validation: **72 pytest tests passed**, `pip check` and `git diff --check` passed. PR #3's original 35-test suite was also reproduced from commit `60a64f6`. Desktop (1280px) and mobile (390px) demo-card layouts were inspected in the in-app browser using a temporary database: equal collapsed card-body heights within each viewport and no horizontal page overflow. Actual provider responses, source authenticity and application availability remain unverified.
