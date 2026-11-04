import json

import pytest

from opportunityradar.discovery import parse_result
from opportunityradar.quality import (LIKELY, REVIEW, IRRELEVANT, classify,
                                      clean_summary, normalize_record)
from opportunityradar import storage


@pytest.mark.parametrize("title,url,body,expected", [
    ("Top 10 internships", "https://school.edu/apply", "Apply for internships for students", IRRELEVANT),
    ("How to get a software internship", "https://example.org/jobs", "Apply now", IRRELEVANT),
    ("Career advice for students", "https://example.org/advice", "Find an internship", IRRELEVANT),
    ("Atlas hackathon", "https://reddit.com/r/cs/post", "Register as a student", IRRELEVANT),
    ("Atlas fellowship", "https://example.org/blog/atlas", "Applications for undergraduates", REVIEW),
    ("Internships", "https://school.edu/careers", "Browse applications", REVIEW),
    ("Software internship opportunities", "https://school.edu/jobs/students", "Students may apply", REVIEW),
    ("Software internship", "https://employer.example/jobs", "Applications for students", REVIEW),
    ("Student hackathon", "https://school.edu/event", "", REVIEW),
    ("Software internship", "https://school.edu/jobs", "", REVIEW),
    ("Atlas fellowship", "https://school.edu/fellowships/atlas", "Undergraduates join a 10 week programme.", LIKELY),
    ("Software engineering intern", "https://employer.example/jobs/123", "Responsibilities include testing. Undergraduate students may apply.", LIKELY),
    ("Cedar research programme", "https://school.edu/programs/cedar", "A 12 week placement for undergraduate students.", LIKELY),
    ("Orbit scholarship", "https://school.edu/scholarships/orbit", "Eligibility includes undergraduate enrolment.", LIKELY),
    ("Campus hackathon", "https://event.example/register", "Participants register in teams.", LIKELY),
    ("Atlas fellowship", "https://reddit.com.example.org/apply", "Applications for students", LIKELY),
    ("Cooking recipes", "https://example.org/food", "Make soup with carrots.", IRRELEVANT),
    (None, None, None, REVIEW),
])
def test_conservative_classification(title, url, body, expected):
    item = dict(title=title, source_url=url, raw_snippet=body)
    assert classify(item)[0] == expected


def test_clean_summary_retains_facts_and_removes_noise():
    raw = """Home | Menu | Skip to content
Organization: Cedar Lab
Location: remote
Funding: funded
Eligibility: Undergraduate students
Cedar placement
Build accessible tools. Build accessible tools!  Work with mentors.
Read more | https://example.org/apply
Accept all cookies. Privacy policy. All rights reserved.
<script>steal()</script><b>Learn testing.</b>"""
    summary = clean_summary(raw, omit=("Cedar placement", "Cedar Lab"))
    assert summary == "Build accessible tools. Work with mentors. Learn testing."
    record = normalize_record(dict(title="Cedar placement", summary=raw))
    assert record["raw_snippet"] == raw
    assert record["summary"] == summary


@pytest.mark.parametrize("raw", [None, "", "Home | Menu", "x" * 500, "A sentence about testing. " * 100, "Word " * 200])
def test_empty_and_long_snippets(raw):
    summary = clean_summary(raw)
    assert summary and len(summary) < 180
    assert "  " not in summary


def test_full_raw_snippet_preserved_and_no_open_status_inferred():
    raw = "  Organization: Cedar\nLocation: Berlin\nFunding: stipend\nDeadline: 2028-05-01\n" + "Learn systems. " * 100
    record = parse_result(dict(title="Cedar internship", url="https://school.edu/apply", content=raw), "Internship", "2026-11-04")
    assert record["raw_snippet"] == raw
    assert len(record["summary"]) < 180
    assert record["location"] == "Berlin"
    assert record["remote"] is None and record["funded"] is None
    assert record["deadline"] is None and record["verified"] is False
    assert "open" not in record.get("status", "").lower()


def test_legacy_sqlite_is_adapted_without_rewriting_data(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    storage.initialize(path)
    profile = dict(country="Pakistan", education_level="Undergraduate")
    storage.save_profile(profile, path)
    old = dict(title="Cedar internship", summary="Learn systems. Learn systems.",
               source_url="https://school.edu/apply", is_demo=False, discovered_at="2026-01-01")
    payload = json.dumps(old)
    with storage.connection(path) as db:
        db.execute("INSERT INTO discovered(payload) VALUES (?)", (payload,))
    storage.store_search("old query", [old], path)
    storage.reserve_search(path)
    storage.initialize(path)
    loaded = storage.load_discovered(path)[0]
    assert loaded["raw_snippet"] == old["summary"]
    assert loaded["summary"] == "Learn systems."
    assert loaded["classification"] == REVIEW
    assert loaded["discovered_at"] == "2026-01-01"
    assert storage.load_profile(path) == profile
    assert storage.cached_search("old query", path) == [old]
    assert storage.save_discovered([loaded], path) == 0
    with storage.connection(path) as db:
        assert db.execute("SELECT payload FROM discovered").fetchone()[0] == payload
        assert db.execute("SELECT COUNT(*) FROM search_attempts").fetchone()[0] == 1
    assert len(storage.load_opportunities(path)) == 6
