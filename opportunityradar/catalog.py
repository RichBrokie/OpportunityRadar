"""Fictional fixtures and transparent filtering/eligibility rules."""
from datetime import date

INTERESTS = ["Artificial intelligence", "Web development", "Cybersecurity", "Data science", "Systems", "Human-computer interaction"]
LEVELS = ["High school", "Undergraduate", "Master's", "PhD"]
CATEGORIES = ["Internship", "Research", "Scholarship", "Fellowship", "Hackathon"]


def demo_opportunities():
    """Fixed fictional data: dates and criteria are examples, never live claims."""
    rows = [
        ("Software internship", "Demo Orbit Studio", "Internship", "2027-06-15", "Build accessible web tools with a fictional student engineering team.", ["Web development", "Systems"], True, True, [], ["Undergraduate", "Master's"]),
        ("AI research programme", "Demo Cedar Lab", "Research", "2027-04-30", "Explore machine learning evaluation in a fictional summer research programme.", ["Artificial intelligence", "Data science"], False, True, ["Pakistan"], ["Undergraduate", "Master's"]),
        ("Computing scholarship", "Demo Horizon Foundation", "Scholarship", "2027-03-01", "An illustrative tuition award for students studying computer science.", ["Systems", "Data science"], False, True, [], ["Undergraduate"]),
        ("Security fellowship", "Demo Signal Institute", "Fellowship", "2027-05-20", "Practice responsible security research with a fictional mentor cohort.", ["Cybersecurity"], True, True, [], ["Master's", "PhD"]),
        ("Build for good weekend", "Demo Open Campus", "Hackathon", "2027-02-10", "A fictional weekend of collaborative prototyping for community projects.", ["Web development", "Human-computer interaction"], True, False, [], LEVELS),
        ("Data discovery internship", "Demo Maple Analytics", "Internship", "2027-07-01", "Learn how a fictional analytics team turns datasets into useful insights.", ["Data science", "Artificial intelligence"], False, True, ["Canada"], ["Undergraduate", "Master's"]),
    ]
    return [dict(id=i, title=f"DEMO · {r[0]}", organization=r[1], category=r[2], deadline=r[3], summary=r[4], interests=r[5], remote=r[6], funded=r[7], countries=r[8], education_levels=r[9], source_url=f"https://example.com/demo-opportunity-{i}", is_demo=True) for i, r in enumerate(rows, 1)]


def filter_opportunities(items, categories=(), keyword="", interests=(), remote_only=False, funded_only=False):
    query = keyword.strip().casefold()
    return [item for item in items
            if (not categories or item["category"] in categories)
            and (not query or query in " ".join([item["title"], item["organization"], item["summary"]]).casefold())
            and (not interests or set(interests).intersection(item["interests"]))
            and (not remote_only or item["remote"])
            and (not funded_only or item["funded"])]


def eligibility(item, profile, today=None):
    """A basic country/education check, never a verified eligibility decision."""
    if date.fromisoformat(item["deadline"]) < (today or date.today()):
        return "Deadline passed", "This example deadline has passed."
    if not profile:
        return "Profile needed", "Save your profile to compare the demo criteria."
    if item["countries"] and profile["country"].strip().casefold() not in {c.casefold() for c in item["countries"]}:
        return "Criteria mismatch", "Example country requirement: " + ", ".join(item["countries"])
    if profile["education_level"] not in item["education_levels"]:
        return "Criteria mismatch", "Example education requirement: " + ", ".join(item["education_levels"])
    return "Potential match", "Country and education match the demo rules. Full eligibility is unverified."
