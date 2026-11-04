"""Explicit Tavily searches; conservative, unverified snippet extraction."""
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests
from tavily import TavilyClient
from tavily.errors import (InvalidAPIKeyError, UsageLimitExceededError,
                          TavilyKeylessLimitError, ForbiddenError, TimeoutError as TavilyTimeout)

from opportunityradar.catalog import INTERESTS
from opportunityradar.quality import LIKELY, REVIEW, IRRELEVANT, normalize_record
from opportunityradar.storage import cached_search, reserve_search, store_search, save_discovered

TOPICS = {
    "CS internships": ("Internship", "computer science internships applications"),
    "Summer research": ("Research", "computer science summer research programmes applications"),
    "Scholarships": ("Scholarship", "computer science scholarships applications"),
    "Fellowships": ("Fellowship", "computer science student fellowships applications"),
    "Hackathons": ("Hackathon", "student hackathons registration"),
    "Remote software opportunities": ("Software opportunity", "remote software development opportunities for students"),
}


class DiscoveryError(Exception):
    """Safe user-facing error, without provider payloads or credentials."""


def resolve_api_key(secrets=None):
    return os.getenv("TAVILY_API_KEY") or (secrets or {}).get("TAVILY_API_KEY") or None


def build_query(topic, profile=None, keyword=""):
    profile = profile or {}
    parts = [TOPICS[topic][1], str(datetime.now(timezone.utc).year)]
    for field in ("country", "education_level"):
        if profile.get(field):
            parts.append(str(profile[field])[:100])
    parts.extend(str(i)[:60] for i in profile.get("interests", [])[:6])
    if profile.get("remote_only"):
        parts.append("remote")
    if profile.get("funded_only"):
        parts.append("funded")
    if keyword.strip():
        parts.append(keyword.strip()[:160])
    parts.append("official organizer application page -guide -tips -roundup")
    return " ".join(parts)


def text(value):
    return value.strip() if isinstance(value, str) else ""


def valid_source(url):
    if not isinstance(url, str) or re.search(r"[\s\\\x00-\x1f\x7f]", url):
        return False
    try:
        parsed = urlsplit(url)
        parsed.port  # Reject malformed ports as well as malformed hosts.
        return parsed.scheme in {"https", "http"} and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def labeled_value(content, label):
    """Only retain explicitly labeled fields, not inferred prose claims."""
    match = re.search(rf"(?im)^\s*{label}\s*:\s*([^\n]+)", content)
    return match.group(1).strip()[:500] if match else None


def parse_result(result, category, discovered_at):
    if not isinstance(result, dict):
        return None
    url = text(result.get("url"))
    if not valid_source(url):
        return None
    content = result.get("content") if isinstance(result.get("content"), str) else ""
    title = text(result.get("title"))
    location = labeled_value(content, "Location")
    funding = labeled_value(content, "Funding")
    return normalize_record(dict(
        title=title or "Untitled search result", organization=labeled_value(content, "Organization"),
        category=category, category_basis="Search topic (unverified)",
        raw_snippet=content, location=location, funding_details=funding,
        source_url=url, deadline=None, remote={"remote": True, "in-person": False}.get((location or "").casefold()),
        funded={"funded": True, "unfunded": False}.get((funding or "").casefold()),
        eligibility_requirements=labeled_value(content, "Eligibility"),
        countries=None, education_levels=None,
        interests=[i for i in INTERESTS if i.casefold() in (title + " " + content).casefold()],
        discovered_at=discovered_at, verified=False, is_demo=False, status="DISCOVERED",
    ))


def save_search_results(records, found, path, *, cached):
    counts = save_discovered(records, path, with_counts=True)
    return dict(added=counts["added"], results=len(records), found=found,
                accepted=counts[LIKELY], review=counts[REVIEW], irrelevant=counts[IRRELEVANT],
                duplicates=counts["duplicates"], invalid=found - len(records) + counts["invalid"], cached=cached)


def discover(topic, profile=None, api_key=None, allow_keyless=False, path=None, keyword=""):
    """One explicit topic search. Cache hits do not consume request allowance."""
    if not api_key and not allow_keyless:
        raise DiscoveryError("Set TAVILY_API_KEY in your environment or Streamlit secrets, or enable limited keyless development.")
    query = build_query(topic, profile, keyword)
    cached = cached_search(query, path)
    if cached is not None:
        # Old caches stored a list; new envelopes also retain the provider count.
        records = cached if isinstance(cached, list) else cached["records"]
        found = len(records) if isinstance(cached, list) else cached["found"]
        return save_search_results(records, found, path, cached=True)
    if not reserve_search(path):
        raise DiscoveryError("Local limit reached: 12 API requests per rolling hour. Cached searches remain available; try again later.")
    client = None
    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(query=query, search_depth="basic", max_results=5,
                                 include_answer=False, include_raw_content=False,
                                 auto_parameters=False, timeout=20)
    except InvalidAPIKeyError:
        raise DiscoveryError("Tavily rejected the API key. Check TAVILY_API_KEY in environment settings or Streamlit secrets.") from None
    except TavilyKeylessLimitError:
        raise DiscoveryError("Tavily's keyless allowance is unavailable or exhausted. Add an API key or try again later.") from None
    except UsageLimitExceededError:
        raise DiscoveryError("Tavily rate or usage limit reached. Check your quota and try again later.") from None
    except ForbiddenError:
        raise DiscoveryError("Tavily denied access. Check your account permissions and network policy.") from None
    except (requests.RequestException, TavilyTimeout, TimeoutError):
        raise DiscoveryError("Could not reach Tavily. Check network access to api.tavily.com and try again later.") from None
    except Exception:
        # Provider messages may contain sensitive request details; never display them.
        raise DiscoveryError("Tavily could not complete this search. Check configuration and try again later.") from None
    finally:
        if client is not None:
            client.session.close()
    if not isinstance(response, dict) or not isinstance(response.get("results"), list):
        raise DiscoveryError("Tavily returned an unexpected response. No results were saved.")
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = response["results"][:5]
    records = [record for row in rows
               if (record := parse_result(row, TOPICS[topic][0], timestamp)) is not None]
    outcome = save_search_results(records, len(rows), path, cached=False)
    store_search(query, {"records": records, "found": len(rows)}, path)
    return outcome
