"""Run with: streamlit run app.py."""
import streamlit as st
from datetime import datetime, timezone
from opportunityradar.discovery import TOPICS, discover, DiscoveryError, resolve_api_key
from opportunityradar.catalog import CATEGORIES, INTERESTS, LEVELS, eligibility, filter_opportunities
from opportunityradar.storage import initialize, load_opportunities, load_profile, save_profile, load_discovered

st.set_page_config(page_title="OpportunityRadar", page_icon="◉", layout="wide")
st.markdown("""<style>
.block-container {max-width: 1180px; padding-top: 2.5rem;}
h1 {letter-spacing: -.045em;} h2, h3 {letter-spacing: -.025em;}
[data-testid="stMetric"] {background: white; border: 1px solid #dae5e9; border-radius: 16px; padding: 18px;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius: 16px;}
[data-testid="stSidebar"] {border-right: 1px solid #dae5e9;}
</style>""", unsafe_allow_html=True)
initialize()
profile = load_profile()
items = load_opportunities()
with st.sidebar:
    st.title("◉ OpportunityRadar")
    st.caption("YOUR NEXT CHAPTER STARTS HERE")
    page = st.radio("Explore", ["Dashboard", "Opportunities", "Your profile"])
    st.divider()
    st.markdown("**Your opportunity radar**")
    st.caption("Search the web on demand or explore the demo collection.")
    st.info("Local, single-user app. Anyone with access to this app can see and edit this profile.")

st.caption("OPPORTUNITYRADAR / " + page.upper())
st.title({"Dashboard": "A little direction. A lot of possibility.", "Opportunities": "Find your next opportunity.", "Your profile": "Make your radar yours."}[page])
st.info("DISCOVERED results are unverified search leads. DEMO listings are fictional. Always confirm details at the original source before applying.")


def card(item):
    with st.container(border=True):
        demo = item.get("is_demo", False)
        label = "DEMO" if demo else "DISCOVERED · UNVERIFIED"
        location = {True: "REMOTE", False: "IN PERSON"}.get(item.get("remote"), "LOCATION UNKNOWN")
        st.caption(f"{label} · {item['category'].upper()} · {location}")
        st.subheader(item["title"])
        st.text(item.get("organization") or "Organization unknown")
        st.text(item["summary"])
        st.caption("Interests: " + (" · ".join(item.get("interests") or []) or "Unknown"))
        funding = {True: "Yes", False: "No"}.get(item.get("funded"), "Unknown")
        st.write(f"**{'Example deadline' if demo else 'Verified deadline'}:** {item.get('deadline') or 'Unknown'} · **Funded:** {funding}")
        status, reason = eligibility(item, profile)
        st.markdown(f"**Eligibility: {status}**")
        st.caption(reason)
        if not demo:
            st.text("Stated eligibility (unverified): " + (item.get("eligibility_requirements") or "Unknown"))
            st.caption("Category is based on the search topic. Other details are unverified snippet claims.")
            st.caption("Discovered: " + item["discovered_at"] + " (UTC)")
        st.link_button("View placeholder source ↗" if demo else "Check original source ↗", item["source_url"])
        st.caption("Source URL: " + item["source_url"] + (" — example.com placeholder; no application available." if demo else ""))



if page == "Your profile":
    st.write("Save your preferences locally to tailor searches and your browsing experience.")
    current = profile or {}
    with st.form("profile"):
        left, right = st.columns(2)
        country = left.text_input("Country", current.get("country", ""), placeholder="e.g. Pakistan")
        education = right.selectbox("Education level", LEVELS, index=LEVELS.index(current.get("education_level", "Undergraduate")))
        year = left.selectbox("Academic year", ["Not applicable", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5+"], index=["Not applicable", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5+"].index(current.get("academic_year", "Year 1")))
        interests = st.multiselect("CS interests", INTERESTS, default=current.get("interests", []))
        remote = st.checkbox("Prefer remote opportunities", current.get("remote_only", False))
        funded = st.checkbox("Prefer funded opportunities", current.get("funded_only", False))
        st.caption("Preferences set the initial filters on Opportunities. Academic year is stored for future matching.")
        if st.form_submit_button("Save profile", type="primary"):
            if not country.strip():
                st.error("Please enter your country.")
            else:
                save_profile(dict(country=country.strip(), education_level=education, academic_year=year, interests=interests, remote_only=remote, funded_only=funded))
                # Refresh initial browsing preferences after an explicit save.
                for key in ("filter_interests", "filter_remote", "filter_funded"):
                    st.session_state.pop(key, None)
                st.success("Profile saved locally. Open Opportunities to explore your matches.")
elif page == "Dashboard":
    st.write("Discover what could come next — explore the demo collection, then tell us what matters to you.")
    cols = st.columns(3)
    cols[0].metric("Demo opportunities", len(items))
    cols[1].metric("Opportunity types", len({i["category"] for i in items}))
    cols[2].metric("Your profile", "Saved" if profile else "Not set")
    st.subheader("Start with a possibility")
    st.caption("A selection from the fictional collection. Browse all listings using Opportunities in the sidebar.")
    columns = st.columns(2)
    for index, item in enumerate(items[:2]):
        with columns[index]:
            card(item)
    st.info("Open Opportunities to search with Tavily. Email delivery and scheduling are not implemented.")
else:
    collection = st.radio("Collection", ["Discovered", "Demo"], horizontal=True)
    if collection == "Discovered":
        st.caption("Search sends your saved country, education and interests to Tavily. One topic per click, up to 5 results. Cached for 15 minutes; maximum 12 API requests per rolling hour across this local app.")
        topic = st.selectbox("Search topic", list(TOPICS))
        keyless = st.checkbox("Allow limited keyless development", value=False)
        st.caption("Keyless availability and quotas are controlled by Tavily. A configured key takes precedence and may consume account credits.")
        if st.button("Discover opportunities", type="primary"):
            try:
                try:
                    key = resolve_api_key(st.secrets)
                except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
                    key = resolve_api_key()
                with st.spinner("Searching for opportunities…"):
                    outcome = discover(topic, profile, api_key=key, allow_keyless=keyless)
                message = (f"{'Cached search' if outcome['cached'] else 'Search complete'}: "
                           f"{outcome['results']} usable results; {outcome['added']} new saved. "
                           "Duplicates keep their original discovery time.")
                if not outcome['results']:
                    message = "No usable search results. Try another topic or adjust your profile."
                st.session_state["search_status"] = ("success", message, datetime.now(timezone.utc).isoformat(timespec="seconds"))
            except DiscoveryError as exc:
                st.session_state["search_status"] = ("error", str(exc), datetime.now(timezone.utc).isoformat(timespec="seconds"))
        if "search_status" in st.session_state:
            kind, message, timestamp = st.session_state["search_status"]
            (st.error if kind == "error" else st.info)(message)
            st.caption("Last search action: " + timestamp + " (UTC)")
        items = load_discovered()
    else:
        st.warning("DEMO ONLY — These listings and their criteria are fictional examples.")
    preferences = profile or {}
    with st.container(border=True):
        a, b = st.columns(2)
        categories = a.multiselect("Opportunity type", CATEGORIES)
        keyword = b.text_input("Search by keyword", placeholder="Title, organization or summary")
        interests = st.multiselect("Filter by interests", INTERESTS, default=preferences.get("interests", []), key="filter_interests")
        a, b = st.columns(2)
        remote = a.checkbox("Remote only", preferences.get("remote_only", False), key="filter_remote")
        funded = b.checkbox("Funded only", preferences.get("funded_only", False), key="filter_funded")
    results = filter_opportunities(items, categories, keyword, interests, remote, funded)
    st.caption(f"{len(results)} of {len(items)} opportunities · Interests match any selected interest. Unknown funding/location is excluded by strict filters.")
    if not results:
        st.info("No demo opportunities match. Clear a filter or try a broader keyword." if collection == "Demo" else "No discovered opportunities match. Run a search or clear filters; unknown interests, location or funding may be excluded.")
    columns = st.columns(2)
    for index, item in enumerate(results):
        with columns[index % 2]:
            card(item)
