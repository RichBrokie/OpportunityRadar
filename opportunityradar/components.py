"""Reusable Streamlit sections; external text stays escaped or plain text."""
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import streamlit as st
from opportunityradar.catalog import INTERESTS, LEVELS, eligibility
from opportunityradar.discovery import TOPICS, discover, DiscoveryError, resolve_api_key, valid_source
from opportunityradar.presentation import card_html
from opportunityradar.ranking import quality_signals
from opportunityradar.storage import save_profile


def apply_style():
    css = Path(__file__).with_name("assets").joinpath("style.css").read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def opportunity_card(item, profile=None):
    with st.container(border=True):
        # card_html escapes every external field; no external markup is trusted.
        st.markdown(card_html(item), unsafe_allow_html=True)
        url = item.get("source_url") or ""
        safe_url = valid_source(url)
        action, details = st.columns([1.4, 2.6])
        if safe_url:
            action.link_button("View demo source" if item.get("is_demo") else "View source", url)
        else:
            action.caption("Source unavailable")
        with details.expander("More details"):
            st.text(item.get("title") or "Untitled opportunity")
            st.text("Organization: " + (item.get("organization") or "Unknown"))
            st.caption("Description" if item.get("is_demo") else "Raw search snippet")
            st.text(item.get("raw_snippet", item.get("summary")) or "No snippet supplied.")
            st.caption("Original source")
            st.text(url or "Source link unavailable")
            if safe_url:
                st.text("Source website: " + (urlsplit(url).hostname or "Unknown"))
            status, reason = eligibility(item, profile)
            st.text(f"Eligibility: {status}. {reason}")
            if item.get("is_demo"):
                st.caption("This is a fictional example. Its organization, criteria and deadline are not real.")
            else:
                st.text("Classification: " + item.get("classification", "Needs review"))
                st.text(item.get("classification_reason") or "Insufficient information to classify this lead.")
                st.text("Stated requirements: " + (item.get("eligibility_requirements") or "Unknown"))
                st.text("Stated location: " + (item.get("location") or "Unknown"))
                st.text("Stated funding: " + (item.get("funding_details") or "Unknown"))
                st.caption("Search snippet only. Category comes from the search topic. A listing or URL signal does not prove the page is official or applications are open. Confirm deadlines, eligibility, location and funding on the source page.")
                st.text("Discovered: " + (item.get("discovered_at") or "Unknown") + " (UTC)")
                _, signals = quality_signals(item)
                st.text("Ranking hints: " + ("; ".join(signals) or "No strong page-quality signals"))
                st.caption("Ranking hints are heuristics, not verification of the organizer or opportunity.")


def discovery_panel(profile, prefix):
    """Only the submit button calls the API; options and reruns are passive."""
    with st.container(border=True):
        with st.form(prefix + "_discovery", border=False):
            st.text_input("What are you looking for?", placeholder="Try machine learning, summer research, or a company…", key=prefix + "_query")
            st.selectbox("Search topic", list(TOPICS), key=prefix + "_topic")
            with st.expander("Search settings"):
                st.checkbox("Allow limited keyless development", key=prefix + "_keyless")
                st.caption("Search uses your saved country, education and interests. A configured Tavily key takes precedence and may use credits. Keyless access is limited by Tavily.")
                st.caption("Up to 5 results per search · 15-minute cache · 12 API attempts per hour. API keys belong in environment settings or Streamlit secrets.")
            submitted = st.form_submit_button("Discover opportunities", type="primary")
        if submitted:
            try:
                try:
                    key = resolve_api_key(st.secrets)
                except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
                    key = resolve_api_key()
                with st.spinner("Finding opportunities for you…"):
                    outcome = discover(st.session_state[prefix + "_topic"], profile,
                                       api_key=key, allow_keyless=st.session_state[prefix + "_keyless"],
                                       keyword=st.session_state[prefix + "_query"])
                message = (f"{'Cached search' if outcome['cached'] else 'Search complete'} · "
                           f"{outcome['found']} results found · {outcome['accepted']} accepted as likely · "
                           f"{outcome['review']} sent for review · {outcome['irrelevant']} saved as irrelevant · "
                           f"{outcome['duplicates']} duplicates skipped · {outcome['invalid']} invalid results skipped. "
                           "Classification counts are newly saved records; accepted does not mean verified or open.")
                if not outcome['found']:
                    message += " No results this time. Try a broader keyword or another topic."
                st.session_state["search_status"] = ("success", message, datetime.now(timezone.utc).isoformat(timespec="seconds"))
            except DiscoveryError as exc:
                st.session_state["search_status"] = ("error", str(exc), datetime.now(timezone.utc).isoformat(timespec="seconds"))
        if "search_status" in st.session_state:
            kind, message, _ = st.session_state["search_status"]
            (st.error if kind == "error" else st.success)(message)


def profile_form(profile):
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
