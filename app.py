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
IMPACT_COLOR = {"high": "#f87171", "medium": "#fbbf24", "low": "#94a3b8", None: "#94a3b8"}
IMPACT_BG    = {"high": "#3f1515", "medium": "#3d2a08", "low": "#1e2130", None: "#1e2130"}
IMPACT_LABEL = {"high": "HIGH", "medium": "MED", "low": "LOW", None: "—"}

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

def fmt_val(v, unit=""):
    if v is None or v == "": return "N/A"
    try:    return f"{float(v):,.3f}{' '+unit if unit else ''}"
    except: return str(v)

def main():
    if "selected_event" not in st.session_state:
        st.session_state.selected_event = None

    try:
        api_key = st.secrets["FINNHUB_API_KEY"]
    except Exception:
        api_key = ""

    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap');

* { box-sizing: border-box; }

.stApp { background: #111827; }

[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] * { color: #94a3b8 !important; }
[data-testid="stSidebar"] .stCheckbox label {
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    color: #cbd5e1 !important;
}
[data-testid="stSidebar"] [data-testid="stCheckbox"] label span {
    color: #cbd5e1 !important;
}

.sb-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px; font-weight: 600;
    color: #334155 !important;
    text-transform: uppercase; letter-spacing: .2em;
    margin: 22px 0 10px; display: block;
}

/* ── Page header ── */
.pg-header {
    display: flex; align-items: baseline; gap: 16px;
    margin-bottom: 8px; padding-bottom: 16px;
    border-bottom: 1px solid #1e293b;
}
.pg-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 20px; font-weight: 600; color: #f1f5f9;
    letter-spacing: -.02em;
}
.pg-range {
    font-family: 'Inter', sans-serif;
    font-size: 13px; color: #475569; font-weight: 400;
}

/* ── Legend ── */
.legend {
    display: flex; gap: 22px; margin-bottom: 16px; align-items: center;
}
.leg {
    display: flex; align-items: center; gap: 7px;
    font-family: 'Inter', sans-serif; font-size: 12px; color: #64748b;
}
.leg-dot { width: 8px; height: 8px; border-radius: 50%; }

/* ── DOW header ── */
.dow-grid {
    display: grid; grid-template-columns: repeat(7, 1fr);
    gap: 4px; margin-bottom: 4px;
}
.dow-cell {
    text-align: center;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; font-weight: 600; color: #334155;
    letter-spacing: .14em; text-transform: uppercase; padding: 6px 0;
}

/* ── Calendar grid ── */
.cal-week { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 4px; }

/* ── Day cell ── */
.day-cell {
    background: #1e293b;
    border: 1px solid #293548;
    border-radius: 10px;
    padding: 12px 12px 10px;
    height: 220px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: #334155 transparent;
    transition: border-color .15s, background .15s;
}
.day-cell::-webkit-scrollbar { width: 3px; }
.day-cell::-webkit-scrollbar-thumb { background: #334155; border-radius: 2px; }
.day-cell:hover { border-color: #3b5bdb; background: #1e2d45; }
.day-cell.today {
    border-color: #3b5bdb;
    background: #1a2744;
    box-shadow: inset 0 0 0 1px #3b5bdb33;
}
.day-cell.past { opacity: .5; }
.day-cell.weekend { background: #192132; border-color: #22304a; }
.day-cell.selected {
    border-color: #6366f1 !important;
    background: #1e2050 !important;
    box-shadow: 0 0 0 2px #6366f133 !important;
}

/* ── Day number ── */
.day-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px; font-weight: 600; color: #475569;
    display: block; margin-bottom: 10px; line-height: 1;
}
.day-cell.today .day-num { color: #818cf8; }
.day-month-tag {
    font-size: 9px; color: #334155; margin-left: 5px;
    text-transform: uppercase; letter-spacing: .08em;
}

/* ── Event row inside cell ── */
.ev-row {
    display: flex; align-items: center; gap: 6px;
    padding: 4px 7px; margin-bottom: 3px;
    border-radius: 5px; border-left: 2px solid #334155;
    background: #263348;
    cursor: pointer;
    transition: background .1s;
}
.ev-row:hover { background: #2d3f5c; }
.ev-row.high   { border-left-color: #f87171; background: #2d1a1a; }
.ev-row.high:hover { background: #3a2020; }
.ev-row.medium { border-left-color: #fbbf24; background: #2d2210; }
.ev-row.medium:hover { background: #3a2c14; }

.ev-flag { font-size: 12px; flex-shrink: 0; line-height: 1; }
.ev-name {
    font-family: 'Inter', sans-serif;
    font-size: 11px; font-weight: 400; color: #94a3b8;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    flex: 1; min-width: 0;
}
.ev-row.high   .ev-name { color: #fca5a5; }
.ev-row.medium .ev-name { color: #fcd34d; }

/* ── Streamlit button invisible overlay ── */
div[data-testid="stButton"] button {
    all: unset !important;
    display: block !important;
    width: 100% !important;
    cursor: pointer !important;
}

/* ── Detail panel ── */
.detail-panel {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 24px 28px;
    margin-top: 20px;
}
.detail-date-header {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px; color: #475569;
    text-transform: uppercase; letter-spacing: .12em;
    margin-bottom: 20px;
}
.detail-event {
    display: flex; align-items: flex-start; gap: 14px;
    padding: 14px 16px; margin-bottom: 8px;
    border-radius: 8px; background: #263348;
    border-left: 3px solid #334155;
}
.detail-event.high   { border-left-color: #f87171; background: #2a1a1a; }
.detail-event.medium { border-left-color: #fbbf24; background: #2a2010; }
.detail-flag { font-size: 22px; flex-shrink: 0; margin-top: 2px; }
.detail-info { flex: 1; }
.detail-name {
    font-family: 'Inter', sans-serif;
    font-size: 14px; font-weight: 600; color: #e2e8f0;
    margin-bottom: 3px;
}
.detail-meta {
    font-family: 'Inter', sans-serif;
    font-size: 11px; color: #64748b; margin-bottom: 12px;
}
.detail-stats { display: flex; gap: 28px; }
.stat-block {}
.stat-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px; color: #475569;
    text-transform: uppercase; letter-spacing: .12em; margin-bottom: 4px;
}
.stat-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 16px; color: #94a3b8;
}
.stat-val.has-data { color: #e2e8f0; }
.stat-val.actual   { color: #4ade80; }
.stat-val.na       { color: #334155; }
.detail-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px; font-weight: 600;
    border: 1px solid; border-radius: 4px;
    padding: 3px 8px; letter-spacing: .1em;
    flex-shrink: 0; align-self: flex-start;
    margin-top: 2px;
}

/* ── Scrollbar on detail panel ── */
.detail-panel { max-height: 70vh; overflow-y: auto; scrollbar-width: thin; scrollbar-color: #334155 transparent; }
</style>
""", unsafe_allow_html=True)

    # ── Sidebar ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown('<span class="sb-title">Countries</span>', unsafe_allow_html=True)
        selected_countries = {}
        for code, info in COUNTRY_CONFIG.items():
            selected_countries[code] = st.checkbox(f"{info['flag']}  {info['name']}", value=True, key=f"c_{code}")
        active_countries = {c for c, v in selected_countries.items() if v}

        st.markdown('<span class="sb-title">Impact</span>', unsafe_allow_html=True)
        show_high   = st.checkbox("🔴  High",   value=True)
        show_medium = st.checkbox("🟡  Medium", value=True)
        show_low    = st.checkbox("⚪  Low",    value=True)
        allowed_impacts = set()
        if show_high:   allowed_impacts.add("high")
        if show_medium: allowed_impacts.add("medium")
        if show_low:    allowed_impacts.update({"low", None, ""})

    # ── Data ─────────────────────────────────────────────────
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
        <span class="leg"><span class="leg-dot" style="background:#f87171"></span>High Impact</span>
        <span class="leg"><span class="leg-dot" style="background:#fbbf24"></span>Medium Impact</span>
        <span class="leg"><span class="leg-dot" style="background:#475569"></span>Low / None</span>
    </div>
    """, unsafe_allow_html=True)

    # ── DOW header ───────────────────────────────────────────
    st.markdown(
        '<div class="dow-grid">' +
        "".join(f'<div class="dow-cell">{d}</div>' for d in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]) +
        '</div>',
        unsafe_allow_html=True
    )

    # ── Calendar grid ────────────────────────────────────────
    # Strategy: render the visual HTML cell, then a HIDDEN button per EVENT
    # (not per day) using display:none trick — we collect button presses via session_state

    for week in week_grid:
        cols = st.columns(7, gap="small")
        for day_idx, day in enumerate(week):
            day_key    = day.isoformat()
            is_today   = day == today
            is_past    = day < today
            is_weekend = day_idx >= 5
            day_events = events_by_date.get(day_key, [])

            sel_ev = st.session_state.selected_event
            is_selected = sel_ev is not None and (sel_ev.get("time","") or "")[:10] == day_key

            css = "day-cell"
            if is_today:    css += " today"
            elif is_past:   css += " past"
            if is_weekend:  css += " weekend"
            if is_selected: css += " selected"

            month_tag = f'<span class="day-month-tag">{day.strftime("%b")}</span>' if day.day == 1 else ""

            # ALL events visible — cell is scrollable
            ev_rows = ""
            for ev in day_events:
                code   = ev.get("country","").upper()
                flag   = COUNTRY_CONFIG.get(code,{}).get("flag","🌐")
                impact = (ev.get("impact") or "").lower()
                name   = ev.get("event","")
                ev_rows += f'<div class="ev-row {impact}"><span class="ev-flag">{flag}</span><span class="ev-name">{name}</span></div>'

            cell_html = f'<div class="{css}"><span class="day-num">{day.day}{month_tag}</span>{ev_rows}</div>'

            with cols[day_idx]:
                st.markdown(cell_html, unsafe_allow_html=True)
                # One small visible button per event for interactivity
                for i, ev in enumerate(day_events):
                    code   = ev.get("country","").upper()
                    flag   = COUNTRY_CONFIG.get(code,{}).get("flag","🌐")
                    impact = (ev.get("impact") or "").lower()
                    icon   = {"high":"🔴","medium":"🟡"}.get(impact,"⚪")
                    name   = ev.get("event","")[:30]
                    key    = f"btn_{day_key}_{code}_{i}"
                    if st.button(f"{flag} {icon} {name}", key=key, use_container_width=True):
                        if st.session_state.selected_event == ev:
                            st.session_state.selected_event = None
                        else:
                            st.session_state.selected_event = ev

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Event detail panel ───────────────────────────────────
    if st.session_state.selected_event:
        ev      = st.session_state.selected_event
        code    = ev.get("country","").upper()
        flag    = COUNTRY_CONFIG.get(code,{}).get("flag","🌐")
        cname   = COUNTRY_CONFIG.get(code,{}).get("name", code)
        ename   = ev.get("event","Unknown")
        impact  = (ev.get("impact") or "").lower() or None
        icolor  = IMPACT_COLOR.get(impact, IMPACT_COLOR[None])
        ilabel  = IMPACT_LABEL.get(impact,"—")
        unit    = ev.get("unit","")
        raw_t   = ev.get("time","")
        edate   = datetime.strptime(raw_t[:10],"%Y-%m-%d").date() if raw_t else None
        is_past = edate is not None and edate < today
        time_str= raw_t[11:16] + " UTC" if len(raw_t) > 10 else ""

        prev_v  = fmt_val(ev.get("prev"), unit)
        est_v   = fmt_val(ev.get("estimate"), unit)
        act_raw = ev.get("actual")
        act_v   = fmt_val(act_raw, unit) if is_past else "N/A"
        act_cls = "actual" if is_past and act_raw is not None and act_raw != "" else ("na" if not is_past else "")

        def val_cls(v):
            return "has-data" if v not in ("N/A","") else "na"

        st.markdown("---")
        hcol, xcol = st.columns([12, 1])
        with xcol:
            if st.button("✕", key="close_ev"):
                st.session_state.selected_event = None
                st.rerun()

        st.markdown(f"""
        <div class="detail-panel">
            <div class="detail-date-header">
                {edate.strftime("%A, %d %B %Y") if edate else ""}{" · " + time_str if time_str else ""}
            </div>
            <div class="detail-event {impact or ''}">
                <div class="detail-flag">{flag}</div>
                <div class="detail-info">
                    <div class="detail-name">{ename}</div>
                    <div class="detail-meta">{cname}</div>
                    <div class="detail-stats">
                        <div class="stat-block">
                            <div class="stat-label">Previous</div>
                            <div class="stat-val {val_cls(prev_v)}">{prev_v}</div>
                        </div>
                        <div class="stat-block">
                            <div class="stat-label">Forecast</div>
                            <div class="stat-val {val_cls(est_v)}">{est_v}</div>
                        </div>
                        <div class="stat-block">
                            <div class="stat-label">Actual</div>
                            <div class="stat-val {act_cls}">{act_v}</div>
                        </div>
                    </div>
                </div>
                <div class="detail-badge" style="color:{icolor};border-color:{icolor};">{ilabel}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:40px;padding-top:14px;border-top:1px solid #1e293b;
                font-family:'JetBrains Mono',monospace;font-size:9px;color:#1e293b;
                display:flex;justify-content:space-between;">
        <span>DATA · FINNHUB FREE TIER · ASIAN ECONOMIES</span>
        <span>CACHE · 15 MIN</span>
    </div>
    """, unsafe_allow_html=True)

main()
