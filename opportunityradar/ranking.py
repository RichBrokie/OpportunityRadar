"""Explainable relevance hints, never source verification."""
import re
from datetime import date, datetime, timezone
from urllib.parse import urlsplit

SORTS = ["Recommended", "Recently discovered", "Deadline soonest", "Title A–Z"]
SOCIAL_HOSTS = {"reddit.com", "facebook.com", "instagram.com", "twitter.com", "x.com", "tiktok.com"}


def parsed_date(value):
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def quality_signals(item, today=None):
    """Rank likely application pages above guides; retain all results for review."""
    today = today or date.today()
    title = str(item.get("title") or "").casefold()
    content = title + " " + str(item.get("summary") or "").casefold()
    try:
        url = urlsplit(item.get("source_url") or "")
        host, path = (url.hostname or "").removeprefix("www."), url.path.lower()
    except ValueError:
        host, path = "", ""
    score, reasons = 0, []
    if any(word in path for word in ("/apply", "/careers", "/jobs", "/admissions", "/opportunities", "/register")):
        score += 3
        reasons.append("Application-page URL signal")
    if host.endswith((".edu", ".ac.uk", ".edu.pk")):
        score += 1
        reasons.append("Academic-domain signal")
    if re.search(r"\b(apply|applications open|register|registration open)\b", content):
        score += 1
    if re.search(r"\b(guide|how to|tips|best|top \d+|ultimate|roundup)\b", title) or "/blog/" in path:
        score -= 4
        reasons.append("May be a guide or roundup")
    if any(host == domain or host.endswith("." + domain) for domain in SOCIAL_HOSTS):
        score -= 4
        reasons.append("Social post; check the original organizer")
    years = [int(y) for y in re.findall(r"\b20\d{2}\b", title)]
    deadline = parsed_date(item.get("deadline"))
    if (years and max(years) < today.year) or (deadline and deadline < today):
        score -= 5
        reasons.append("May refer to an older or closed opportunity")
    if not re.search(r"\b(internship|intern|research|scholarship|fellowship|hackathon|software|developer)\b", content):
        score -= 2
        reasons.append("Limited opportunity relevance in the snippet")
    return score, reasons


def discovered_time(item):
    try:
        value = datetime.fromisoformat(item.get("discovered_at") or "")
        return value.replace(tzinfo=value.tzinfo or timezone.utc).timestamp()
    except (ValueError, TypeError, OverflowError):
        return 0


def sort_opportunities(items, order="Recommended"):
    if order == "Title A–Z":
        return sorted(items, key=lambda i: (i.get("title") or "").casefold())
    if order == "Deadline soonest":
        return sorted(items, key=lambda i: parsed_date(i.get("deadline")) or date.max)
    if order == "Recently discovered":
        return sorted(items, key=discovered_time, reverse=True)
    return sorted(items, key=lambda i: (quality_signals(i)[0], discovered_time(i)), reverse=True)
