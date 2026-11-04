"""Deterministic snippet cleanup and conservative triage, never verification."""
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

LIKELY = "Likely opportunity"
REVIEW = "Needs review"
IRRELEVANT = "Irrelevant"
CLASSIFICATIONS = (LIKELY, REVIEW, IRRELEVANT)
QUALITY_VERSION = 1
SOCIAL_HOSTS = {"reddit.com", "facebook.com", "instagram.com", "twitter.com", "x.com", "tiktok.com", "quora.com"}


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif tag in {"p", "div", "br", "li", "nav", "header", "footer"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        elif tag in {"p", "div", "li", "nav", "header", "footer"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain_text(value):
    parser = _PlainText()
    parser.feed(value if isinstance(value, str) else "")
    return "".join(parser.parts)


def clean_text(value, *, omit=()):
    """Remove markup, navigation, URLs, labeled metadata and duplicate sentences."""
    value = plain_text(value)
    value = re.sub(r"(?:https?://|www\.)\S+", "", value, flags=re.I)
    value = re.sub(r"\[([^\]]+)\]\(\s*\)", r"\1", value)
    seen = {re.sub(r"\W+", " ", str(v)).strip().casefold() for v in omit if v}
    kept = []
    for part in re.split(r"\n+|\s*[|•]\s*|(?<=[.!?])\s+", value):
        part = re.sub(r"\s+", " ", part).strip(" \t-·")
        key = re.sub(r"\W+", " ", part).strip().casefold()
        if not key or key in seen:
            continue
        if re.match(r"^(organization|location|funding|eligibility|deadline|category|remote)\s*:", part, re.I):
            continue
        if re.fullmatch(r"(?:home|menu|navigation|search|log ?in|sign ?in|sign ?up|about(?: us)?|contact(?: us)?|read more|learn more|apply now|skip to (?:main )?content)[.!]?", part, re.I):
            continue
        if re.search(r"\b(cookie (?:policy|preferences|settings)|accept (?:all )?cookies|privacy policy|terms (?:of use|and conditions)|all rights reserved|subscribe to (?:our|the) newsletter)\b", part, re.I):
            continue
        kept.append(part)
        seen.add(key)
    return " ".join(kept)


def clean_summary(value, *, omit=(), limit=179):
    text = clean_text(value, omit=omit)
    if not text:
        return "No descriptive snippet available."
    if len(text) <= limit:
        return text
    shortened = text[:limit - 1]
    if " " in shortened:
        shortened = shortened.rsplit(" ", 1)[0]
    return shortened.rstrip(" ,;:") + "…"


def classify(item):
    """Require a specific listing plus supporting detail and a direct-page signal.

    A domain/path is a hint only. Never assert officialness or open applications.
    """
    title = plain_text(item.get("title")).casefold()
    body = clean_text(item.get("raw_snippet", item.get("summary"))).casefold()
    try:
        url = urlsplit(item.get("source_url") or "")
        host, path = (url.hostname or "").lower(), url.path.lower()
    except (ValueError, TypeError):
        host, path = "", ""
    if (any(host == h or host.endswith("." + h) for h in SOCIAL_HOSTS)
            or ((host == "linkedin.com" or host.endswith(".linkedin.com")) and path.startswith(("/posts/", "/feed/", "/pulse/")))):
        return IRRELEVANT, "Social discussion; not a direct listing."
    editorial = r"\b(guide|tips|how to|advice|roundup|round-up|listicle|top \d+|best|ultimate|list of|ways to|interview preparation)\b"
    if re.search(editorial, title):
        return IRRELEVANT, "Guide, advice or roundup rather than a specific listing."
    topic = r"\b(internships?|intern|research|scholarships?|fellowships?|hackathons?|software|developer)\b"
    if not re.search(topic, title + " " + body):
        if not body or not title or title == "untitled search result":
            return REVIEW, "Too little information to assess relevance."
        return IRRELEVANT, "No supported opportunity topic in the title or snippet."
    if re.search(r"/(blog|news|articles?|guides?|discussion|forum)(/|$)", path) or re.search(editorial, body):
        return REVIEW, "Editorial context; inspect the original listing before treating this as an opportunity."
    if re.search(r"\b(opportunities|listings|vacancies|directory|job board|search results)\b", title):
        return REVIEW, "Broad collection rather than evidence of a single listing."
    # Singular listing types and role titles; broad category pages do not qualify.
    listing = re.search(r"\b(internship|intern|scholarship|fellowship|hackathon|research (?:programme?|placement|internship)|(?:software|developer).{0,30}(?:role|position|engineer))\b", title)
    generic = {"student", "students", "summer", "winter", "research", "programme", "program", "placement", "internship", "intern", "scholarship", "fellowship", "hackathon", "applications", "application", "open", "apply", "registration", "remote", "funded", "paid", "for", "the", "a", "an", "of", "and", "in", "at"}
    identity = set(re.findall(r"[a-z]+", title)) - generic
    specific = bool(identity or item.get("organization"))
    detail = re.search(r"\b(apply|applications?|registration|register|eligib\w*|requirements?|responsibilities|undergraduates?|graduates?|students?|participants?|stipend|weeks?|months?)\b", body)
    direct = re.search(r"/(apply|careers?|jobs?|positions?|programmes?|programs?|fellowships?|scholarships?|hackathons?|events?|register|registration|admissions)(/|$|[-_])", path)
    if path.rstrip("/") in {"/jobs", "/careers", "/programs", "/programmes", "/events", "/scholarships", "/fellowships", "/hackathons"}:
        direct = None  # A collection landing page is not a specific listing.
    if listing and specific and detail and direct and host:
        return LIKELY, "Specific listing title, supporting snippet detail and a direct-page URL signal. Source and availability remain unverified."
    return REVIEW, "Insufficient evidence of a specific direct listing; inspect the source."


def normalize_record(item):
    """Derive current fields on a copy; legacy JSON remains untouched on disk."""
    record = dict(item)
    raw = record.get("raw_snippet", record.get("summary", ""))
    record["raw_snippet"] = raw if isinstance(raw, str) else ""
    record["summary"] = clean_summary(record["raw_snippet"], omit=(record.get("title"), record.get("organization")))
    record["classification"], record["classification_reason"] = classify(record)
    record["quality_version"] = QUALITY_VERSION
    return record


def classification_counts(items):
    return {label: sum(item.get("classification") == label for item in items) for label in CLASSIFICATIONS}
