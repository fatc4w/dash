import streamlit as st

st.set_page_config(
    page_title="Macro Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom global styles
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

[data-testid="stSidebar"] {
    background: #0a0a0f;
    border-right: 1px solid #1e1e2e;
}

[data-testid="stSidebar"] * {
    color: #c0c0d0 !important;
}

.stApp {
    background: #06060b;
}

h1, h2, h3 {
    font-family: 'IBM Plex Mono', monospace !important;
    letter-spacing: -0.02em;
}
</style>
""", unsafe_allow_html=True)

pg = st.navigation([
    st.Page("pages/calendar.py", title="Calendar", icon="📅"),
])

pg.run()
