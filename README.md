# Macro Dashboard — Economic Calendar

A multi-page Streamlit dashboard for tracking Asian economic events.

## Setup

```bash
# 1. Clone / copy this folder
cd economic_dashboard

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
streamlit run app.py
```

## Finnhub API Key

1. Go to https://finnhub.io and register (free, no credit card)
2. Copy the API key from your dashboard
3. Paste it into the sidebar input when the app is running

The free tier allows 60 API calls/minute — well within what this dashboard needs.

## Project Structure

```
economic_dashboard/
├── app.py               # Entry point, page navigation, global styles
├── pages/
│   └── calendar.py      # 4-week economic calendar page
└── requirements.txt
```

## Adding More Pages

Create a new file in `pages/` (e.g. `pages/charts.py`) and register it in `app.py`:

```python
pg = st.navigation([
    st.Page("pages/calendar.py", title="Calendar", icon="📅"),
    st.Page("pages/charts.py",   title="Charts",   icon="📈"),
])
```
