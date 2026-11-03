"""Conservative duplicate detection for a future import pipeline."""
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def normalize_url(url):
    try:
        parts = urlsplit(url.strip() if isinstance(url, str) else "")
    except ValueError:
        return ""
    query = sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                   if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"})
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), ""))


def normalize_text(value):
    return re.sub(r"\s+", " ", value if isinstance(value, str) else "").strip().casefold()


def is_duplicate(candidate, existing):
    """Same nonempty URL, or title + organization + deadline, counts as duplicate.

    Meaningful query parameters and deadline differences are retained so separate
    listings and annual editions are not merged by title alone.
    """
    url = normalize_url(candidate.get("source_url", ""))
    fields = ("title", "organization", "deadline")
    signature = tuple(normalize_text(candidate.get(k, "")) for k in fields)
    return any((url and url == normalize_url(item.get("source_url", ""))) or
               (all(signature) and signature == tuple(normalize_text(item.get(k, "")) for k in fields))
               for item in existing)
