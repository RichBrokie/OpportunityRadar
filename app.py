"""Run with: streamlit run app.py."""
import streamlit as st
from opportunityradar.catalog import CATEGORIES, INTERESTS, LEVELS, eligibility, filter_opportunities
from opportunityradar.storage import initialize, load_opportunities, load_profile, save_profile

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
    st.markdown("**Foundation · Demo edition**")
    st.caption("Explore sample opportunities and shape your student profile.")
    st.info("Local, single-user app. Anyone with access to this app can see and edit this profile.")

st.caption("OPPORTUNITYRADAR / " + page.upper())
st.title({"Dashboard": "A little direction. A lot of possibility.", "Opportunities": "Find your next opportunity.", "Your profile": "Make your radar yours."}[page])
st.warning("DEMO ONLY — All listings, organizations, deadlines and criteria are fictional examples. No live opportunities are being discovered or emailed.")


def card(item):
    with st.container(border=True):
        st.caption(f"DEMO · {item['category'].upper()} · {'REMOTE' if item['remote'] else 'IN PERSON'}")
        st.subheader(item["title"])
        st.write(item["organization"])
        st.write(item["summary"])
        st.caption("Interests: " + " · ".join(item["interests"]))
        st.write(f"**Example deadline:** {item['deadline']} · **Funded:** {'Yes' if item['funded'] else 'No'}")
        status, reason = eligibility(item, profile)
        st.markdown(f"**Eligibility: {status}**")
        st.caption(reason)
        st.link_button("View placeholder source ↗", item["source_url"])
        st.caption("Source URL: " + item["source_url"] + " — example.com placeholder; no application available.")


if page == "Your profile":
    st.write("Save your preferences locally to tailor your demo browsing experience.")
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
    st.info("Coming later: online discovery with Tavily, email digests with Resend, and scheduled updates. These integrations are not active.")
else:
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
    st.caption(f"{len(results)} of {len(items)} demo opportunities · Interests match any selected interest")
    if not results:
        st.info("No demo opportunities match. Clear a filter or try a broader keyword.")
    columns = st.columns(2)
    for index, item in enumerate(results):
        with columns[index % 2]:
            card(item)
