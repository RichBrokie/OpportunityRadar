"""OpportunityRadar. Run with: python -m streamlit run app.py."""
import streamlit as st
from opportunityradar.catalog import CATEGORIES, INTERESTS, filter_opportunities
from opportunityradar.components import apply_style, discovery_panel, opportunity_card, profile_form
from opportunityradar.ranking import SORTS, sort_opportunities
from opportunityradar.storage import initialize, load_discovered, load_opportunities, load_profile

st.set_page_config(page_title="OpportunityRadar", page_icon="◉", layout="wide")
apply_style()
initialize()
profile = load_profile()


def navigate_category(category):
    st.session_state["navigation"] = "Opportunities"
    st.session_state["category_filter"] = [category]
    st.session_state["collection"] = "Discovered"


def sidebar():
    with st.sidebar:
        st.subheader("◉ OpportunityRadar")
        st.caption("AHEAD OF YOUR NEXT CHAPTER")
        st.divider()
        page = st.radio("Workspace", ["Dashboard", "Opportunities", "Your profile"], key="navigation", label_visibility="collapsed")
        st.divider()
        st.caption("YOUR PREFERENCES")
        if profile:
            st.text(profile["country"] + " · " + profile["education_level"])
            st.caption(" · ".join(profile.get("interests") or []) or "Add interests to personalize discovery.")
        else:
            st.caption("Add your student profile for more relevant searches.")
        with st.expander("About your workspace"):
            st.caption("Single-user local workspace. Anyone with app access shares this profile. Discovered results are unverified; demo listings are fictional.")
        return page


def dashboard():
    st.caption("YOUR NEXT CHAPTER")
    st.title("Good things are ahead.")
    st.write("Find internships, research and experiences that move you forward.")
    discovery_panel(profile, "dashboard")
    items = load_discovered()  # Include results from a search made in this rerun.
    matched = filter_opportunities(items, interests=(profile or {}).get("interests", []),
                                   remote_only=(profile or {}).get("remote_only", False),
                                   funded_only=(profile or {}).get("funded_only", False))
    a, b, c = st.columns(3)
    a.metric("Discovered", len(items))
    b.metric("Matching preferences", len(matched))
    c.metric("Your profile", "Saved" if profile else "Not set")
    st.caption("Matches reflect filters, not eligibility. All discovered results need source review.")
    st.subheader("Explore by category")
    columns = st.columns(3)
    for index, category in enumerate(CATEGORIES):
        columns[index % 3].button(category, key="quick_" + category, on_click=navigate_category, args=(category,), use_container_width=True)
    st.subheader("Recently discovered")
    if not items:
        st.info("Your radar is ready. Run your first search above to start your collection.")
    for item in sort_opportunities(items, "Recently discovered")[:3]:
        opportunity_card(item, profile)


def opportunities():
    st.title("Find your next opportunity.")
    st.write("A focused collection of possibilities, shaped around you.")
    collection = st.radio("Collection", ["Discovered", "Demo"], horizontal=True, key="collection")
    if collection == "Discovered":
        discovery_panel(profile, "browse")
        items = load_discovered()
    else:
        st.caption("DEMO COLLECTION · Fictional examples for exploring the platform.")
        items = load_opportunities()
    preferences = profile or {}
    with st.container(border=True):
        st.text_input("Search this collection", placeholder="Filter by title, organization or keyword", key="browse_filter")
        a, b = st.columns([2, 1])
        categories = a.multiselect("Opportunity type", CATEGORIES, key="category_filter")
        order = b.selectbox("Sort by", SORTS, key="sort_order")
        with st.expander("Personalize filters"):
            interests = st.multiselect("Filter by interests", INTERESTS, default=preferences.get("interests", []), key="filter_interests")
            a, b = st.columns(2)
            remote = a.checkbox("Remote only", preferences.get("remote_only", False), key="filter_remote")
            funded = b.checkbox("Funded only", preferences.get("funded_only", False), key="filter_funded")
            st.caption("Interests match any selected interest. Unknown values are excluded by active filters; clear preferences to broaden results.")
    results = filter_opportunities(items, categories, st.session_state["browse_filter"], interests, remote, funded)
    st.caption(f"{len(results)} opportunities · {len(items)} in your {collection.lower()} collection")
    if not results:
        st.info("No demo opportunities match. Clear a filter or try a broader keyword." if collection == "Demo" else "No opportunities to show yet. Discover new results or broaden your filters.")
    for item in sort_opportunities(results, order):
        opportunity_card(item, profile)


page = sidebar()
if page == "Dashboard":
    dashboard()
elif page == "Opportunities":
    opportunities()
else:
    st.title("Make your radar yours.")
    profile_form(profile)
