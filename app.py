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
IMPACT_COLOR  = {"high": "#ef4444", "medium": "#f59e0b", "low": "#6b7280", None: "#6b7280"}
IMPACT_LABEL  = {"high": "HIGH", "medium": "MED", "low": "LOW", None: "—"}

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

def render_event_pill(ev, today):
    code   = ev.get("country","").upper()
    flag   = COUNTRY_CONFIG.get(code,{}).get("flag","🌐")
    name   = ev.get("event","")
    impact = (ev.get("impact") or "").lower() or None
    color  = IMPACT_COLOR.get(impact, IMPACT_COLOR[None])
    short  = name if len(name)<=32 else name[:30]+"…"
    return f'<div class="event-pill impact-{impact or "none"}" style="border-left:2px solid {color};"><span class="event-flag">{flag}</span><span class="event-name">{short}</span></div>'

def render_event_detail(ev, today):
    code        = ev.get("country","").upper()
    flag        = COUNTRY_CONFIG.get(code,{}).get("flag","🌐")
    cname       = COUNTRY_CONFIG.get(code,{}).get("name", code)
    ename       = ev.get("event","Unknown")
    impact      = (ev.get("impact") or "").lower() or None
    icolor      = IMPACT_COLOR.get(impact, IMPACT_COLOR[None])
    ilabel      = IMPACT_LABEL.get(impact,"—")
    raw_time    = ev.get("time","")
    edate       = datetime.strptime(raw_time[:10],"%Y-%m-%d").date() if raw_time else None
    is_past     = edate is not None and edate < today
    unit        = ev.get("unit","")
    def fmt(v):
        if v is None or v=="": return "—"
        try: return f"{float(v):,.3f}{' '+unit if unit else ''}"
        except: return str(v)
    st.markdown(f'<div class="detail-card"><div class="detail-header"><span class="detail-flag">{flag}</span><div class="detail-title-block"><div class="detail-event-name">{ename}</div><div class="detail-country">{cname}</div></div><div class="detail-impact" style="color:{icolor};border-color:{icolor};">{ilabel}</div></div></div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    c1.metric("Previous", fmt(ev.get("prev")))
    c2.metric("Forecast", fmt(ev.get("estimate")))
    c3.metric("Actual", fmt(ev.get("actual")) if is_past else "Pending")
    if raw_time and len(raw_time)>10:
        st.caption(f"🕐 {raw_time[11:16]} UTC")

def main():
    if "selected_event" not in st.session_state:
        st.session_state.selected_event = None

    try:
        api_key = st.secrets["FINNHUB_API_KEY"]
    except Exception:
        api_key = ""

    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
.stApp{background:#06060b;}
[data-testid="stSidebar"]{background:#0a0a0f;border-right:1px solid #1e1e2e;}
[data-testid="stSidebar"] *{color:#c0c0d0!important;}
.cal-header{display:flex;align-items:baseline;gap:12px;margin-bottom:28px;}
.cal-title{font-family:'IBM Plex Mono',monospace;font-size:22px;font-weight:600;color:#e8e8f0;letter-spacing:-0.03em;}
.cal-subtitle{font-family:'IBM Plex Sans',sans-serif;font-size:13px;color:#555570;font-weight:300;}
.legend-row{display:flex;gap:18px;margin-bottom:20px;align-items:center;}
.legend-item{display:flex;align-items:center;gap:5px;font-size:11px;font-family:'IBM Plex Mono',monospace;color:#666680;}
.legend-dot{width:8px;height:8px;border-radius:50%;display:inline-block;}
.dow-row{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin-bottom:4px;}
.dow-cell{text-align:center;font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;color:#3a3a5c;letter-spacing:.12em;text-transform:uppercase;padding:6px 0;}
.day-cell{background:#0e0e1a;border:1px solid #16162a;border-radius:6px;padding:8px 8px 6px;min-height:110px;transition:border-color .15s ease;overflow:hidden;}
.day-cell:hover{border-color:#2a2a4a;}
.day-cell.today{background:#0f0f20;border-color:#3b3bff44;box-shadow:0 0 0 1px #3b3bff22 inset;}
.day-cell.today .day-num{color:#7b7bff;background:#1a1a3a;border-radius:4px;padding:1px 5px;}
.day-cell.past{opacity:.55;}
.day-cell.weekend{background:#0c0c16;}
.day-num{font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:600;color:#404060;margin-bottom:5px;display:inline-block;}
.day-month-label{font-family:'IBM Plex Mono',monospace;font-size:9px;color:#2a2a3a;margin-left:3px;text-transform:uppercase;letter-spacing:.1em;}
.event-pill{display:flex;align-items:center;gap:4px;background:#13131f;border-radius:3px;padding:2px 5px;margin-bottom:2px;overflow:hidden;}
.event-flag{font-size:10px;flex-shrink:0;}
.event-name{font-family:'IBM Plex Sans',sans-serif;font-size:9.5px;color:#8888aa;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;}
.event-pill.impact-high .event-name{color:#cc8888;}
.event-pill.impact-medium .event-name{color:#b89060;}
.detail-card{background:#0e0e1a;border:1px solid #1e1e35;border-radius:8px;padding:16px 18px;margin-bottom:12px;}
.detail-header{display:flex;align-items:flex-start;gap:12px;}
.detail-flag{font-size:28px;flex-shrink:0;}
.detail-title-block{flex:1;}
.detail-event-name{font-family:'IBM Plex Sans',sans-serif;font-size:15px;font-weight:600;color:#d0d0e8;margin-bottom:2px;}
.detail-country{font-family:'IBM Plex Sans',sans-serif;font-size:12px;color:#555570;}
.detail-impact{font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:600;border:1px solid;border-radius:3px;padding:2px 6px;flex-shrink:0;letter-spacing:.08em;}
[data-testid="stColumns"] .stButton>button{background:#13131f!important;border:none!important;border-left:2px solid #333355!important;border-radius:3px!important;padding:2px 6px!important;margin-bottom:2px!important;font-family:'IBM Plex Sans',sans-serif!important;font-size:9.5px!important;color:#8888aa!important;text-align:left!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;max-width:100%!important;min-height:0!important;line-height:1.4!important;}
[data-testid="stColumns"] .stButton>button:hover{background:#1a1a2e!important;color:#aaaacc!important;border-left-color:#5555aa!important;}
.stMetric label{font-family:'IBM Plex Mono',monospace!important;font-size:10px!important;color:#555570!important;text-transform:uppercase;letter-spacing:.08em;}
.sidebar-section-title{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#333355;text-transform:uppercase;letter-spacing:.15em;margin:18px 0 8px;}
</style>
""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<div class="sidebar-section-title">Countries</div>', unsafe_allow_html=True)
        selected_countries = {}
        for code, info in COUNTRY_CONFIG.items():
            selected_countries[code] = st.checkbox(f"{info['flag']} {info['name']}", value=True, key=f"c_{code}")
        active_countries = {c for c,v in selected_countries.items() if v}

        st.markdown('<div class="sidebar-section-title">Impact Filter</div>', unsafe_allow_html=True)
        show_high   = st.checkbox("🔴 High",   value=True)
        show_medium = st.checkbox("🟡 Medium", value=True)
        show_low    = st.checkbox("⚫ Low",    value=True)
        allowed_impacts = set()
        if show_high:   allowed_impacts.add("high")
        if show_medium: allowed_impacts.add("medium")
        if show_low:    allowed_impacts.update({"low", None, ""})

    today = date.today()
    start_monday, end_sunday = get_4week_range()
    week_grid = build_week_grid(start_monday)
    month_labels = sorted({d.strftime("%B %Y") for week in week_grid for d in week})

    st.markdown(f'<div class="cal-header"><span class="cal-title">ECONOMIC CALENDAR</span><span class="cal-subtitle">{" · ".join(month_labels)}</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="legend-row"><span class="legend-item"><span class="legend-dot" style="background:#ef4444"></span> High Impact</span><span class="legend-item"><span class="legend-dot" style="background:#f59e0b"></span> Medium Impact</span><span class="legend-item"><span class="legend-dot" style="background:#444460"></span> Low Impact</span></div>', unsafe_allow_html=True)

    events_by_date = {}
    if api_key:
        raw = fetch_economic_events(start_monday.isoformat(), end_sunday.isoformat(), api_key)
        filtered = [e for e in raw if e.get("country","").upper() in active_countries and (e.get("impact") or "").lower() in allowed_impacts]
        events_by_date = group_events_by_date(filtered)
    else:
        st.warning("FINNHUB_API_KEY not found in secrets.", icon="🔑")

    st.markdown('<div class="dow-row"><div class="dow-cell">Mon</div><div class="dow-cell">Tue</div><div class="dow-cell">Wed</div><div class="dow-cell">Thu</div><div class="dow-cell">Fri</div><div class="dow-cell">Sat</div><div class="dow-cell">Sun</div></div>', unsafe_allow_html=True)

    for week in week_grid:
        cols = st.columns(7, gap="small")
        for day_idx, day in enumerate(week):
            day_key    = day.isoformat()
            is_today   = day == today
            is_past    = day < today
            is_weekend = day_idx >= 5
            day_events = events_by_date.get(day_key, [])
            classes    = ["day-cell"] + (["today"] if is_today else ["past"] if is_past else []) + (["weekend"] if is_weekend else [])
            month_suffix = f'<span class="day-month-label">{day.strftime("%b")}</span>' if day.day == 1 else ""
            pills = "".join(render_event_pill(ev, today) for ev in day_events[:6])
            if len(day_events) > 6:
                pills += f'<div style="font-size:9px;color:#444460;padding:1px 5px;">+{len(day_events)-6} more</div>'
            with cols[day_idx]:
                st.markdown(f'<div class="{" ".join(classes)}"><span class="day-num">{day.day}</span>{month_suffix}{pills}</div>', unsafe_allow_html=True)
                for i, ev in enumerate(day_events):
                    code   = ev.get("country","").upper()
                    flag   = COUNTRY_CONFIG.get(code,{}).get("flag","🌐")
                    impact = (ev.get("impact") or "").lower()
                    icon   = {"high":"🔴","medium":"🟡"}.get(impact,"⚫")
                    label  = f"{flag} {icon} {ev.get('event','')[:22]}"
                    key    = f"ev_{day_key}_{ev.get('event','')[:20]}_{code}_{i}"
                    if st.button(label, key=key, use_container_width=True):
                        st.session_state.selected_event = None if st.session_state.selected_event == ev else ev
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    if st.session_state.selected_event:
        ev = st.session_state.selected_event
        st.markdown("---")
        col_d, col_x = st.columns([11,1])
        with col_x:
            if st.button("✕", key="close_detail"):
                st.session_state.selected_event = None
                st.rerun()
        with col_d:
            render_event_detail(ev, today)

    st.markdown('<div style="margin-top:32px;padding-top:16px;border-top:1px solid #111124;font-family:\'IBM Plex Mono\',monospace;font-size:10px;color:#2a2a3a;display:flex;justify-content:space-between;"><span>DATA · FINNHUB FREE TIER</span><span>CACHE · 15 MIN</span></div>', unsafe_allow_html=True)

main()
