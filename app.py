import streamlit as st
import streamlit.components.v1 as components
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
    # ── Global styles (sidebar only) ─────────────────────────
    st.markdown("""
    <style>
    .stApp { background: #ffffff; }
    [data-testid="stSidebar"] { background: #f8f9fa !important; border-right: 1px solid #e9ecef; }
    [data-testid="stSidebar"] * { color: #495057 !important; }
    [data-testid="stSidebar"] .stCheckbox label { font-family: sans-serif !important; font-size: 13px !important; }
    .sb-title { font-family: monospace; font-size: 9px; font-weight: 700; color: #adb5bd !important;
        text-transform: uppercase; letter-spacing: .18em; margin: 20px 0 8px; display: block; }
    div[data-testid="stMainBlockContainer"] { padding-top: 1rem; }
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
    try:
        api_key = st.secrets["FINNHUB_API_KEY"]
    except Exception:
        api_key = ""
        st.warning("FINNHUB_API_KEY not found in secrets.", icon="🔑")

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

    # ── Serialise events to JSON for JS ──────────────────────
    all_days = {}
    for week in week_grid:
        for day in week:
            dk = day.isoformat()
            evs = events_by_date.get(dk, [])
            all_days[dk] = [
                {
                    "event":    e.get("event",""),
                    "country":  e.get("country","").upper(),
                    "flag":     COUNTRY_CONFIG.get(e.get("country","").upper(),{}).get("flag","🌐"),
                    "cname":    COUNTRY_CONFIG.get(e.get("country","").upper(),{}).get("name",""),
                    "impact":   (e.get("impact") or "").lower(),
                    "prev":     fmt_val(e.get("prev"), e.get("unit","")),
                    "estimate": fmt_val(e.get("estimate"), e.get("unit","")),
                    "actual":   fmt_val(e.get("actual"), e.get("unit","")),
                    "time":     e.get("time",""),
                    "unit":     e.get("unit",""),
                    "is_past":  (e.get("time","") or "")[:10] < today.isoformat(),
                }
                for e in evs
            ]

    today_str = today.isoformat()
    days_flat = []
    for week in week_grid:
        for day_idx, day in enumerate(week):
            dk = day.isoformat()
            days_flat.append({
                "date":      dk,
                "day":       day.day,
                "month_abbr": day.strftime("%b") if day.day == 1 else "",
                "is_today":  dk == today_str,
                "is_past":   dk < today_str,
                "is_weekend": day_idx >= 5,
                "week_idx":  week_grid.index(week),
            })

    range_label = " · ".join(month_labels)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', sans-serif; background: #fff; color: #212529; padding: 0 4px; }}

  /* Header */
  .pg-header {{ display:flex; align-items:baseline; gap:14px; margin-bottom:6px; padding-bottom:14px; border-bottom:2px solid #f1f3f5; }}
  .pg-title {{ font-family:'JetBrains Mono',monospace; font-size:18px; font-weight:700; color:#212529; letter-spacing:-.02em; }}
  .pg-range {{ font-size:12px; color:#adb5bd; }}

  /* Legend */
  .legend {{ display:flex; gap:20px; margin-bottom:14px; align-items:center; }}
  .leg {{ display:flex; align-items:center; gap:6px; font-size:11px; color:#868e96; }}
  .leg-dot {{ width:8px; height:8px; border-radius:50%; }}

  /* DOW */
  .dow-grid {{ display:grid; grid-template-columns:repeat(7,1fr); gap:4px; margin-bottom:4px; }}
  .dow-cell {{ text-align:center; font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700;
               color:#adb5bd; letter-spacing:.14em; text-transform:uppercase; padding:5px 0; }}

  /* Calendar grid */
  .cal-grid {{ display:grid; grid-template-columns:repeat(7,1fr); gap:4px; margin-bottom:4px; }}

  /* Day cell */
  .day-cell {{
    background: #fff;
    border: 1.5px solid #e9ecef;
    border-radius: 10px;
    padding: 10px 10px 8px;
    height: 200px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: #dee2e6 transparent;
    cursor: default;
    transition: border-color .15s;
  }}
  .day-cell::-webkit-scrollbar {{ width: 3px; }}
  .day-cell::-webkit-scrollbar-thumb {{ background:#dee2e6; border-radius:2px; }}
  .day-cell:hover {{ border-color: #4263eb; }}
  .day-cell.today {{ border-color:#4263eb; background:#f0f4ff; }}
  .day-cell.past {{ opacity:.45; }}
  .day-cell.weekend {{ background:#f8f9fa; }}

  /* Day number */
  .day-num {{ font-family:'JetBrains Mono',monospace; font-size:13px; font-weight:700;
              color:#ced4da; display:block; margin-bottom:8px; line-height:1; }}
  .day-cell.today .day-num {{ color:#4263eb; }}
  .month-tag {{ font-size:9px; color:#dee2e6; margin-left:4px; text-transform:uppercase; letter-spacing:.07em; }}

  /* Event row */
  .ev-row {{
    display: flex; align-items: center; gap: 6px;
    padding: 4px 7px; margin-bottom: 3px;
    border-radius: 5px; border-left: 2.5px solid #dee2e6;
    background: #f8f9fa;
    cursor: pointer;
    transition: background .1s, border-color .1s;
    user-select: none;
  }}
  .ev-row:hover {{ background: #e9ecef; }}
  .ev-row.high   {{ border-left-color:#f03e3e; background:#fff5f5; }}
  .ev-row.high:hover {{ background:#ffe3e3; }}
  .ev-row.medium {{ border-left-color:#f59f00; background:#fffbeb; }}
  .ev-row.medium:hover {{ background:#fff3bf; }}
  .ev-row.selected {{ outline: 2px solid #4263eb; background:#edf2ff !important; }}

  .ev-flag {{ font-size:12px; flex-shrink:0; line-height:1; }}
  .ev-name {{ font-size:11px; font-weight:400; color:#495057;
              white-space:nowrap; overflow:hidden; text-overflow:ellipsis; flex:1; min-width:0; }}
  .ev-row.high   .ev-name {{ color:#c92a2a; font-weight:500; }}
  .ev-row.medium .ev-name {{ color:#e67700; font-weight:500; }}

  /* Detail panel */
  .detail-panel {{
    background: #fff;
    border: 1.5px solid #e9ecef;
    border-radius: 12px;
    padding: 24px 28px;
    margin-top: 20px;
    max-height: 500px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: #dee2e6 transparent;
  }}
  .detail-panel::-webkit-scrollbar {{ width:3px; }}
  .detail-panel::-webkit-scrollbar-thumb {{ background:#dee2e6; border-radius:2px; }}

  .detail-header {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:18px; }}
  .detail-date {{ font-family:'JetBrains Mono',monospace; font-size:11px; color:#adb5bd;
                  text-transform:uppercase; letter-spacing:.12em; }}
  .close-btn {{ background:none; border:1.5px solid #dee2e6; border-radius:6px; padding:4px 10px;
                font-size:12px; color:#868e96; cursor:pointer; font-family:inherit; }}
  .close-btn:hover {{ background:#f8f9fa; color:#212529; }}

  .ev-card {{
    display:flex; align-items:flex-start; gap:14px;
    padding:16px 18px; margin-bottom:8px;
    border-radius:8px; background:#f8f9fa;
    border-left:3px solid #dee2e6;
    cursor:pointer; transition:background .1s;
  }}
  .ev-card:hover {{ background:#f1f3f5; }}
  .ev-card.high   {{ border-left-color:#f03e3e; background:#fff5f5; }}
  .ev-card.high:hover {{ background:#ffe3e3; }}
  .ev-card.medium {{ border-left-color:#f59f00; background:#fffbeb; }}
  .ev-card.medium:hover {{ background:#fff3bf; }}
  .ev-card.selected {{ outline:2px solid #4263eb; }}

  .card-flag {{ font-size:24px; flex-shrink:0; }}
  .card-info {{ flex:1; }}
  .card-name {{ font-size:14px; font-weight:600; color:#212529; margin-bottom:3px; }}
  .card-meta {{ font-size:11px; color:#868e96; margin-bottom:12px; }}

  .stats {{ display:flex; gap:32px; }}
  .stat-label {{ font-family:'JetBrains Mono',monospace; font-size:9px; color:#adb5bd;
                 text-transform:uppercase; letter-spacing:.12em; margin-bottom:4px; }}
  .stat-val {{ font-family:'JetBrains Mono',monospace; font-size:16px; font-weight:600; color:#495057; }}
  .stat-val.na {{ color:#dee2e6; }}
  .stat-val.actual {{ color:#2f9e44; }}

  .card-badge {{ font-family:'JetBrains Mono',monospace; font-size:9px; font-weight:700;
                 border:1.5px solid; border-radius:4px; padding:3px 8px; letter-spacing:.1em;
                 flex-shrink:0; align-self:flex-start; }}
  .badge-high   {{ color:#f03e3e; border-color:#f03e3e; }}
  .badge-medium {{ color:#f59f00; border-color:#f59f00; }}
  .badge-low    {{ color:#868e96; border-color:#dee2e6; }}

  .no-events {{ font-size:12px; color:#ced4da; padding:8px 0; font-style:italic; }}
</style>
</head>
<body>

<div class="pg-header">
  <span class="pg-title">ECONOMIC CALENDAR</span>
  <span class="pg-range">{range_label}</span>
</div>
<div class="legend">
  <span class="leg"><span class="leg-dot" style="background:#f03e3e"></span>High Impact</span>
  <span class="leg"><span class="leg-dot" style="background:#f59f00"></span>Medium Impact</span>
  <span class="leg"><span class="leg-dot" style="background:#ced4da"></span>Low / None</span>
</div>

<div class="dow-grid">
  <div class="dow-cell">Mon</div><div class="dow-cell">Tue</div>
  <div class="dow-cell">Wed</div><div class="dow-cell">Thu</div>
  <div class="dow-cell">Fri</div><div class="dow-cell">Sat</div>
  <div class="dow-cell">Sun</div>
</div>

<div id="cal-root"></div>
<div id="detail-root"></div>

<script>
const DAYS   = {json.dumps(days_flat)};
const EVENTS = {json.dumps(all_days)};

let selectedKey = null;

function impactClass(impact) {{
  if (impact === 'high')   return 'high';
  if (impact === 'medium') return 'medium';
  return '';
}}

function badgeClass(impact) {{
  if (impact === 'high')   return 'badge-high';
  if (impact === 'medium') return 'badge-medium';
  return 'badge-low';
}}

function badgeLabel(impact) {{
  if (impact === 'high')   return 'HIGH';
  if (impact === 'medium') return 'MED';
  return 'LOW';
}}

function statValClass(val, is_actual, is_past) {{
  if (is_actual) {{
    if (!is_past) return 'na';
    if (val === 'N/A') return 'na';
    return 'actual';
  }}
  if (val === 'N/A') return 'na';
  return '';
}}

function renderCalendar() {{
  const root = document.getElementById('cal-root');
  root.innerHTML = '';

  // Group days by week
  const weeks = {{}};
  DAYS.forEach(d => {{
    const w = d.week_idx;
    if (!weeks[w]) weeks[w] = [];
    weeks[w].push(d);
  }});

  Object.keys(weeks).sort().forEach(wi => {{
    const grid = document.createElement('div');
    grid.className = 'cal-grid';

    weeks[wi].forEach(d => {{
      const evs = EVENTS[d.date] || [];
      let css = 'day-cell';
      if (d.is_today)   css += ' today';
      else if (d.is_past) css += ' past';
      if (d.is_weekend) css += ' weekend';

      const cell = document.createElement('div');
      cell.className = css;

      let html = `<span class="day-num">${{d.day}}${{d.month_abbr ? `<span class="month-tag">${{d.month_abbr}}</span>` : ''}}</span>`;

      if (evs.length === 0) {{
        // empty cell
      }} else {{
        evs.forEach((ev, i) => {{
          const ic = impactClass(ev.impact);
          html += `<div class="ev-row ${{ic}}" data-date="${{d.date}}" data-idx="${{i}}">
            <span class="ev-flag">${{ev.flag}}</span>
            <span class="ev-name">${{ev.event}}</span>
          </div>`;
        }});
      }}

      cell.innerHTML = html;
      grid.appendChild(cell);
    }});

    root.appendChild(grid);
    const spacer = document.createElement('div');
    spacer.style.height = '4px';
    root.appendChild(spacer);
  }});

  // Attach click listeners to all ev-rows
  document.querySelectorAll('.ev-row').forEach(row => {{
    row.addEventListener('click', e => {{
      const dateKey = row.getAttribute('data-date');
      const idx     = parseInt(row.getAttribute('data-idx'));
      const ev      = EVENTS[dateKey][idx];
      const key     = dateKey + '_' + idx;

      // Deselect all
      document.querySelectorAll('.ev-row.selected').forEach(r => r.classList.remove('selected'));

      if (selectedKey === key) {{
        selectedKey = null;
        renderDetail(null, null);
      }} else {{
        selectedKey = key;
        row.classList.add('selected');
        renderDetail(dateKey, ev);
      }}
      e.stopPropagation();
    }});
  }});
}}

function renderDetail(dateKey, ev) {{
  const root = document.getElementById('detail-root');
  if (!ev) {{ root.innerHTML = ''; return; }}

  const ic    = impactClass(ev.impact);
  const bc    = badgeClass(ev.impact);
  const bl    = badgeLabel(ev.impact);

  // Format date label
  const dt  = new Date(dateKey + 'T00:00:00');
  const dLabel = dt.toLocaleDateString('en-GB', {{weekday:'long', day:'2-digit', month:'long', year:'numeric'}});
  const tLabel = ev.time && ev.time.length > 10 ? ev.time.substring(11,16) + ' UTC' : '';

  const prevClass   = ev.prev     === 'N/A' ? 'na' : '';
  const estClass    = ev.estimate === 'N/A' ? 'na' : '';
  const actClass    = !ev.is_past ? 'na' : (ev.actual === 'N/A' ? 'na' : 'actual');
  const actDisplay  = ev.is_past ? ev.actual : 'N/A';

  root.innerHTML = `
  <div class="detail-panel">
    <div class="detail-header">
      <span class="detail-date">${{dLabel}}${{tLabel ? ' · ' + tLabel : ''}}</span>
      <button class="close-btn" onclick="closeDetail()">✕ Close</button>
    </div>
    <div class="ev-card ${{ic}}">
      <div class="card-flag">${{ev.flag}}</div>
      <div class="card-info">
        <div class="card-name">${{ev.event}}</div>
        <div class="card-meta">${{ev.cname}}</div>
        <div class="stats">
          <div>
            <div class="stat-label">Previous</div>
            <div class="stat-val ${{prevClass}}">${{ev.prev}}</div>
          </div>
          <div>
            <div class="stat-label">Forecast</div>
            <div class="stat-val ${{estClass}}">${{ev.estimate}}</div>
          </div>
          <div>
            <div class="stat-label">Actual</div>
            <div class="stat-val ${{actClass}}">${{actDisplay}}</div>
          </div>
        </div>
      </div>
      <div class="card-badge ${{bc}}">${{bl}}</div>
    </div>
  </div>`;
}}

function closeDetail() {{
  selectedKey = null;
  document.querySelectorAll('.ev-row.selected').forEach(r => r.classList.remove('selected'));
  document.getElementById('detail-root').innerHTML = '';
}}

renderCalendar();
</script>
</body>
</html>
"""

    components.html(html, height=1200, scrolling=True)

main()
