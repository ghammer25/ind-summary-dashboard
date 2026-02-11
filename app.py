import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
import os
import pickle
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="HC Reconciliation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shopee Palette ────────────────────────────────────────────────────────────
NAVY    = "#0D274C"
BLUE    = "#004AB5"
LBLUE   = "#1665C4"
CYAN    = "#218E7E"
ORANGE  = "#D3422A"
RED     = "#B50220"
YELLOW  = "#E5A300"
GOLD    = "#BF9B65"
GRAY    = "#A1A8B4"
LGRAY   = "#D7DADF"

st.markdown(f"""
<style>
    .block-container {{ padding-top: .8rem; padding-bottom: .5rem; }}
    section[data-testid="stSidebar"] {{ background: {NAVY}; }}
    section[data-testid="stSidebar"] * {{ color: white !important; }}
    section[data-testid="stSidebar"] label {{ font-size: 13px !important; }}
    section[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {{
        background: {ORANGE} !important;
    }}
    /* ── Tabs as pill buttons ── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 2px;
        background: #f0f2f6;
        border-radius: 30px;
        padding: 4px;
    }}
    .stTabs [data-baseweb="tab"] {{
        padding: 10px 28px;
        border-radius: 30px;
        font-size: 14px;
        font-weight: 500;
        color: #555;
        background: transparent;
        white-space: nowrap;
    }}
    .stTabs [aria-selected="true"] {{
        background: {ORANGE} !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(211,66,42,.25);
    }}
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {{
        display: none !important;
    }}
    /* ── KPI mini-cards ── */
    .kpi {{
        border-radius: 8px; padding: 10px 14px; text-align: center;
        color: white; margin-bottom: 6px;
        box-shadow: 0 2px 6px rgba(0,0,0,.12);
    }}
    .kpi h4 {{ margin:0; font-size:11px; opacity:.8; font-weight:400; letter-spacing:.3px; }}
    .kpi h2 {{ margin:2px 0 0; font-size:22px; font-weight:700; }}
    /* ── Report Table ── */
    .rtable {{
        width:100%; border-collapse:collapse; font-size:12px;
        font-family:'Segoe UI',sans-serif;
    }}
    .rtable th {{
        background:{NAVY}; color:white; padding:6px 8px;
        text-align:center; font-weight:600; border:1px solid #0a1c36;
        position:sticky; top:0; z-index:10; font-size:11px;
    }}
    .rtable th.gh {{ background:{BLUE}; font-size:12px; }}
    .rtable td {{ padding:5px 8px; border:1px solid #e0e4e8; text-align:right; }}
    .rtable td:first-child {{ text-align:left; font-weight:500; white-space:nowrap; }}
    .rtable tr:nth-child(even) {{ background:#f8f9fb; }}
    .rtable tr:hover {{ background:#edf1f7; }}
    .rtable tr.lv0 {{ font-weight:700; background:#e0e8f0; }}
    .rtable tr.lv1 {{ font-weight:600; }}
    .rtable tr.lv3 {{ font-size:11px; color:#555; }}
    .rtable tr.lv4 {{ font-size:10px; color:#888; }}
    .rtable tr.sep td {{ background:{LGRAY}; height:2px; padding:0; }}
    .vz {{ color:{CYAN}; font-weight:600; }}
    .vh {{ color:{RED}; font-weight:600; }}
    .vm {{ color:{ORANGE}; }}
    .vn {{ color:{GRAY}; font-style:italic; }}
    .sot-box {{
        background:#f0f2f6; border-left:3px solid {NAVY};
        padding:8px 12px; margin:4px 0; font-size:12px; border-radius:0 6px 6px 0;
    }}
    /* ── Employee Card ── */
    .emp-card {{
        background: white; border-radius: 10px; padding: 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,.08); margin-bottom: 16px;
        border: 1px solid #e0e4e8;
    }}
    .emp-card h3 {{ color: {NAVY}; margin: 0 0 4px; font-size: 18px; }}
    .emp-badge {{
        display: inline-block; padding: 3px 10px; border-radius: 12px;
        font-size: 11px; font-weight: 600; margin-right: 6px; color: white;
    }}
    .db-grid {{
        display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin: 12px 0;
    }}
    .db-box {{
        background: #f8f9fb; border-radius: 8px; padding: 12px;
        border: 1px solid #e0e4e8;
    }}
    .db-box h5 {{ margin: 0 0 8px; color: {NAVY}; font-size: 13px; }}
    .db-field {{ font-size: 12px; margin: 4px 0; }}
    .db-label {{ color: #888; font-size: 11px; }}
    .match {{ color: {CYAN}; }}
    .mismatch {{ color: {RED}; font-weight: 600; }}
    .move-warn {{
        background:#fff3cd; border-radius:6px; padding:8px 12px;
        margin-top:8px; font-size:12px; border:1px solid #ffc107;
    }}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════════════════════════
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]
CREDENTIALS_FILE = r"c:\Users\SPXBR26731\OneDrive - Seagroup\Área de Trabalho\codes\credentials.json"
TOKEN_FILE = r"c:\Users\SPXBR26731\OneDrive - Seagroup\Área de Trabalho\codes\token_write.pickle"


def get_gc():
    try:
        has_sa = "gcp_service_account" in st.secrets
    except Exception:
        has_sa = False
    if has_sa:
        from google.oauth2.service_account import Credentials as SA
        return gspread.authorize(SA.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=SCOPES))
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    return gspread.authorize(creds)


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════
SID = "1f3RtvA7F2SCdJ5XJkhXh0W8JOb6qnuyDj1zzhB1BanY"
GROWTH_SID = "1fMgeB-AMfq0_mGzwLjAK-dEBoECUJNeAEhdJSJ1cwM0"


@st.cache_data(ttl=300, show_spinner="Carregando CrossCheck...")
def load_crosscheck():
    gc = get_gc()
    for w in gc.open_by_key(SID).worksheets():
        if w.id == 358464056:
            raw = w.get_all_values()
            break
    else:
        return pd.DataFrame()
    col_names = [
        'empty', 'staff_id', 'spx', 'bpo', 'active',
        'in_hr', 'in_att', 'in_perf', 'all_dbs',
        'name_hr', 'name_att', 'name_perf', 'sot_name',
        'name_eq_hr', 'name_eq_att', 'name_eq_perf', 'name_eq_total',
        'func_hr_raw', 'func_att_raw', 'func_perf_raw',
        'func_hr', 'func_att', 'func_perf', 'sot_func',
        'func_eq_hr', 'func_eq_att', 'func_eq_perf', 'func_eq_total',
        'subteam_hr', 'subteam_att',
        'sc_hr', 'sc_att', 'sc_perf',
        'cnpj_hr', 'cnpj_att', 'cnpj_perf',
        'same_hub', 'moving', 'loc_sot',
        'loc_eq_hr', 'loc_eq_att', 'loc_eq_perf', 'loc_eq_total',
        'loc_type', 'new_hub', 'col_at',
        'n_ppl_hr', 'n_ppl_att', 'n_ppl_perf',
        'name_on_all', 'sot_n_ppl',
    ]
    headers = raw[3]
    while len(col_names) < len(headers):
        col_names.append(f'col_{len(col_names)}')
    df = pd.DataFrame(raw[4:], columns=col_names[:len(headers)])
    bool_cols = ['spx', 'bpo', 'active', 'in_hr', 'in_att', 'in_perf', 'all_dbs',
                 'name_eq_hr', 'name_eq_att', 'name_eq_perf', 'name_eq_total',
                 'func_eq_hr', 'func_eq_att', 'func_eq_perf', 'func_eq_total',
                 'same_hub', 'moving',
                 'loc_eq_hr', 'loc_eq_att', 'loc_eq_perf', 'loc_eq_total',
                 'new_hub', 'name_on_all']
    for c in bool_cols:
        if c in df.columns:
            df[c] = df[c].str.upper().eq('TRUE')
    df = df[df['staff_id'].str.strip().ne('') & df['staff_id'].ne('-')].copy()
    return df


@st.cache_data(ttl=300, show_spinner="Carregando HR...")
def load_hr():
    gc = get_gc()
    for w in gc.open_by_key(SID).worksheets():
        if w.id == 0:
            raw = w.get_all_values()
            break
    else:
        return pd.DataFrame()
    data = raw[2:]
    df = pd.DataFrame(data)
    if df.shape[1] > 16:
        hr = df[[1, 5, 6, 9, 16]].copy()
        hr.columns = ['bpo_name', 'categoria', 'staff_id', 'tipo_contrato', 'status_hr']
        hr = hr[hr['staff_id'].str.strip().ne('')].drop_duplicates(subset='staff_id')
        return hr
    return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner="Carregando Ind. Summary...")
def load_ind_summary():
    gc = get_gc()
    for w in gc.open_by_key(SID).worksheets():
        if w.id == 2047376970:
            return w.get_all_values()
    return []


@st.cache_data(ttl=300, show_spinner="Carregando HC Growth...")
def load_hc_growth():
    """Load DDMM date tabs from HC Growth spreadsheet and compute comparisons."""
    try:
        gc = get_gc()
        sp = gc.open_by_key(GROWTH_SID)
    except Exception:
        return None, None, None

    date_tabs = []
    for ws in sp.worksheets():
        t = ws.title
        if len(t) == 4 and t.isdigit():
            d, m = int(t[:2]), int(t[2:])
            if 1 <= d <= 31 and 1 <= m <= 12:
                date_tabs.append({'name': t, 'day': d, 'month': m, 'ws': ws})

    date_tabs.sort(key=lambda x: (x['month'], x['day']))
    if len(date_tabs) < 2:
        return None, None, None

    COL_R_REL = 15  # Column R relative to column C (index 2)

    # Group column definitions (relative to column C = index 2)
    GRP_COLS = {
        'All':   [0, 1, 2, 3],
        'FMH':   [5, 6, 7, 8],
        'SOC':   [10, 11, 12, 13],
        'HUB':   [15, 16, 17, 18],
        'Almox': [20, 21, 22, 23],
        'CB':    [25, 26, 27, 28],
        'RTS':   [30, 31, 32, 33],
    }
    SUBCOLS = ['HR', 'Att', 'Perf', 'Total']

    labels = None
    periods = []
    grp_periods = {(g, s): [] for g in GRP_COLS for s in SUBCOLS}

    for tab in date_tabs:
        raw = tab['ws'].get_all_values()
        start = 3
        for i, row in enumerate(raw):
            if len(row) > 1 and 'Main KPIs' in row[1]:
                start = i
                break
        rows = raw[start:]
        t_labels, t_vals = [], []
        grp_vals = {(g, s): [] for g in GRP_COLS for s in SUBCOLS}

        for row in rows:
            lbl = row[1] if len(row) > 1 else ''
            vals = row[2:] if len(row) > 2 else []
            vs = vals[COL_R_REL] if COL_R_REL < len(vals) else ''
            try:
                v = float(vs.replace(',', '').replace(' ', '')) if vs.strip() else 0
            except Exception:
                v = 0
            t_labels.append(lbl)
            t_vals.append(v)

            for grp, col_idxs in GRP_COLS.items():
                for si, ci in enumerate(col_idxs):
                    sc = SUBCOLS[si]
                    raw_v = vals[ci] if ci < len(vals) else ''
                    try:
                        gv = float(raw_v.replace(',', '').replace(' ', '')) if raw_v.strip() else 0
                    except Exception:
                        gv = 0
                    grp_vals[(grp, sc)].append(gv)

        if labels is None:
            labels = t_labels
        p_label = f"{tab['day']:02d}/{tab['month']:02d}"
        periods.append({
            'name': tab['name'],
            'label': p_label,
            'values': t_vals,
        })
        for key in grp_vals:
            grp_periods[key].append({'label': p_label, 'values': grp_vals[key]})

    n = len(labels)

    # Absolute values DataFrame
    abs_df = pd.DataFrame({'KPI': labels})
    for p in periods:
        v = p['values'] + [0] * max(0, n - len(p['values']))
        abs_df[p['label']] = v[:n]

    # Variation % DataFrame
    var_df = pd.DataFrame({'KPI': labels})
    for i in range(1, len(periods)):
        prev, curr = periods[i - 1]['values'], periods[i]['values']
        col = f"{periods[i - 1]['label']} → {periods[i]['label']}"
        var = []
        for j in range(n):
            vp = prev[j] if j < len(prev) else 0
            vc_ = curr[j] if j < len(curr) else 0
            if vp == 0:
                var.append(None if vc_ != 0 else 0.0)
            else:
                var.append(((vc_ - vp) / vp) * 100)
        var_df[col] = var

    # Accumulated (first vs last)
    fv, lv = periods[0]['values'], periods[-1]['values']
    acum = []
    for j in range(n):
        vf = fv[j] if j < len(fv) else 0
        vl = lv[j] if j < len(lv) else 0
        if vf == 0:
            acum.append(None if vl != 0 else 0.0)
        else:
            acum.append(((vl - vf) / vf) * 100)
    var_df['Acumulado'] = acum

    # Average per period
    np_ = len(periods) - 1
    var_df['Média'] = [a / np_ if a is not None else None for a in acum]

    # Build perf_data: (group, subcol) -> DataFrame with KPI rows × period columns
    perf_data = {}
    for (grp, sc), p_list in grp_periods.items():
        pdf = pd.DataFrame({'KPI': labels})
        for p in p_list:
            v = p['values'] + [0] * max(0, n - len(p['values']))
            pdf[p['label']] = v[:n]
        perf_data[(grp, sc)] = pdf

    return abs_df, var_df, perf_data


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def fmt(v):
    if v is None:
        return "N/A"
    if isinstance(v, float):
        v = int(v)
    return f"{v:,}"


def pn(val):
    if not val or val in ('', 'N/A'):
        return None
    try:
        return int(val.replace(',', '').replace('.', ''))
    except Exception:
        return None


def vc(val_str, parsed):
    if val_str in ('N/A', ''):
        return 'vn'
    if parsed == 0:
        return 'vz'
    if parsed and parsed > 500:
        return 'vh'
    if parsed and parsed > 100:
        return 'vm'
    return ''


def indent_level(s):
    sp = len(s) - len(s.lstrip())
    for lv, mx in enumerate([0, 3, 6, 9, 12, 15, 18], 0):
        if sp <= mx:
            return lv
    return 7


def render_employee_card(person):
    """Build employee card HTML as a compact string (no blank lines)."""
    g = lambda f, d='-': person.get(f, d) if person.get(f, d) else d
    tipo = "FTE" if person.get('spx', False) else "BPO"
    tipo_bg = BLUE if tipo == "FTE" else ORANGE
    active_str = "Ativo" if person.get('active', False) else "Inativo"
    active_bg = CYAN if active_str == "Ativo" else RED
    in_hr = person.get('in_hr', False)
    in_att = person.get('in_att', False)
    in_perf = person.get('in_perf', False)
    eq = lambda f: "match" if person.get(f, False) else "mismatch"
    ok = lambda v: "✅" if v else "❌"

    p = []
    p.append(f'<div class="emp-card">')
    p.append(f'<h3>{g("sot_name","N/A")}</h3>')
    p.append(f'<div style="margin-bottom:10px;">'
             f'<span class="emp-badge" style="background:{tipo_bg}">{tipo}</span>'
             f'<span class="emp-badge" style="background:{active_bg}">{active_str}</span>'
             f'<span style="font-size:13px;color:#666;margin-left:10px;">'
             f'Staff ID: <b>{g("staff_id","N/A")}</b></span></div>')
    p.append(f'<div style="font-size:13px;margin-bottom:8px;">'
             f'{ok(in_hr)} HR &nbsp;&nbsp;{ok(in_att)} Attendance &nbsp;&nbsp;'
             f'{ok(in_perf)} Performance</div>')
    p.append(f'<div style="font-size:12px;color:#888;margin-bottom:6px;">'
             f'Location SoT: <b>{g("loc_sot")}</b> · '
             f'Site Type: <b>{g("loc_type")}</b> · '
             f'Cargo SoT: <b>{g("sot_func")}</b></div>')

    bpo_n = g('bpo_name', 'N/A')
    cat = g('categoria', 'N/A')
    ctr = g('tipo_contrato', 'N/A')
    sts = g('status_hr', 'N/A')
    if any(v not in ('N/A', '', '-') for v in [bpo_n, cat, ctr, sts]):
        p.append(f'<div style="font-size:12px;color:#888;margin-bottom:12px;">'
                 f'BPO: <b>{bpo_n}</b> · Categoria: <b>{cat}</b> · '
                 f'Contrato: <b>{ctr}</b> · Status HR: <b>{sts}</b></div>')

    p.append('<div class="db-grid">')
    # HR
    p.append(f'<div class="db-box"><h5>{ok(in_hr)} HR</h5>'
             f'<div class="db-field"><span class="db-label">Nome:</span> '
             f'<span class="{eq("name_eq_hr")}">{g("name_hr")}</span></div>'
             f'<div class="db-field"><span class="db-label">Cargo:</span> '
             f'<span class="{eq("func_eq_hr")}">{g("func_hr")}</span></div>'
             f'<div class="db-field"><span class="db-label">Sort Code:</span> '
             f'<span class="{eq("loc_eq_hr")}">{g("sc_hr")}</span></div>'
             f'<div class="db-field"><span class="db-label">CNPJ:</span> {g("cnpj_hr")}</div>'
             f'<div class="db-field"><span class="db-label">Subteam:</span> {g("subteam_hr")}</div>'
             f'</div>')
    # Attendance
    p.append(f'<div class="db-box"><h5>{ok(in_att)} Attendance</h5>'
             f'<div class="db-field"><span class="db-label">Nome:</span> '
             f'<span class="{eq("name_eq_att")}">{g("name_att")}</span></div>'
             f'<div class="db-field"><span class="db-label">Cargo:</span> '
             f'<span class="{eq("func_eq_att")}">{g("func_att")}</span></div>'
             f'<div class="db-field"><span class="db-label">Sort Code:</span> '
             f'<span class="{eq("loc_eq_att")}">{g("sc_att")}</span></div>'
             f'<div class="db-field"><span class="db-label">CNPJ:</span> {g("cnpj_att")}</div>'
             f'<div class="db-field"><span class="db-label">Subteam:</span> {g("subteam_att")}</div>'
             f'</div>')
    # Performance
    p.append(f'<div class="db-box"><h5>{ok(in_perf)} Performance</h5>'
             f'<div class="db-field"><span class="db-label">Nome:</span> '
             f'<span class="{eq("name_eq_perf")}">{g("name_perf")}</span></div>'
             f'<div class="db-field"><span class="db-label">Cargo:</span> '
             f'<span class="{eq("func_eq_perf")}">{g("func_perf")}</span></div>'
             f'<div class="db-field"><span class="db-label">Sort Code:</span> '
             f'<span class="{eq("loc_eq_perf")}">{g("sc_perf")}</span></div>'
             f'<div class="db-field"><span class="db-label">CNPJ:</span> {g("cnpj_perf")}</div>'
             f'</div>')
    p.append('</div>')

    if person.get('moving', False) or person.get('new_hub', False):
        sh = "Sim" if person.get('same_hub', False) else "Não"
        mv = "Sim" if person.get('moving', False) else "Não"
        nh = "Sim" if person.get('new_hub', False) else "Não"
        p.append(f'<div class="move-warn">⚠️ <b>Movimentação:</b> '
                 f'Same Hub: {sh} · Moving: {mv} · New Hub: {nh}</div>')

    p.append('</div>')
    return ''.join(p)


def export_to_gsheets(df, title):
    """Create a new Google Sheet with the DataFrame data."""
    gc = get_gc()
    sh = gc.create(title)
    ws = sh.get_worksheet(0)
    ws.update_title("Dados")
    export_df = df.copy()
    for c in export_df.select_dtypes(include=[bool]).columns:
        export_df[c] = export_df[c].map({True: 'TRUE', False: 'FALSE'})
    export_df = export_df.fillna('')
    rows = [export_df.columns.tolist()] + export_df.astype(str).values.tolist()
    ws.update(range_name='A1', values=rows)
    sh.share('', perm_type='anyone', role='reader')
    return sh.url


DISPLAY_COLS = ['staff_id', 'sot_name', 'spx', 'bpo', 'active',
                'in_hr', 'in_att', 'in_perf', 'all_dbs',
                'loc_sot', 'loc_type', 'loc_eq_total',
                'sot_func', 'func_eq_total',
                'same_hub', 'moving', 'new_hub']
HR_COLS = ['bpo_name', 'categoria', 'tipo_contrato', 'status_hr']
COL_RENAME = {
    'staff_id': 'Staff ID', 'sot_name': 'Nome (SoT)',
    'spx': 'FTE', 'bpo': 'BPO', 'active': 'Active',
    'in_hr': 'In HR', 'in_att': 'In Att', 'in_perf': 'In Perf',
    'all_dbs': 'All DBs', 'loc_sot': 'Location SoT',
    'loc_type': 'Site Type', 'loc_eq_total': 'Sort Code OK',
    'sot_func': 'Cargo (SoT)', 'func_eq_total': 'Cargo OK',
    'same_hub': 'Same Hub', 'moving': 'Moving', 'new_hub': 'New Hub',
    'bpo_name': 'BPO Name', 'categoria': 'Categoria',
    'tipo_contrato': 'Tipo Contrato', 'status_hr': 'Status HR',
}


def build_display_df(df):
    """Build a display-ready DataFrame with renamed columns."""
    cols = DISPLAY_COLS[:]
    if 'bpo_name' in df.columns:
        cols += HR_COLS
    out = df[[c for c in cols if c in df.columns]].copy()
    return out.rename(columns=COL_RENAME)


def render_export_buttons(display_df, key_prefix):
    """Render CSV + Google Sheets export buttons."""
    c1, c2 = st.columns(2)
    with c1:
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            f"📥 CSV ({len(display_df):,} linhas)",
            csv, f"{key_prefix}.csv", "text/csv",
            use_container_width=True, key=f"csv_{key_prefix}")
    with c2:
        if st.button(f"📊 Google Sheets ({len(display_df):,} linhas)",
                     use_container_width=True, key=f"gs_{key_prefix}"):
            with st.spinner("Exportando para Google Sheets..."):
                try:
                    ts = datetime.now().strftime("%Y%m%d_%H%M")
                    url = export_to_gsheets(
                        display_df, f"HC_Recon_Export_{key_prefix}_{ts}")
                    st.success(f"Exportado! [Abrir planilha]({url})")
                except Exception as e:
                    st.error(f"Erro ao exportar: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: GRÁFICOS
# ═══════════════════════════════════════════════════════════════════════════════
def page_graficos(fdf):
    n_total = len(fdf)
    n_active = int(fdf['active'].sum())
    n_inactive = n_total - n_active
    n_fte = int(fdf['spx'].sum())
    n_bpo = int(fdf['bpo'].sum())
    n_in_hr = int(fdf['in_hr'].sum())
    n_in_att = int(fdf['in_att'].sum())
    n_in_perf = int(fdf['in_perf'].sum())
    n_all_dbs = int(fdf['all_dbs'].sum())

    r1 = st.columns(6)
    for col, (title, val, color) in zip(r1, [
        ("Total HCs", n_total, NAVY), ("Active", n_active, CYAN),
        ("Inactive", n_inactive, RED), ("FTEs", n_fte, BLUE),
        ("BPOs", n_bpo, ORANGE), ("All DBs", n_all_dbs, GOLD),
    ]):
        col.markdown(
            f'<div class="kpi" style="background:{color}">'
            f'<h4>{title}</h4><h2>{fmt(val)}</h2></div>',
            unsafe_allow_html=True)

    r2 = st.columns(6)
    for col, (title, val, color) in zip(r2, [
        ("In HR", n_in_hr, NAVY), ("In Attendance", n_in_att, NAVY),
        ("In Performance", n_in_perf, NAVY),
        ("Not in HR", n_total - n_in_hr, RED if n_total - n_in_hr > 0 else CYAN),
        ("Not in Att", n_total - n_in_att, RED if n_total - n_in_att > 0 else CYAN),
        ("Not in Perf", n_total - n_in_perf, RED if n_total - n_in_perf > 0 else CYAN),
    ]):
        col.markdown(
            f'<div class="kpi" style="background:{color}">'
            f'<h4>{title}</h4><h2>{fmt(val)}</h2></div>',
            unsafe_allow_html=True)

    st.markdown("")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("##### HC por Database")
        fig = go.Figure(go.Bar(
            x=['HR', 'Attendance', 'Performance'],
            y=[n_in_hr, n_in_att, n_in_perf],
            marker_color=[NAVY, CYAN, ORANGE],
            text=[fmt(n_in_hr), fmt(n_in_att), fmt(n_in_perf)],
            textposition='outside'))
        fig.update_layout(height=280, margin=dict(l=10, r=10, t=40, b=30),
                          yaxis_title="", xaxis_title="", font=dict(size=11))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("##### HC por Site Type")
        by_type = fdf['loc_type'].value_counts().reset_index()
        by_type.columns = ['Site Type', 'Count']
        by_type = by_type[
            by_type['Site Type'].str.strip().ne('')
            & by_type['Site Type'].ne('-')
            & by_type['Site Type'].str.lower().ne('nan')
        ]
        palette = [NAVY, BLUE, LBLUE, CYAN, ORANGE, RED, YELLOW, GOLD, GRAY]
        fig2 = px.bar(by_type, x='Site Type', y='Count', text_auto=True,
                      color='Site Type', color_discrete_sequence=palette)
        fig2.update_layout(height=280, margin=dict(l=10, r=10, t=40, b=30),
                           showlegend=False, yaxis_title="", xaxis_title="",
                           font=dict(size=11))
        fig2.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
        st.plotly_chart(fig2, use_container_width=True)

    with c3:
        st.markdown("##### FTE vs BPO")
        fig3 = go.Figure(go.Pie(
            labels=['FTE', 'BPO'], values=[n_fte, n_bpo],
            marker_colors=[BLUE, ORANGE], hole=0.5,
            textinfo='label+value+percent', textfont_size=12))
        fig3.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10),
                           showlegend=False, font=dict(size=11))
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")
    d1, d2 = st.columns(2)
    active_df = fdf[fdf['active']]

    with d1:
        st.markdown("##### Divergências - Isn't in DB")
        fte_a = active_df[active_df['spx']]
        bpo_a = active_df[active_df['bpo']]
        div_data = pd.DataFrame({
            'Database': ['HR', 'Attendance', 'Performance'] * 2,
            'Type': ['FTE'] * 3 + ['BPO'] * 3,
            'Count': [
                int((~fte_a['in_hr']).sum()), int((~fte_a['in_att']).sum()),
                int((~fte_a['in_perf']).sum()),
                int((~bpo_a['in_hr']).sum()), int((~bpo_a['in_att']).sum()),
                int((~bpo_a['in_perf']).sum()),
            ]
        })
        fig_d = px.bar(div_data, x='Database', y='Count', color='Type',
                       barmode='group', text_auto=True,
                       color_discrete_map={'FTE': BLUE, 'BPO': ORANGE})
        fig_d.update_layout(height=280, margin=dict(l=10, r=10, t=40, b=30),
                            yaxis_title="", xaxis_title="", font=dict(size=11),
                            legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"))
        fig_d.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
        st.plotly_chart(fig_d, use_container_width=True)

    with d2:
        st.markdown("##### Sort Code - Correto vs Incorreto")
        all_dbs_df = active_df[active_df['all_dbs']]
        correct = int(all_dbs_df['loc_eq_total'].sum())
        incorrect = int((~all_dbs_df['loc_eq_total']).sum())
        fig_sc = go.Figure()
        fig_sc.add_trace(go.Bar(name='Correto', x=['Sort Code'], y=[correct],
                                marker_color=CYAN, text=[fmt(correct)], textposition='inside'))
        fig_sc.add_trace(go.Bar(name='Incorreto', x=['Sort Code'], y=[incorrect],
                                marker_color=RED, text=[fmt(incorrect)], textposition='inside'))
        fig_sc.update_layout(barmode='stack', height=250,
                             margin=dict(l=10, r=10, t=10, b=30),
                             yaxis_title="", font=dict(size=11),
                             legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"))
        st.plotly_chart(fig_sc, use_container_width=True)

    st.markdown("---")
    with st.expander("📏 Source of Truth (SoT) Rules"):
        c_sc, c_jt = st.columns(2)
        with c_sc:
            st.markdown("**Sort Code:**")
            for sc, rule in [
                ("FTE & Same CNPJ", "Performance > Attendance > HR"),
                ("FTE, Diff CNPJ & Moving", "Performance > Attendance > HR"),
                ("FTE, Diff CNPJ & Non-Moving", "Attendance > Performance > HR"),
                ("BPO & Same CNPJ", "Performance > HR"),
                ("BPO, Diff CNPJ & Moving", "Performance > HR"),
                ("BPO, Diff CNPJ & Non-Moving", "HR > Performance"),
            ]:
                st.markdown(f'<div class="sot-box"><b>{sc}:</b> {rule}</div>',
                            unsafe_allow_html=True)
        with c_jt:
            st.markdown("**Job Title & Name:**")
            for sc, rule in [
                ("FTE", "Attendance > HR > Performance"),
                ("BPO", "HR > Performance"),
            ]:
                st.markdown(f'<div class="sot-box"><b>{sc}:</b> {rule}</div>',
                            unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: RECON
# ═══════════════════════════════════════════════════════════════════════════════
def page_recon(fdf, raw_summary):
    # ── Report Summary Table ──
    st.markdown("#### Resumo para Report")
    ops_report = ['FMH', 'HUB', 'SOC', 'Almox', 'CB', 'RTS', 'Total']
    active_ftes = fdf[(fdf['active']) & (fdf['spx'])]
    active_bpos = fdf[(fdf['active']) & (fdf['bpo'])]

    def count_by_op(subset, condition_fn, ops):
        result = {}
        for op in ops:
            grp = subset if op == 'Total' else subset[subset['loc_type'] == op]
            result[op] = int(condition_fn(grp)) if len(grp) > 0 else 0
        return result

    report_data = [
        ("Não contém nas bases - FTE",
         count_by_op(active_ftes, lambda g: (~g['all_dbs']).sum(), ops_report)),
        ("OK - FTE (Sort Code correto)",
         count_by_op(active_ftes[active_ftes['all_dbs']], lambda g: g['loc_eq_total'].sum(), ops_report)),
        ("Location divergente - FTE",
         count_by_op(active_ftes[active_ftes['all_dbs']], lambda g: (~g['loc_eq_total']).sum(), ops_report)),
        ("Não contém nas bases - BPO",
         count_by_op(active_bpos, lambda g: (~g['all_dbs']).sum(), ops_report)),
        ("OK - BPO (Sort Code correto)",
         count_by_op(active_bpos[active_bpos['all_dbs']], lambda g: g['loc_eq_total'].sum(), ops_report)),
        ("Location divergente - BPO",
         count_by_op(active_bpos[active_bpos['all_dbs']], lambda g: (~g['loc_eq_total']).sum(), ops_report)),
    ]

    h = ('<div style="overflow-x:auto;border-radius:8px;border:1px solid #e0e4e8;">'
         '<table class="rtable"><tr><th style="text-align:left;min-width:250px">Categoria</th>')
    for op in ops_report:
        h += f'<th class="gh">{op}</th>'
    h += '</tr>'
    for label, vals in report_data:
        h += f'<tr><td>{label}</td>'
        for op in ops_report:
            v = vals.get(op, 0)
            cls = 'vz' if v == 0 else ('vh' if v > 500 else ('vm' if v > 100 else ''))
            h += f'<td class="{cls}">{fmt(v)}</td>'
        h += '</tr>'
    h += '</table></div>'
    st.markdown(h, unsafe_allow_html=True)

    st.markdown("---")

    # ── Sub-tabs: Todos | Incorrect Sort Codes | Wrong Staff ID | Isn't in DB ──
    sub_all, sub_sc, sub_wsid, sub_nodb = st.tabs(
        ["Todos", "Incorrect Sort Codes", "Wrong Staff ID", "Isn't in DB"])

    def render_recon_table(sub_df, key_suffix):
        st.caption(f"{len(sub_df):,} registros")
        qs1, qs2, qs3, qs4 = st.columns(4)
        with qs1:
            st.metric("Isn't in all DBs", fmt(int((~sub_df['all_dbs']).sum())))
        with qs2:
            adb = sub_df[sub_df['all_dbs']]
            st.metric("Sort Code Incorreto", fmt(int((~adb['loc_eq_total']).sum()) if len(adb) > 0 else 0))
        with qs3:
            st.metric("Cargo Incorreto", fmt(int((~adb['func_eq_total']).sum()) if len(adb) > 0 else 0))
        with qs4:
            st.metric("Nome Incorreto", fmt(int((~adb['name_eq_total']).sum()) if len(adb) > 0 else 0))

        display_df = build_display_df(sub_df)
        st.dataframe(display_df, use_container_width=True, height=450, hide_index=True)
        render_export_buttons(display_df, key_suffix)

    with sub_all:
        render_recon_table(fdf, "todos")
    with sub_sc:
        render_recon_table(fdf[fdf['all_dbs'] & ~fdf['loc_eq_total']], "incorrect_sc")
    with sub_wsid:
        render_recon_table(fdf[fdf['active'] & ~fdf['all_dbs'] & fdf['name_on_all']], "wrong_sid")
    with sub_nodb:
        render_recon_table(fdf[~fdf['all_dbs']], "not_in_db")

    # ── Tabela Original Ind. Summary + Drill-Down ──
    st.markdown("---")
    with st.expander("📋 Tabela Original - Ind. Summary (clique para drill-down)"):
        if not raw_summary:
            st.warning("Ind. Summary não carregou.")
        else:
            GROUPS = [
                ("All",   [2, 3, 4, 5]),
                ("FMH",   [7, 8, 9, 10]),
                ("SOC",   [12, 13, 14, 15]),
                ("HUB",   [17, 18, 19, 20]),
                ("Almox", [22, 23, 24, 25]),
                ("CB",    [27, 28, 29, 30]),
                ("RTS",   [32, 33, 34, 35]),
            ]
            sel_g = st.multiselect("Operações:", [g[0] for g in GROUPS],
                                    default=["All"], key="recon_ops")
            if not sel_g:
                sel_g = ["All"]
            groups = [g for g in GROUPS if g[0] in sel_g]

            html = ('<div style="overflow-x:auto;max-height:650px;overflow-y:auto;'
                    'border-radius:8px;border:1px solid #e0e4e8;">'
                    '<table class="rtable">')
            html += '<tr><th rowspan="2" style="min-width:250px;text-align:left">KPI</th>'
            for name, _ in groups:
                html += f'<th colspan="4" class="gh">{name}</th>'
            html += '<th rowspan="2" style="min-width:180px;max-width:280px;text-align:left">Comments</th></tr>'
            html += '<tr>'
            for _ in groups:
                html += '<th>HR</th><th>Att.</th><th>Perf.</th><th>Total</th>'
            html += '</tr>'

            for ri in range(3, min(51, len(raw_summary))):
                row = raw_summary[ri]
                label = row[1] if len(row) > 1 else ''
                if not label.strip():
                    html += '<tr class="sep"><td colspan="100"></td></tr>'
                    continue
                lvl = indent_level(label)
                lbl = f'<span style="padding-left:{lvl*16}px">{label.strip()}</span>'
                html += f'<tr class="lv{min(lvl,4)}"><td>{lbl}</td>'
                for _, cidxs in groups:
                    for ci in cidxs:
                        v = row[ci] if ci < len(row) else ''
                        p = pn(v)
                        html += f'<td class="{vc(v,p)}">{v}</td>'
                comment = row[37] if len(row) > 37 else ''
                if comment:
                    short = comment[:70] + ('...' if len(comment) > 70 else '')
                    html += f'<td style="text-align:left;font-size:10px;color:#666" title="{comment}">{short}</td>'
                else:
                    html += '<td></td>'
                html += '</tr>'
            html += '</table></div>'
            st.markdown(html, unsafe_allow_html=True)

            # ── Drill-Down ──
            st.markdown("---")
            st.markdown("##### 🔍 Drill-Down - Ver colaboradores")
            dd1, dd2, dd3 = st.columns(3)
            with dd1:
                dd_op = st.selectbox("Operação:", ["All", "FMH", "HUB", "SOC", "Almox", "CB", "RTS"],
                                     key="dd_op")
            with dd2:
                dd_type = st.selectbox("Tipo:", ["FTE + BPO", "FTE", "BPO"], key="dd_type")
            with dd3:
                dd_kpi = st.selectbox("KPI:", [
                    "Active - In all DBs",
                    "Active - Isn't in all DBs",
                    "Active - Not in HR",
                    "Active - Not in Attendance",
                    "Active - Not in Performance",
                    "Active - Incorrect Sort Code",
                    "Active - Incorrect Name",
                    "Active - Incorrect Cargo",
                    "Active - Moving",
                    "Inactive",
                ], key="dd_kpi")

            dd_df = fdf.copy()
            if dd_op != "All":
                dd_df = dd_df[dd_df['loc_type'] == dd_op]
            if dd_type == "FTE":
                dd_df = dd_df[dd_df['spx']]
            elif dd_type == "BPO":
                dd_df = dd_df[dd_df['bpo']]

            if dd_kpi == "Active - In all DBs":
                dd_df = dd_df[dd_df['active'] & dd_df['all_dbs']]
            elif dd_kpi == "Active - Isn't in all DBs":
                dd_df = dd_df[dd_df['active'] & ~dd_df['all_dbs']]
            elif dd_kpi == "Active - Not in HR":
                dd_df = dd_df[dd_df['active'] & ~dd_df['in_hr']]
            elif dd_kpi == "Active - Not in Attendance":
                dd_df = dd_df[dd_df['active'] & ~dd_df['in_att']]
            elif dd_kpi == "Active - Not in Performance":
                dd_df = dd_df[dd_df['active'] & ~dd_df['in_perf']]
            elif dd_kpi == "Active - Incorrect Sort Code":
                dd_df = dd_df[dd_df['active'] & dd_df['all_dbs'] & ~dd_df['loc_eq_total']]
            elif dd_kpi == "Active - Incorrect Name":
                dd_df = dd_df[dd_df['active'] & dd_df['all_dbs'] & ~dd_df['name_eq_total']]
            elif dd_kpi == "Active - Incorrect Cargo":
                dd_df = dd_df[dd_df['active'] & dd_df['all_dbs'] & ~dd_df['func_eq_total']]
            elif dd_kpi == "Active - Moving":
                dd_df = dd_df[dd_df['active'] & dd_df['moving']]
            elif dd_kpi == "Inactive":
                dd_df = dd_df[~dd_df['active']]

            st.caption(f"{len(dd_df):,} colaboradores encontrados")
            if len(dd_df) > 0:
                dd_display = build_display_df(dd_df)
                st.dataframe(dd_display, use_container_width=True, height=350, hide_index=True)
                render_export_buttons(dd_display, "drilldown")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: CONSULTA COLABORADOR(A)
# ═══════════════════════════════════════════════════════════════════════════════
def page_consulta(df):
    st.markdown("#### Consulta Colaborador(a)")
    st.caption("Buscar por Staff ID, Nome ou CPF/CNPJ")

    search = st.text_input("🔍 Buscar:", placeholder="Digite Staff ID, Nome ou CPF...",
                           key="emp_search")

    if not search:
        st.info("Digite um termo de busca acima para consultar colaboradores.")
        return

    term = search.strip().upper()
    match_mask = (
        df['staff_id'].str.upper().str.contains(term, na=False) |
        df['sot_name'].str.upper().str.contains(term, na=False) |
        df['name_hr'].str.upper().str.contains(term, na=False) |
        df['name_att'].str.upper().str.contains(term, na=False) |
        df['name_perf'].str.upper().str.contains(term, na=False) |
        df['cnpj_hr'].str.upper().str.contains(term, na=False) |
        df['cnpj_att'].str.upper().str.contains(term, na=False) |
        df['cnpj_perf'].str.upper().str.contains(term, na=False)
    )
    results = df[match_mask]

    if results.empty:
        st.warning(f"Nenhum resultado para '{search}'")
        return

    st.success(f"{len(results)} resultado(s) encontrado(s)")

    # Export results
    res_display = build_display_df(results)
    render_export_buttons(res_display, "consulta")

    st.markdown("---")

    if len(results) > 50:
        st.warning("Muitos resultados. Mostrando os primeiros 50. Refine a busca.")
        results = results.head(50)

    for _, person in results.iterrows():
        st.markdown(render_employee_card(person), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: HC GROWTH
# ═══════════════════════════════════════════════════════════════════════════════
def page_hc_growth(abs_df, var_df):
    st.markdown("#### 📈 HC Growth - Evolução por Período")

    if abs_df is None or var_df is None:
        st.warning("Dados de HC Growth não disponíveis. Verifique se a planilha possui "
                    "pelo menos 2 abas no formato DDMM.")
        return

    kpis = abs_df['KPI'].tolist()
    period_cols = [c for c in abs_df.columns if c != 'KPI']
    var_period_cols = [c for c in var_df.columns if c not in ('KPI', 'Acumulado', 'Média')]
    last_var = var_period_cols[-1] if var_period_cols else None

    # ── KPI Cards ──
    card_defs = []
    for i, k in enumerate(kpis):
        s = k.strip()
        if s == '# of HCs':
            card_defs.append((i, 'Total HCs', NAVY))
        elif k == '   Active':
            card_defs.append((i, 'Ativos', CYAN))
        elif k == '   Inactive':
            card_defs.append((i, 'Inativos', RED))

    # Find Active FTEs and BPOs (appear after '   Active' at indent level ~1)
    active_found = False
    fte_done = False
    for i, k in enumerate(kpis):
        if k == '   Active':
            active_found = True
        elif active_found and not fte_done and k.strip() == 'FTEs' and indent_level(k) <= 2:
            card_defs.append((i, 'FTEs Ativos', BLUE))
            fte_done = True
        elif fte_done and k.strip() == 'BPOs' and indent_level(k) <= 2:
            card_defs.append((i, 'BPOs Ativos', ORANGE))
            break

    if card_defs and last_var:
        cols = st.columns(min(len(card_defs), 6))
        for col, (idx, name, color) in zip(cols, card_defs[:6]):
            val = abs_df.loc[idx, period_cols[-1]] if idx < len(abs_df) else 0
            var_val = var_df.loc[idx, last_var] if idx < len(var_df) else None
            if pd.isna(var_val):
                var_val = None
            var_str = f"{var_val:+.1f}%" if var_val is not None else "N/A"
            arrow = "↑" if var_val and var_val > 0 else ("↓" if var_val and var_val < 0 else "→")
            col.markdown(
                f'<div class="kpi" style="background:{color}">'
                f'<h4>{name}</h4><h2>{fmt(val)}</h2>'
                f'<span style="font-size:11px;opacity:.85">{arrow} {var_str}</span>'
                f'</div>', unsafe_allow_html=True)

    st.markdown("")

    # ── Evolution Chart ──
    st.markdown("##### Evolução - Valores Absolutos")

    # Build unique options for multiselect
    options = []
    opt_to_idx = {}
    seen = {}
    for i, k in enumerate(kpis):
        s = k.strip()
        if not s:
            continue
        if s in seen:
            seen[s] += 1
            disp = f"{s} [{seen[s]}]"
        else:
            seen[s] = 1
            disp = s
        options.append(disp)
        opt_to_idx[disp] = i

    defaults = [o for o in options if o in ('# of HCs', 'Active', 'Inactive')][:3]
    selected = st.multiselect("KPIs:", options, default=defaults, key="hcg_sel")

    if selected:
        fig = go.Figure()
        chart_colors = [NAVY, CYAN, RED, BLUE, ORANGE, YELLOW, GOLD, LBLUE, GRAY]
        for si, sel in enumerate(selected):
            idx = opt_to_idx[sel]
            values = [abs_df.loc[idx, c] for c in period_cols]
            fig.add_trace(go.Scatter(
                x=period_cols, y=values,
                mode='lines+markers+text', name=sel,
                line=dict(color=chart_colors[si % len(chart_colors)], width=2),
                text=[fmt(v) for v in values],
                textposition='top center', textfont=dict(size=10)))
        fig.update_layout(
            height=350, margin=dict(l=10, r=10, t=40, b=30),
            font=dict(size=11), xaxis_title="Período", yaxis_title="",
            legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── Variation % Table ──
    st.markdown("##### Variação % por Período")
    all_v_cols = var_period_cols + ['Acumulado', 'Média']

    h = ('<div style="overflow-x:auto;max-height:600px;overflow-y:auto;'
         'border-radius:8px;border:1px solid #e0e4e8;">'
         '<table class="rtable"><tr>'
         '<th style="text-align:left;min-width:280px">KPI</th>')
    for vc in all_v_cols:
        cls = 'gh' if vc in ('Acumulado', 'Média') else ''
        h += f'<th class="{cls}">{vc}</th>'
    h += '</tr>'

    for i, kpi in enumerate(kpis):
        if not kpi.strip():
            h += '<tr class="sep"><td colspan="100"></td></tr>'
            continue
        lvl = indent_level(kpi)
        lbl = f'<span style="padding-left:{lvl*16}px">{kpi.strip()}</span>'
        h += f'<tr class="lv{min(lvl, 4)}"><td>{lbl}</td>'
        for vc in all_v_cols:
            if vc not in var_df.columns or i >= len(var_df):
                h += '<td>-</td>'
                continue
            val = var_df.loc[i, vc]
            if pd.isna(val):
                h += f'<td style="color:{GOLD};font-style:italic">Novo</td>'
            elif val == 0:
                h += f'<td style="color:{GRAY}">0.0%</td>'
            elif val > 0:
                h += f'<td style="color:{RED};font-weight:600">+{val:.1f}%</td>'
            else:
                h += f'<td style="color:{CYAN};font-weight:600">{val:.1f}%</td>'
        h += '</tr>'
    h += '</table></div>'
    st.markdown(h, unsafe_allow_html=True)

    st.markdown("---")

    # ── Absolute Values Table ──
    with st.expander("📊 Valores Absolutos por Período"):
        h2 = ('<div style="overflow-x:auto;max-height:600px;overflow-y:auto;'
              'border-radius:8px;border:1px solid #e0e4e8;">'
              '<table class="rtable"><tr>'
              '<th style="text-align:left;min-width:280px">KPI</th>')
        for pc in period_cols:
            h2 += f'<th>{pc}</th>'
        h2 += '</tr>'
        for i, kpi in enumerate(kpis):
            if not kpi.strip():
                h2 += '<tr class="sep"><td colspan="100"></td></tr>'
                continue
            lvl = indent_level(kpi)
            lbl = f'<span style="padding-left:{lvl*16}px">{kpi.strip()}</span>'
            h2 += f'<tr class="lv{min(lvl, 4)}"><td>{lbl}</td>'
            for pc in period_cols:
                v = abs_df.loc[i, pc] if i < len(abs_df) else 0
                cls = f'style="color:{GRAY}"' if v == 0 else ''
                h2 += f'<td {cls}>{fmt(v)}</td>'
            h2 += '</tr>'
        h2 += '</table></div>'
        st.markdown(h2, unsafe_allow_html=True)

    # ── Export ──
    st.markdown("---")
    st.markdown("**Exportar Variação %:**")
    render_export_buttons(var_df, "hcg_var")
    st.markdown("**Exportar Valores Absolutos:**")
    render_export_buttons(abs_df, "hcg_abs")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: PERFORMANCE HUBS
# ═══════════════════════════════════════════════════════════════════════════════
PERF_GROUPS_ORDER = ['All', 'FMH', 'SOC', 'HUB', 'Almox', 'CB', 'RTS']
PERF_SUBCOLS = ['HR', 'Att', 'Perf', 'Total']


def page_performance(perf_data):
    st.markdown("#### 🏢 Performance Hubs")

    if perf_data is None:
        st.warning("Dados de Performance Hubs não disponíveis. Verifique se a planilha HC Growth "
                    "possui pelo menos 2 abas no formato DDMM.")
        return

    sample_key = list(perf_data.keys())[0]
    sample_df = perf_data[sample_key]
    period_cols = [c for c in sample_df.columns if c != 'KPI']
    if not period_cols:
        st.warning("Nenhum período disponível.")
        return
    latest = period_cols[-1]
    prev = period_cols[-2] if len(period_cols) >= 2 else None
    kpis = sample_df['KPI'].tolist()

    # Find key row indices
    hc_idx = active_idx = None
    for i, k in enumerate(kpis):
        if k.strip() == '# of HCs':
            hc_idx = i
        if k == '   Active':
            active_idx = i
    target_idx = active_idx if active_idx is not None else (hc_idx if hc_idx is not None else 0)

    # ── KPI Cards: HRIS / Att / Perf / Total (All) ──
    st.markdown(f"##### Visão Geral — Active ({latest})")
    cols = st.columns(4)
    sc_colors = [NAVY, CYAN, ORANGE, BLUE]
    for col, sc, color in zip(cols, PERF_SUBCOLS, sc_colors):
        key = ('All', sc)
        val = perf_data[key].loc[target_idx, latest] if key in perf_data else 0
        var_val = None
        if prev and key in perf_data:
            pv = perf_data[key].loc[target_idx, prev]
            if pv != 0:
                var_val = ((val - pv) / pv) * 100
        var_str = f"{var_val:+.1f}%" if var_val is not None else "N/A"
        arrow = "↑" if var_val and var_val > 0 else ("↓" if var_val and var_val < 0 else "→")
        col.markdown(
            f'<div class="kpi" style="background:{color}">'
            f'<h4>{sc} (Active)</h4><h2>{fmt(val)}</h2>'
            f'<span style="font-size:11px;opacity:.85">{arrow} {var_str}</span>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("")

    # ── Overview Table: all operations × HRIS/Att/Perf/Total ──
    st.markdown(f"##### Breakdown por Operação — Active ({latest})")
    h = ('<div style="overflow-x:auto;border-radius:8px;border:1px solid #e0e4e8;">'
         '<table class="rtable"><tr>'
         '<th style="text-align:left;min-width:100px">Operação</th>')
    for sc in PERF_SUBCOLS:
        h += f'<th class="gh">{sc}</th>'
    h += '<th>Var% Total</th></tr>'

    for grp in PERF_GROUPS_ORDER:
        is_focus = grp in ('FMH', 'HUB')
        row_style = ' style="background:#e8f0fe;"' if is_focus else ''
        h += f'<tr{row_style}><td><b>{grp}</b></td>'
        for sc in PERF_SUBCOLS:
            key = (grp, sc)
            if key in perf_data and target_idx < len(perf_data[key]):
                val = perf_data[key].loc[target_idx, latest]
                cls = f'style="color:{GRAY}"' if val == 0 else ''
                h += f'<td {cls}>{fmt(val)}</td>'
            else:
                h += '<td>-</td>'
        # Var% Total (latest vs previous)
        total_key = (grp, 'Total')
        if prev and total_key in perf_data and target_idx < len(perf_data[total_key]):
            cv = perf_data[total_key].loc[target_idx, latest]
            pv = perf_data[total_key].loc[target_idx, prev]
            if pv != 0:
                vr = ((cv - pv) / pv) * 100
                color = CYAN if vr <= 0 else RED
                h += f'<td style="color:{color};font-weight:600">{vr:+.1f}%</td>'
            else:
                h += f'<td style="color:{GOLD};font-style:italic">N/A</td>'
        else:
            h += '<td>-</td>'
        h += '</tr>'
    h += '</table></div>'
    st.markdown(h, unsafe_allow_html=True)

    st.markdown("---")

    # ── FMH & HUB Detail Tabs ──
    st.markdown("##### Detalhe — FMH & HUB")
    tab_fmh, tab_hub = st.tabs(["FMH", "HUB"])

    for tab, grp_name in [(tab_fmh, 'FMH'), (tab_hub, 'HUB')]:
        with tab:
            # KPI cards
            kcols = st.columns(4)
            for kcol, sc, color in zip(kcols, PERF_SUBCOLS, sc_colors):
                key = (grp_name, sc)
                val = perf_data[key].loc[target_idx, latest] if key in perf_data else 0
                var_val = None
                if prev and key in perf_data:
                    pv = perf_data[key].loc[target_idx, prev]
                    if pv != 0:
                        var_val = ((val - pv) / pv) * 100
                var_str = f"{var_val:+.1f}%" if var_val is not None else "N/A"
                arrow = "↑" if var_val and var_val > 0 else ("↓" if var_val and var_val < 0 else "→")
                kcol.markdown(
                    f'<div class="kpi" style="background:{color}">'
                    f'<h4>{sc} (Active)</h4><h2>{fmt(val)}</h2>'
                    f'<span style="font-size:11px;opacity:.85">{arrow} {var_str}</span>'
                    f'</div>', unsafe_allow_html=True)

            st.markdown("")

            # Detail table: KPI × (HR, Att, Perf, Total) for latest period
            st.markdown(f"###### Tabela Detalhada — {grp_name} ({latest})")
            h = ('<div style="overflow-x:auto;max-height:500px;overflow-y:auto;'
                 'border-radius:8px;border:1px solid #e0e4e8;">'
                 '<table class="rtable"><tr>'
                 '<th style="text-align:left;min-width:250px">KPI</th>')
            for sc in PERF_SUBCOLS:
                h += f'<th>{sc}</th>'
            h += '</tr>'
            for i, kpi in enumerate(kpis):
                if not kpi.strip():
                    h += '<tr class="sep"><td colspan="100"></td></tr>'
                    continue
                lvl = indent_level(kpi)
                lbl = f'<span style="padding-left:{lvl*16}px">{kpi.strip()}</span>'
                h += f'<tr class="lv{min(lvl, 4)}"><td>{lbl}</td>'
                for sc in PERF_SUBCOLS:
                    key = (grp_name, sc)
                    if key in perf_data and i < len(perf_data[key]):
                        val = perf_data[key].loc[i, latest]
                        cls = f'style="color:{GRAY}"' if val == 0 else ''
                        h += f'<td {cls}>{fmt(val)}</td>'
                    else:
                        h += '<td>-</td>'
                h += '</tr>'
            h += '</table></div>'
            st.markdown(h, unsafe_allow_html=True)

            st.markdown("---")

            # Historical evolution chart for Total subcol
            st.markdown(f"###### Evolução Temporal — {grp_name}")
            ch1, ch2 = st.columns(2)
            with ch1:
                st.markdown("**Total (Active)**")
                total_key = (grp_name, 'Total')
                if total_key in perf_data:
                    tdf = perf_data[total_key]
                    chart_kpis = []
                    for i, k in enumerate(kpis):
                        s = k.strip()
                        if s in ('# of HCs', 'Active', 'Inactive'):
                            chart_kpis.append((i, s))
                    if chart_kpis:
                        fig = go.Figure()
                        ccolors = [NAVY, CYAN, RED]
                        for ci, (idx, name) in enumerate(chart_kpis):
                            values = [tdf.loc[idx, c] for c in period_cols]
                            fig.add_trace(go.Scatter(
                                x=period_cols, y=values,
                                mode='lines+markers+text', name=name,
                                line=dict(color=ccolors[ci % len(ccolors)], width=2),
                                text=[fmt(v) for v in values],
                                textposition='top center', textfont=dict(size=9)))
                        fig.update_layout(
                            height=300, margin=dict(l=10, r=10, t=40, b=30),
                            font=dict(size=11), xaxis_title="Período",
                            legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"))
                        st.plotly_chart(fig, use_container_width=True, key=f"perf_total_{grp_name}")

            with ch2:
                st.markdown("**HR / Att / Perf (Active)**")
                if active_idx is not None:
                    fig2 = go.Figure()
                    sc_colors_chart = [NAVY, CYAN, ORANGE]
                    for si, sc in enumerate(['HR', 'Att', 'Perf']):
                        key = (grp_name, sc)
                        if key in perf_data:
                            values = [perf_data[key].loc[active_idx, c] for c in period_cols]
                            fig2.add_trace(go.Scatter(
                                x=period_cols, y=values,
                                mode='lines+markers+text', name=sc,
                                line=dict(color=sc_colors_chart[si], width=2),
                                text=[fmt(v) for v in values],
                                textposition='top center', textfont=dict(size=9)))
                    fig2.update_layout(
                        height=300, margin=dict(l=10, r=10, t=40, b=30),
                        font=dict(size=11), xaxis_title="Período",
                        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"))
                    st.plotly_chart(fig2, use_container_width=True, key=f"perf_db_{grp_name}")

            # Historical table: periods as columns, Total values
            with st.expander(f"📊 Evolução {grp_name} — Valores por Período (Total)"):
                total_key = (grp_name, 'Total')
                if total_key in perf_data:
                    tdf = perf_data[total_key]
                    h2 = ('<div style="overflow-x:auto;max-height:500px;overflow-y:auto;'
                          'border-radius:8px;border:1px solid #e0e4e8;">'
                          '<table class="rtable"><tr>'
                          '<th style="text-align:left;min-width:250px">KPI</th>')
                    for pc in period_cols:
                        h2 += f'<th>{pc}</th>'
                    h2 += '</tr>'
                    for i, kpi in enumerate(kpis):
                        if not kpi.strip():
                            h2 += '<tr class="sep"><td colspan="100"></td></tr>'
                            continue
                        lvl = indent_level(kpi)
                        lbl = f'<span style="padding-left:{lvl*16}px">{kpi.strip()}</span>'
                        h2 += f'<tr class="lv{min(lvl, 4)}"><td>{lbl}</td>'
                        for pc in period_cols:
                            val = tdf.loc[i, pc] if i < len(tdf) else 0
                            cls = f'style="color:{GRAY}"' if val == 0 else ''
                            h2 += f'<td {cls}>{fmt(val)}</td>'
                        h2 += '</tr>'
                    h2 += '</table></div>'
                    st.markdown(h2, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: GUIA DE USO
# ═══════════════════════════════════════════════════════════════════════════════
def page_guia():
    st.markdown("#### 📖 Guia de Uso")
    st.markdown("---")

    st.markdown("##### Fontes de Dados")
    st.markdown("""
Este dashboard consolida dados de **3 abas** da planilha de Reconciliation:

| Fonte | Aba (gid) | Descrição |
|-------|-----------|-----------|
| **CrossCheck** | `358464056` | Tabela principal de reconciliação. Cruza dados de HR, Attendance e Performance para cada colaborador (staff\_id). Contém ~40K linhas com flags booleanas (in\_hr, in\_att, in\_perf, etc.), nomes, cargos, sort codes e CNPJs de cada base. |
| **HR** | `0` | Base de dados de Recursos Humanos. Fornece dados complementares: nome do BPO, Categoria HC, Tipo de Contrato e Status HR. Usada para enriquecer filtros da sidebar. |
| **Ind. Summary** | `2047376970` | Tabela resumo por operação (FMH, SOC, HUB, Almox, CB, RTS) com contagens de HR, Attendance, Performance e Total para cada KPI. Exibida na aba Recon com possibilidade de drill-down. |
""")

    st.markdown("##### Como os Dados São Processados")
    st.markdown("""
1. **CrossCheck** é carregada com cabeçalho na **linha 4** (row index 3) e dados a partir da **linha 5**.
   Colunas booleanas (TRUE/FALSE) são convertidas para `bool` do Python.
   Linhas com `staff_id` vazio ou "-" são removidas.

2. **HR** é carregada e faz-se merge com CrossCheck via `staff_id` (left join),
   adicionando colunas: `bpo_name`, `categoria`, `tipo_contrato`, `status_hr`.

3. **Filtros da sidebar** são aplicados sobre o DataFrame combinado.

4. **Cache**: Dados ficam em cache por **5 minutos** (`ttl=300`). Use o botão
   "🔄 Atualizar Dados" na sidebar para forçar recarga.
""")

    st.markdown("##### Navegação")
    st.markdown("""
- **📊 Gráficos** — KPIs principais (Total, Active, Inactive, FTE, BPO, por database)
  e gráficos interativos (HC por Database, HC por Site Type, FTE vs BPO, Divergências, Sort Code).
- **📋 Recon** — Tabela resumo tipo report, sub-abas (Todos, Incorrect Sort Codes,
  Wrong Staff ID, Isn't in DB), tabela original Ind. Summary com drill-down.
- **📈 HC Growth** — Evolução de KPIs ao longo dos períodos (abas DDMM da planilha
  de acompanhamento). Gráfico de linha, tabela de variação % e valores absolutos.
- **🏢 Performance Hubs** — Breakdown de HRIS, Attendance, Performance e Total
  por operação (FMH, HUB, SOC, etc.). Detalhe completo e evolução temporal para FMH e HUB.
- **🔍 Consulta Colaborador(a)** — Busca individual por Staff ID, Nome ou CPF/CNPJ.
  Exibe card detalhado com dados de cada base (HR, Attendance, Performance).
- **📖 Guia de Uso** — Esta página.
- **📚 Glossário** — Definições de termos e siglas.
""")

    st.markdown("##### Exportação")
    st.markdown("""
- **CSV**: Download direto pelo navegador.
- **Google Sheets**: Cria uma nova planilha no Google Drive com os dados filtrados.
  A planilha é compartilhada como "Qualquer pessoa com o link pode visualizar".
""")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: GLOSSÁRIO
# ═══════════════════════════════════════════════════════════════════════════════
def page_glossario():
    st.markdown("#### 📚 Glossário")
    st.markdown("---")

    terms = [
        ("FMH", "First Mile Hub", "Hub de primeira milha — ponto de coleta inicial dos pacotes."),
        ("HUB", "Hub (Centro de Distribuição)", "Centro de triagem e distribuição intermediário."),
        ("SOC", "Sorting Center", "Centro de triagem automatizada de pacotes."),
        ("Almox", "Almoxarifado", "Estoque / depósito de materiais e insumos."),
        ("CB", "Cross Belt", "Esteira de triagem com belts cruzados para separação automatizada."),
        ("RTS", "Return to Sender", "Operação de devolução de pacotes ao remetente."),
        ("FTE", "Full-Time Employee", "Colaborador contratado diretamente (CLT SPX). No dashboard, aparece como 'SPX = TRUE'."),
        ("BPO", "Business Process Outsourcing", "Colaborador terceirizado. No dashboard, aparece como 'BPO = TRUE'."),
        ("HC", "Headcount", "Contagem de pessoas / colaboradores."),
        ("SoT", "Source of Truth", "Fonte da verdade — qual base de dados tem prioridade para cada campo (nome, cargo, sort code). As regras variam por tipo de HC (FTE/BPO) e situação (same CNPJ, moving, etc.)."),
        ("Sort Code", "Sort Code (Código de Localidade)", "Código que identifica a unidade/localidade onde o colaborador está alocado. Cada base (HR, Att, Perf) possui seu próprio sort code."),
        ("CNPJ", "Cadastro Nacional da Pessoa Jurídica", "Identificador fiscal da empresa. Usado para verificar se o colaborador está no mesmo CNPJ nas bases."),
        ("CPF", "Cadastro de Pessoas Físicas", "Identificador fiscal individual do colaborador."),
        ("Staff ID", "Staff ID", "Identificador único do colaborador no sistema HR."),
        ("In HR / In Att / In Perf", "Presença nas Bases", "Indica se o colaborador foi encontrado na base de HR, Attendance ou Performance, respectivamente."),
        ("All DBs", "In All Databases", "TRUE se o colaborador está presente em todas as 3 bases (HR, Attendance, Performance)."),
        ("Moving", "Em Movimentação", "Colaborador que está em processo de transferência entre unidades."),
        ("New Hub", "Novo Hub", "Indica se o colaborador foi alocado em um hub recém-criado."),
        ("Same Hub", "Mesmo Hub", "Indica se o sort code aponta para o mesmo hub em todas as bases."),
        ("Incorrect Sort Code", "Sort Code Divergente", "O sort code do colaborador não é igual em todas as bases (HR ≠ Att ≠ Perf)."),
        ("Isn't in DB", "Não Está na Base", "Colaborador ativo que não foi encontrado em pelo menos uma das 3 bases."),
        ("Ind. Summary", "Individual Summary", "Tabela resumo com contagens agregadas por operação e KPI."),
    ]

    for sigla, nome, desc in terms:
        st.markdown(
            f'<div style="background:#f8f9fb;border-radius:8px;padding:10px 14px;'
            f'margin-bottom:8px;border-left:3px solid {NAVY};">'
            f'<b style="color:{ORANGE};font-size:14px;">{sigla}</b> '
            f'<span style="color:{NAVY};font-size:13px;">— {nome}</span><br>'
            f'<span style="font-size:12px;color:#555;">{desc}</span></div>',
            unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    df_cc = load_crosscheck()
    df_hr = load_hr()
    raw_summary = load_ind_summary()
    abs_growth, var_growth, perf_data = load_hc_growth()

    if df_cc.empty:
        st.error("Erro ao carregar CrossCheck.")
        return

    if not df_hr.empty:
        df = df_cc.merge(df_hr, on='staff_id', how='left')
    else:
        df = df_cc.copy()
        for c in ['bpo_name', 'categoria', 'tipo_contrato', 'status_hr']:
            df[c] = ''

    for c in ['bpo_name', 'categoria', 'tipo_contrato', 'status_hr']:
        df[c] = df[c].fillna('N/A')

    # ── Sidebar Filters ──
    with st.sidebar:
        st.markdown("## 📊 Filtros")
        st.markdown("---")
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown("---")

        tipo_hc = st.multiselect("Tipo HC", ["FTE (SPX)", "BPO"],
                                  default=["FTE (SPX)", "BPO"])
        loc_types = sorted([l for l in df['loc_type'].unique() if l.strip() and l != '-'])
        sel_loc_type = st.multiselect("Site Type", loc_types, default=loc_types)
        available_locs = sorted(
            df[df['loc_sot'].str.strip().ne('') & df['loc_sot'].ne('-')]['loc_sot'].unique())
        sel_locs = st.multiselect("Location (Sort Code)", available_locs,
                                   default=[], placeholder="Todos")
        st.markdown("---")

        col_inhr, col_inatt, col_inperf = st.columns(3)
        with col_inhr:
            in_hr_filter = st.selectbox("In HR?", ["All", "Yes", "No"])
        with col_inatt:
            in_att_filter = st.selectbox("In Att?", ["All", "Yes", "No"])
        with col_inperf:
            in_perf_filter = st.selectbox("In Perf?", ["All", "Yes", "No"])
        st.markdown("---")

        cats = sorted([c for c in df['categoria'].unique() if c and c != 'N/A'])
        sel_cat = st.multiselect("Categoria HC", cats, default=[], placeholder="Todas")
        contratos = sorted([c for c in df['tipo_contrato'].unique() if c and c != 'N/A'])
        sel_contrato = st.multiselect("Tipo Contrato", contratos, default=[], placeholder="Todos")
        statuses = sorted([c for c in df['status_hr'].unique() if c and c != 'N/A'])
        sel_status = st.multiselect("Status HC", statuses, default=[], placeholder="Todos")
        bpos = sorted([c for c in df['bpo_name'].unique() if c and c != 'N/A'])
        sel_bpo = st.multiselect("BPO", bpos, default=[], placeholder="Todos")

    # ── Apply filters ──
    mask = pd.Series(True, index=df.index)
    if tipo_hc and len(tipo_hc) < 2:
        mask &= df['spx'] if "FTE (SPX)" in tipo_hc else df['bpo']
    if sel_loc_type:
        mask &= df['loc_type'].isin(sel_loc_type)
    if sel_locs:
        mask &= df['loc_sot'].isin(sel_locs)
    if in_hr_filter != "All":
        mask &= df['in_hr'] == (in_hr_filter == "Yes")
    if in_att_filter != "All":
        mask &= df['in_att'] == (in_att_filter == "Yes")
    if in_perf_filter != "All":
        mask &= df['in_perf'] == (in_perf_filter == "Yes")
    if sel_cat:
        mask &= df['categoria'].isin(sel_cat)
    if sel_contrato:
        mask &= df['tipo_contrato'].isin(sel_contrato)
    if sel_status:
        mask &= df['status_hr'].isin(sel_status)
    if sel_bpo:
        mask &= df['bpo_name'].isin(sel_bpo)

    fdf = df[mask].copy()

    # ── Header ──
    st.markdown("# HC Reconciliation Dashboard")
    st.caption(f"CrossCheck: {len(fdf):,} registros (de {len(df):,} total)")

    # ── Main Navigation (pill tabs) ──
    tab_graficos, tab_recon, tab_growth, tab_perf, tab_consulta, tab_guia, tab_glossario = st.tabs([
        "📊 Gráficos", "📋 Recon", "📈 HC Growth", "🏢 Performance Hubs",
        "🔍 Consulta Colaborador(a)", "📖 Guia de Uso", "📚 Glossário"])

    with tab_graficos:
        page_graficos(fdf)

    with tab_recon:
        page_recon(fdf, raw_summary)

    with tab_growth:
        page_hc_growth(abs_growth, var_growth)

    with tab_perf:
        page_performance(perf_data)

    with tab_consulta:
        page_consulta(df)

    with tab_guia:
        page_guia()

    with tab_glossario:
        page_glossario()

    st.markdown("")
    st.caption("v4.3 · Dados cached 5 min · Fonte: CrossCheck + Ind.Summary + HR + HC Growth")


if __name__ == '__main__':
    main()
