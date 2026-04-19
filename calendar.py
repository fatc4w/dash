import streamlit as st
import requests
import json
from datetime import datetime, timedelta, date
import calendar

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

COUNTRY_CONFIG = {
    "SG": {"name": "Singapore",   "flag": "🇸🇬"},
    "MY": {"name": "Malaysia",    "flag": "🇲🇾"},
    "ID": {"name": "Indonesia",   "flag": "🇮🇩"},
    "TH": {"name": "Thailand",    "flag": "🇹🇭"},
    "VN": {"name": "Vietnam",     "flag": "🇻🇳"},
    "CN": {"name": "China",       "flag": "🇨🇳"},
    "KR": {"name": "South Korea", "flag": "🇰🇷"},
}

TARGET_COUNTRIES = set(COUNTRY_CONFIG.keys())

IMPACT_COLOR = {
    "high":   "#ef4444",
    "medium": "#f59e0b",
    "low":    "#6b7280",
    None:     "#6b7280",
}

IMPACT_LABEL = {
    "high":   "HIGH",
    "medium": "MED",
    "low":    "LOW",
    None:     "—",
}

# ─────────────────────────────────────────────
# DATE HELPERS
# ─────────────────────────────────────────────

def get_4week_range() -> tuple[date, date]:
    """Returns Monday of current week → Sunday 3 weeks later (28 days total)."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())  # ISO: Monday=0
    sunday = monday + timedelta(days=27)
    return monday, sunday


def build_week_grid(start_monday: date) -> list[list[date]]:
    """Returns 4 weeks × 7 days grid starting from start_monday."""
    return [
        [start_monday + timedelta(days=w * 7 + d) for d in range(7)]
        for w in range(4)
    ]


# ─────────────────────────────────────────────
# FINNHUB FETCH
# ─────────────────────────────────────────────

@st.cache_data(ttl=900)  # 15-minute cache
def fetch_economic_events(from_date: str, to_date: str, api_key: str) -> list[dict]:
    """
    Calls GET https://finnhub.io/api/v1/calendar/economic
    with ?from=YYYY-MM-DD&to=YYYY-MM-DD&token=...

    Returns the list of event dicts from the `economicCalendar` key,
    filtered to our target countries.
    """
    url = "https://finnhub.io/api/v1/calendar/economic"
    params = {"from": from_date, "to": to_date, "token": api_key}

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        events = data.get("economicCalendar", [])
    except requests.exceptions.RequestException as e:
        st.warning(f"Finnhub API error: {e}")
        return []
    except (json.JSONDecodeError, KeyError):
        st.warning("Unexpected response format from Finnhub.")
        return []

    # Filter to target countries (Finnhub uses 2-letter uppercase country codes)
    filtered = [e for e in events if e.get("country", "").upper() in TARGET_COUNTRIES]
    return filtered


def group_events_by_date(events: list[dict]) -> dict[str, list[dict]]:
    """Groups event list by the `time` field (YYYY-MM-DD prefix)."""
    grouped: dict[str, list[dict]] = {}
    for event in events:
        raw_time = event.get("time", "")
        # Finnhub time field is either a full ISO datetime or just YYYY-MM-DD
        day_key = raw_time[:10] if raw_time else ""
        if day_key:
            grouped.setdefault(day_key, []).append(event)
    return grouped


# ─────────────────────────────────────────────
# UI COMPONENTS
# ─────────────────────────────────────────────

def render_event_pill(event: dict, today: date):
    """Renders a compact event pill inside a calendar cell."""
    country_code = event.get("country", "").upper()
    flag = COUNTRY_CONFIG.get(country_code, {}).get("flag", "🌐")
    event_name = event.get("event", "Unknown Event")
    impact = (event.get("impact") or "").lower() or None
    dot_color = IMPACT_COLOR.get(impact, IMPACT_COLOR[None])

    # Truncate long names for the pill
    short_name = event_name if len(event_name) <= 32 else event_name[:30] + "…"

    pill_html = f"""
    <div class="event-pill impact-{impact or 'none'}" 
         title="{event_name} ({country_code})"
         style="border-left: 2px solid {dot_color};">
        <span class="event-flag">{flag}</span>
        <span class="event-name">{short_name}</span>
    </div>
    """
    return pill_html


def render_event_detail(event: dict, today: date) -> None:
    """Renders a detailed popover/expander for a single event."""
    country_code = event.get("country", "").upper()
    flag = COUNTRY_CONFIG.get(country_code, {}).get("flag", "🌐")
    country_name = COUNTRY_CONFIG.get(country_code, {}).get("name", country_code)
    event_name = event.get("event", "Unknown Event")
    impact = (event.get("impact") or "").lower() or None
    impact_color = IMPACT_COLOR.get(impact, IMPACT_COLOR[None])
    impact_label = IMPACT_LABEL.get(impact, "—")

    raw_time = event.get("time", "")
    event_date = datetime.strptime(raw_time[:10], "%Y-%m-%d").date() if raw_time else None
    is_past = event_date is not None and event_date < today

    prev_val  = event.get("prev")
    estimate  = event.get("estimate")
    actual    = event.get("actual")
    unit      = event.get("unit", "")

    def fmt(val):
        if val is None or val == "":
            return "—"
        try:
            return f"{float(val):,.3f}{' ' + unit if unit else ''}"
        except (ValueError, TypeError):
            return str(val)

    with st.container():
        st.markdown(f"""
        <div class="detail-card">
            <div class="detail-header">
                <span class="detail-flag">{flag}</span>
                <div class="detail-title-block">
                    <div class="detail-event-name">{event_name}</div>
                    <div class="detail-country">{country_name}</div>
                </div>
                <div class="detail-impact" style="color:{impact_color}; border-color:{impact_color};">
                    {impact_label}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Previous", fmt(prev_val))
        with col2:
            st.metric("Forecast / Estimate", fmt(estimate))
        with col3:
            if is_past:
                st.metric("Actual", fmt(actual))
            else:
                st.metric("Actual", "Pending")

        if raw_time and len(raw_time) > 10:
            st.caption(f"🕐 {raw_time[11:16]} UTC")


# ─────────────────────────────────────────────
# MAIN PAGE
# ─────────────────────────────────────────────

def main():
    # ── Styles ──────────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

    /* ── Base ─────────────────────── */
    .stApp { background: #06060b; }

    /* ── Header ───────────────────── */
    .cal-header {
        display: flex;
        align-items: baseline;
        gap: 12px;
        margin-bottom: 28px;
    }
    .cal-title {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 22px;
        font-weight: 600;
        color: #e8e8f0;
        letter-spacing: -0.03em;
    }
    .cal-subtitle {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 13px;
        color: #555570;
        font-weight: 300;
    }

    /* ── Legend ───────────────────── */
    .legend-row {
        display: flex;
        gap: 18px;
        margin-bottom: 20px;
        align-items: center;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 5px;
        font-size: 11px;
        font-family: 'IBM Plex Mono', monospace;
        color: #666680;
    }
    .legend-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        display: inline-block;
    }

    /* ── Day-of-week header ───────── */
    .dow-row {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 4px;
        margin-bottom: 4px;
    }
    .dow-cell {
        text-align: center;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        font-weight: 600;
        color: #3a3a5c;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        padding: 6px 0;
    }

    /* ── Calendar grid ────────────── */
    .cal-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        grid-template-rows: repeat(4, 1fr);
        gap: 4px;
        width: 100%;
    }

    /* ── Individual day cell ──────── */
    .day-cell {
        background: #0e0e1a;
        border: 1px solid #16162a;
        border-radius: 6px;
        padding: 8px 8px 6px;
        min-height: 110px;
        transition: border-color 0.15s ease;
        position: relative;
        overflow: hidden;
    }
    .day-cell:hover { border-color: #2a2a4a; }

    .day-cell.today {
        background: #0f0f20;
        border-color: #3b3bff44;
        box-shadow: 0 0 0 1px #3b3bff22 inset;
    }
    .day-cell.today .day-num {
        color: #7b7bff;
        background: #1a1a3a;
        border-radius: 4px;
        padding: 1px 5px;
    }
    .day-cell.past { opacity: 0.55; }
    .day-cell.other-month .day-num { color: #282838; }
    .day-cell.weekend { background: #0c0c16; }

    .day-num {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        color: #404060;
        margin-bottom: 5px;
        display: inline-block;
    }
    .day-month-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 9px;
        color: #2a2a3a;
        margin-left: 3px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    /* ── Event pill ───────────────── */
    .event-pill {
        display: flex;
        align-items: center;
        gap: 4px;
        background: #13131f;
        border-radius: 3px;
        padding: 2px 5px;
        margin-bottom: 2px;
        cursor: pointer;
        transition: background 0.12s ease;
        overflow: hidden;
    }
    .event-pill:hover { background: #1a1a2e; }

    .event-flag { font-size: 10px; flex-shrink: 0; }
    .event-name {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 9.5px;
        color: #8888aa;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
    }

    .event-pill.impact-high   .event-name { color: #cc8888; }
    .event-pill.impact-medium .event-name { color: #b89060; }

    /* ── Detail card ──────────────── */
    .detail-card {
        background: #0e0e1a;
        border: 1px solid #1e1e35;
        border-radius: 8px;
        padding: 16px 18px;
        margin-bottom: 12px;
    }
    .detail-header {
        display: flex;
        align-items: flex-start;
        gap: 12px;
    }
    .detail-flag { font-size: 28px; flex-shrink: 0; }
    .detail-title-block { flex: 1; }
    .detail-event-name {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 15px;
        font-weight: 600;
        color: #d0d0e8;
        margin-bottom: 2px;
    }
    .detail-country {
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 12px;
        color: #555570;
    }
    .detail-impact {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        font-weight: 600;
        border: 1px solid;
        border-radius: 3px;
        padding: 2px 6px;
        flex-shrink: 0;
        letter-spacing: 0.08em;
    }

    /* ── Streamlit overrides ──────── */
    .stMetric label {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 10px !important;
        color: #555570 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .stMetric [data-testid="metric-container"] > div:nth-child(2) {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 16px !important;
        color: #c0c0d8 !important;
    }
    [data-testid="stExpander"] {
        background: #0e0e1a !important;
        border: 1px solid #1e1e35 !important;
        border-radius: 6px !important;
    }
    div[data-testid="stExpander"] summary {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        color: #666688;
    }

    /* ── Sidebar extras ───────────── */
    .sidebar-section-title {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        color: #333355;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        margin: 18px 0 8px;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Sidebar: API key + filters ──────────────────────────
    with st.sidebar:
        st.markdown('<div class="sidebar-section-title">Configuration</div>', unsafe_allow_html=True)
        api_key = st.sidebar.text_input(
            "Finnhub API Key",
            value = st.secrets.get("FINNHUB_API_KEY", ""),
            type="password",
            placeholder="paste your free key here",
            help="Get a free key at https://finnhub.io — no credit card needed",
        )

        st.markdown('<div class="sidebar-section-title">Countries</div>', unsafe_allow_html=True)
        selected_countries = {}
        for code, info in COUNTRY_CONFIG.items():
            selected_countries[code] = st.checkbox(
                f"{info['flag']} {info['name']}", value=True, key=f"country_{code}"
            )
        active_countries = {c for c, v in selected_countries.items() if v}

        st.markdown('<div class="sidebar-section-title">Impact Filter</div>', unsafe_allow_html=True)
        show_high   = st.checkbox("🔴 High",   value=True)
        show_medium = st.checkbox("🟡 Medium", value=True)
        show_low    = st.checkbox("⚫ Low",    value=True)

        allowed_impacts = set()
        if show_high:   allowed_impacts.add("high")
        if show_medium: allowed_impacts.add("medium")
        if show_low:    allowed_impacts.update({"low", None, ""})

    # ── Date range ──────────────────────────────────────────
    today = date.today()
    start_monday, end_sunday = get_4week_range()
    week_grid = build_week_grid(start_monday)

    # ── Page header ─────────────────────────────────────────
    month_labels = sorted({d.strftime("%B %Y") for week in week_grid for d in week})
    range_label = " · ".join(month_labels)

    st.markdown(f"""
    <div class="cal-header">
        <span class="cal-title">ECONOMIC CALENDAR</span>
        <span class="cal-subtitle">{range_label}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Legend ───────────────────────────────────────────────
    st.markdown("""
    <div class="legend-row">
        <span class="legend-item"><span class="legend-dot" style="background:#ef4444"></span> High Impact</span>
        <span class="legend-item"><span class="legend-dot" style="background:#f59e0b"></span> Medium Impact</span>
        <span class="legend-item"><span class="legend-dot" style="background:#444460"></span> Low Impact</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Fetch events ─────────────────────────────────────────
    events_by_date: dict[str, list[dict]] = {}

    if api_key:
        raw_events = fetch_economic_events(
            from_date=start_monday.isoformat(),
            to_date=end_sunday.isoformat(),
            api_key=api_key,
        )
        # Apply country + impact filters
        filtered = [
            e for e in raw_events
            if e.get("country", "").upper() in active_countries
            and (e.get("impact") or "").lower() in allowed_impacts
        ]
        events_by_date = group_events_by_date(filtered)
    else:
        st.info("🔑 Enter your Finnhub API key in the sidebar to load economic events. Free keys are available at [finnhub.io](https://finnhub.io).", icon="💡")

    # ── Day-of-week header ───────────────────────────────────
    st.markdown("""
    <div class="dow-row">
        <div class="dow-cell">Mon</div>
        <div class="dow-cell">Tue</div>
        <div class="dow-cell">Wed</div>
        <div class="dow-cell">Thu</div>
        <div class="dow-cell">Fri</div>
        <div class="dow-cell">Sat</div>
        <div class="dow-cell">Sun</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Render 4 weeks ───────────────────────────────────────
    # We use st.columns(7) per week for reliable layout.
    # Event details open below each week's row in an expander-per-event pattern.

    for week_idx, week in enumerate(week_grid):
        cols = st.columns(7, gap="small")

        # Track which events were clicked this week
        clicked_events_this_week: list[tuple[date, dict]] = []

        for day_idx, day in enumerate(week):
            day_key = day.isoformat()
            is_today   = (day == today)
            is_past    = (day < today)
            is_weekend = (day_idx >= 5)
            is_other   = (day.month != today.month and
                          (week_idx == 0 and day.month != start_monday.month or
                           week_idx == 3 and day.month != end_sunday.month))

            day_events = events_by_date.get(day_key, [])

            # Build CSS classes
            classes = ["day-cell"]
            if is_today:   classes.append("today")
            elif is_past:  classes.append("past")
            if is_weekend: classes.append("weekend")

            # Day number label — show month abbreviation on the 1st
            day_label = str(day.day)
            month_suffix = f'<span class="day-month-label">{day.strftime("%b")}</span>' if day.day == 1 else ""

            # Build event pills HTML
            pills_html = ""
            for ev in day_events[:6]:  # cap visible pills per cell
                pills_html += render_event_pill(ev, today)
            if len(day_events) > 6:
                pills_html += f'<div style="font-size:9px;color:#444460;padding:1px 5px;">+{len(day_events)-6} more</div>'

            cell_html = f"""
            <div class="{' '.join(classes)}">
                <span class="day-num">{day_label}</span>{month_suffix}
                {pills_html}
            </div>
            """
            with cols[day_idx]:
                st.markdown(cell_html, unsafe_allow_html=True)

                # One expander per event for details
                for ev in day_events:
                    country_code = ev.get("country", "").upper()
                    flag = COUNTRY_CONFIG.get(country_code, {}).get("flag", "🌐")
                    short_name = ev.get("event", "")[:28]
                    impact = (ev.get("impact") or "").lower()
                    impact_icon = {"high": "🔴", "medium": "🟡"}.get(impact, "⚫")

                    with st.expander(f"{flag} {impact_icon} {short_name}"):
                        render_event_detail(ev, today)

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Footer ───────────────────────────────────────────────
    st.markdown("""
    <div style="margin-top:32px; padding-top:16px; border-top:1px solid #111124;
                font-family:'IBM Plex Mono',monospace; font-size:10px; color:#2a2a3a;
                display:flex; justify-content:space-between;">
        <span>DATA · FINNHUB FREE TIER</span>
        <span>CACHE · 15 MIN</span>
    </div>
    """, unsafe_allow_html=True)


main()
