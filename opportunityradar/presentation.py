"""Small formatting helpers. Escape all data before including it in HTML."""
from html import escape
import re
from opportunityradar.ranking import parsed_date
from opportunityradar.quality import clean_summary


def short_description(value, limit=180):
    text = re.sub(r"\s+", " ", str(value or "No description available.")).strip()
    if len(text) <= limit:
        return text
    return text[:limit - 1].rsplit(" ", 1)[0] + "…"


def date_label(value):
    value = parsed_date(value)
    return value.strftime("%d %b %Y") if value else "Unknown"


def card_html(item):
    """Only static markup; all external text is escaped, no external HTML/URLs."""
    e = lambda value: escape(re.sub(r"(?:https?://|www\.)\S+", "", str(value), flags=re.I), quote=True)
    demo = item.get("is_demo", False)
    location = item.get("location") or {True: "Remote", False: "In person"}.get(item.get("remote"), "Unknown")
    funding = {True: "Funded", False: "Unfunded"}.get(item.get("funded"), "Unknown")
    status = "DEMO · Fictional" if demo else "Unverified"
    deadline = ("Example deadline" if demo else "Deadline") + ": " + date_label(item.get("deadline"))
    summary = clean_summary(item.get("raw_snippet", item.get("summary")), omit=(item.get("title"), item.get("organization")))
    return f'''<article class="opportunity-card">
<div class="card-tags"><span class="category-tag">{e(item.get("category") or "Opportunity")}</span><span class="status-tag">{status}</span></div>
<h3>{e(item.get("title") or "Untitled opportunity")}</h3>
<p class="organization">{e(item.get("organization") or "Organization unknown")}</p>
<p class="card-description">{e(summary)}</p>
<div class="card-facts"><span>{e('Location: ' + str(location))}</span><span>{e(deadline)}</span><span>{e('Funding: ' + funding)}</span></div>
</article>'''
