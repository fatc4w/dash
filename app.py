import streamlit as st
import requests
import json
from datetime import datetime, timedelta, date

st.set_page_config(
    page_title="Macro Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
IMPACT_COLOR = {"high": "#ef4444", "medium": "#f59e0b", "low": "#4a4a6a", None: "#4a4a6a"}
IMPACT_LABEL = {"high": "HIGH", "medium": "MED", "low": "LOW", None: "—"}
IMPACT_BG    = {"high": "#2a0f0f", "medium": "#2a1f0a", "low": "#13131f", None: "#13131f"}

def get_4week_range():
    today  = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=27)

def build_week_grid(start_monday):
    return [[start_monday + timedelta(days=w*7+d) for d in range(7)] for w in range(4)]

@st.cache_data(ttl=900)
def fetch_economic_events(from_date, to_date, api_key):
    url = "https://finnhub.io/api/v1/calendar/economic"
    try:
        resp = requests.get(url, params={"from": from_date, "to": to_date, "token": api_key}, timeout=10)
        resp.raise_for_status()
        events = resp.json().get("economicCalendar", [])
    except Exception as e:
        st.warning(f"Finnhub error: {e}")
        return []
    return [e for e in events if e.get("country","").upper() in TARGET_COUNTRIES]

def group_events_by_date(events):
    grouped = {}
    for ev in events:
        key = (ev.get("time") or "")[:10]
        if key:
            grouped.setdefault(key, []).append(ev)
    return grouped

def main():
    if "selected_day" not in st.session_state:
        st.session_state.selected_day = None

    try:
        api_key = st.secrets["FINNHUB_API_KEY"]
    except Exception:
        api_key = ""

    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

* { box-sizing: border-box; }
.stApp { background: #07070e; }
[data-testid="stSidebar"] { background: #09090f; border-right: 1px solid #14142a; }
[data-testid="stSidebar"] * { color: #9090b0 !important; }
[data-testid="stSidebar"] .stCheckbox label { font-family: 'IBM Plex Sans', sans-serif !important; font-size: 13px !important; }

/* ── Sidebar titles ── */
.sb-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; font-weight: 600;
    color: #2a2a4a !important;
    text-transform: uppercase; letter-spacing: .18em;
    margin: 20px 0 8px;
}

/* ── Page header ── */
.pg-header {
    display: flex; align-items: baseline; gap: 14px;
    margin-bottom: 6px; padding-bottom: 16px;
    border-bottom: 1px solid #12122a;
}
.pg-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 18px; font-weight: 600;
    color: #d8d8f0; letter-spacing: -.02em;
}
.pg-range {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 12px; color: #444460; font-weight: 300;
}

/* ── Legend ── */
.legend {
    display: flex; gap: 20px; margin-bottom: 18px; align-items: center;
}
.leg { display: flex; align-items: center; gap: 6px;
    font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #555570;
}
.leg-dot { width: 7px; height: 7px; border-radius: 50%; }

/* ── DOW header ── */
.dow-grid {
    display: grid; grid-template-columns: repeat(7, 1fr);
    gap: 3px; margin-bottom: 3px;
}
.dow-cell {
    text-align: center;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; font-weight: 600; color: #252540;
    letter-spacing: .14em; text-transform: uppercase; padding: 4px 0;
}

/* ── Calendar grid ── */
.cal-grid {
    display: grid; grid-template-columns: repeat(7, 1fr);
    gap: 3px;
}

/* ── Day cell ── */
.day-cell {
    background: #0d0d1a;
    border: 1px solid #13132a;
    border-radius: 8px;
    padding: 10px 10px 8px;
    min-height: 160px;
    cursor: pointer;
    transition: border-color .15s, background .15s;
    overflow: hidden;
    position: relative;
}
.day-cell:hover { border-color: #2a2a55; background: #0f0f1e; }
.day-cell.today {
    border-color: #3333cc55;
    background: #0d0d22;
    box-shadow: inset 0 0 0 1px #3333cc22;
}
.day-cell.today .day-num { color: #6666ee; }
.day-cell.past { opacity: .45; }
.day-cell.weekend { background: #0a0a15; }
.day-cell.selected {
    border-color: #5555dd !important;
    background: #10102a !important;
    box-shadow: inset 0 0 0 1px #5555dd44 !important;
}

/* ── Day number ── */
.day-num {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px; font-weight: 600; color: #333358;
    display: block; margin-bottom: 8px;
}
.day-month { font-size: 9px; color: #222235; margin-left: 4px; text-transform: uppercase; letter-spacing: .08em; }

/* ── Event row inside cell ── */
.ev-row {
    display: flex; align-items: center; gap: 5px;
    padding: 3px 5px; margin-bottom: 2px;
    border-radius: 4px; border-left: 2px solid transparent;
    background: #111120;
    overflow: hidden;
}
.ev-flag { font-size: 11px; flex-shrink: 0; line-height: 1; }
.ev-dot  { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }
.ev-name {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 10px; color: #7070a0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    flex: 1; min-width: 0;
}
.ev-row.high   { border-left-color: #ef4444; background: #150d0d; }
.ev-row.high   .ev-name { color: #cc7777; }
.ev-row.medium { border-left-color: #f59e0b; background: #141008; }
.ev-row.medium .ev-name { color: #aa8844; }
.ev-more {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; color: #333355;
    padding: 2px 5px; margin-top: 1px;
}

/* ── Day button overlay (invisible, covers whole cell) ── */
.stButton > button {
    position: absolute !important;
    top: 0 !important; left: 0 !important;
    width: 100% !important; height: 100% !important;
    opacity: 0 !important;
    cursor: pointer !important;
    z-index: 10 !important;
}

/* ── Detail panel ── */
.detail-wrap {
    background: #0d0d1a;
    border: 1px solid #1a1a35;
    border-radius: 10px;
    padding: 20px 24px;
    margin-top: 16px;
}
.detail-date {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px; color: #333355;
    text-transform: uppercase; letter-spacing: .12em;
    margin-bottom: 16px;
}
.ev-detail-row {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 14px; margin-bottom: 6px;
    border-radius: 6px; background: #111120;
    border-left: 3px solid #222240;
    cursor: pointer; transition: background .12s;
}
.ev-detail-row:hover { background: #14142a; }
.ev-detail-row.high   { border-left-color: #ef4444; background: #160d0d; }
.ev-detail-row.medium { border-left-color: #f59e0b; background: #15110a; }
.ev-detail-flag { font-size: 20px; }
.ev-detail-info { flex: 1; }
.ev-detail-name {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 13px; font-weight: 500; color: #c0c0e0;
}
.ev-detail-country {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 11px; color: #444460; margin-top: 1px;
}
.ev-detail-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; font-weight: 600;
    border: 1px solid; border-radius: 3px;
    padding: 2px 6px; letter-spacing: .08em; flex-shrink: 0;
}
.ev-stats {
    display: flex; gap: 24px; margin-top: 8px; margin-left: 30px;
}
.ev-stat-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; color: #333355;
    text-transform: uppercase; letter-spacing: .1em; margin-bottom: 3px;
}
.ev-stat-val {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 14px; color: #9090c0;
}
.ev-stat-val.actual { color: #70c070; }

/* Streamlit metric overrides */
.stMetric label { font-family: 'IBM Plex Mono', monospace !important; font-size: 10px !important; color: #444460 !important; text-transform: uppercase; letter-spacing: .08em; }

/* Hide default streamlit button chrome for day cells */
[data-testid="stColumns"] div[data-testid="column"] > div > div > div > div[data-testid="stButton"] > button {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
    min-height: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
    opacity: 0 !important;
}
</style>
""", unsafe_allow_html=True)

    # ── Sidebar ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown('<div class="sb-title">Countries</div>', unsafe_allow_html=True)
        selected_countries = {}
        for code, info in COUNTRY_CONFIG.items():
            selected_countries[code] = st.checkbox(f"{info['flag']}  {info['name']}", value=True, key=f"c_{code}")
        active_countries = {c for c, v in selected_countries.items() if v}

        st.markdown('<div class="sb-title">Impact</div>', unsafe_allow_html=True)
        show_high   = st.checkbox("🔴  High",   value=True)
        show_medium = st.checkbox("🟡  Medium", value=True)
        show_low    = st.checkbox("⚪  Low",    value=True)
        allowed_impacts = set()
        if show_high:   allowed_impacts.add("high")
        if show_medium: allowed_impacts.add("medium")
        if show_low:    allowed_impacts.update({"low", None, ""})

    # ── Date range + data ────────────────────────────────────
    today = date.today()
    start_monday, end_sunday = get_4week_range()
    week_grid = build_week_grid(start_monday)
    month_labels = sorted({d.strftime("%B %Y") for week in week_grid for d in week})

    events_by_date = {}
    if api_key:
        raw = fetch_economic_events(start_monday.isoformat(), end_sunday.isoformat(), api_key)
        filtered = [
            e for e in raw
            if e.get("country","").upper() in active_countries
            and (e.get("impact") or "").lower() in allowed_impacts
        ]
        events_by_date = group_events_by_date(filtered)
    else:
        st.warning("FINNHUB_API_KEY not found in secrets.", icon="🔑")

    # ── Header ───────────────────────────────────────────────
    st.markdown(f"""
    <div class="pg-header">
        <span class="pg-title">ECONOMIC CALENDAR</span>
        <span class="pg-range">{" · ".join(month_labels)}</span>
    </div>
    <div class="legend">
        <span class="leg"><span class="leg-dot" style="background:#ef4444"></span>High Impact</span>
        <span class="leg"><span class="leg-dot" style="background:#f59e0b"></span>Medium Impact</span>
        <span class="leg"><span class="leg-dot" style="background:#333355"></span>Low / None</span>
    </div>
    """, unsafe_allow_html=True)

    # ── DOW header ───────────────────────────────────────────
    dow_html = '<div class="dow-grid">' + "".join(
        f'<div class="dow-cell">{d}</div>' for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    ) + '</div>'
    st.markdown(dow_html, unsafe_allow_html=True)

    # ── Calendar — one st.columns row per week ───────────────
    # Each cell: HTML for visual display + one invisible button to capture click
    for week in week_grid:
        cols = st.columns(7, gap="small")
        for day_idx, day in enumerate(week):
            day_key    = day.isoformat()
            is_today   = day == today
            is_past    = day < today
            is_weekend = day_idx >= 5
            day_events = events_by_date.get(day_key, [])
            is_selected = st.session_state.selected_day == day_key

            css = "day-cell"
            if is_today:    css += " today"
            elif is_past:   css += " past"
            if is_weekend:  css += " weekend"
            if is_selected: css += " selected"

            month_tag = f'<span class="day-month">{day.strftime("%b")}</span>' if day.day == 1 else ""

            # Build event rows (max 6 visible in cell)
            ev_rows = ""
            for ev in day_events[:6]:
                code   = ev.get("country","").upper()
                flag   = COUNTRY_CONFIG.get(code,{}).get("flag","🌐")
                impact = (ev.get("impact") or "").lower()
                name   = ev.get("event","")[:28]
                dot_c  = IMPACT_COLOR.get(impact, IMPACT_COLOR[None])
                ev_rows += f'<div class="ev-row {impact}"><span class="ev-flag">{flag}</span><span class="ev-dot" style="background:{dot_c}"></span><span class="ev-name">{name}</span></div>'
            overflow = len(day_events) - 6
            if overflow > 0:
                ev_rows += f'<div class="ev-more">+{overflow} more</div>'

            cell_html = f"""
            <div class="{css}">
                <span class="day-num">{day.day}{month_tag}</span>
                {ev_rows}
            </div>
            """

            with cols[day_idx]:
                st.markdown(cell_html, unsafe_allow_html=True)
                # Invisible button — clicking triggers day selection
                if day_events:
                    if st.button(" ", key=f"d_{day_key}", use_container_width=True):
                        if st.session_state.selected_day == day_key:
                            st.session_state.selected_day = None
                        else:
                            st.session_state.selected_day = day_key

        st.markdown("<div style='height:3px'></div>", unsafe_allow_html=True)

    # ── Detail panel ─────────────────────────────────────────
    if st.session_state.selected_day:
        day_key    = st.session_state.selected_day
        day_events = events_by_date.get(day_key, [])
        sel_date   = datetime.strptime(day_key, "%Y-%m-%d").date()
        is_past    = sel_date < today

        close_col, _ = st.columns([1, 11])
        with close_col:
            if st.button("✕ Close", key="close_panel"):
                st.session_state.selected_day = None
                st.rerun()

        st.markdown(f'<div class="detail-date">{sel_date.strftime("%A, %d %B %Y")} · {len(day_events)} event{"s" if len(day_events)!=1 else ""}</div>', unsafe_allow_html=True)

        unit_map = {}
        def fmt(v, unit=""):
            if v is None or v == "": return "—"
            try:    return f"{float(v):,.3f}{' '+unit if unit else ''}"
            except: return str(v)

        for ev in day_events:
            code    = ev.get("country","").upper()
            flag    = COUNTRY_CONFIG.get(code,{}).get("flag","🌐")
            cname   = COUNTRY_CONFIG.get(code,{}).get("name", code)
            ename   = ev.get("event","Unknown")
            impact  = (ev.get("impact") or "").lower() or None
            icolor  = IMPACT_COLOR.get(impact, IMPACT_COLOR[None])
            ilabel  = IMPACT_LABEL.get(impact,"—")
            unit    = ev.get("unit","")
            prev_v  = fmt(ev.get("prev"), unit)
            est_v   = fmt(ev.get("estimate"), unit)
            act_v   = fmt(ev.get("actual"), unit)
            raw_time= ev.get("time","")
            time_str= raw_time[11:16] + " UTC" if len(raw_time) > 10 else ""

            actual_display = act_v if is_past else "—"
            actual_class   = "actual" if is_past and act_v != "—" else ""

            st.markdown(f"""
            <div class="ev-detail-row {impact or ''}">
                <span class="ev-detail-flag">{flag}</span>
                <div class="ev-detail-info">
                    <div class="ev-detail-name">{ename}</div>
                    <div class="ev-detail-country">{cname}{" · " + time_str if time_str else ""}</div>
                    <div class="ev-stats">
                        <div><div class="ev-stat-label">Prev</div><div class="ev-stat-val">{prev_v}</div></div>
                        <div><div class="ev-stat-label">Forecast</div><div class="ev-stat-val">{est_v}</div></div>
                        <div><div class="ev-stat-label">Actual</div><div class="ev-stat-val {actual_class}">{actual_display}</div></div>
                    </div>
                </div>
                <div class="ev-detail-badge" style="color:{icolor};border-color:{icolor};">{ilabel}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:40px;padding-top:14px;border-top:1px solid #0f0f20;
                font-family:'IBM Plex Mono',monospace;font-size:9px;color:#1e1e38;
                display:flex;justify-content:space-between;">
        <span>DATA · FINNHUB FREE TIER · ASIAN ECONOMIES</span>
        <span>CACHE · 15 MIN</span>
    </div>
    """, unsafe_allow_html=True)

main()
