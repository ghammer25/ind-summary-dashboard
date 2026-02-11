import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
import os
import pickle

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
    .db-box .field {{ font-size: 12px; margin: 4px 0; }}
    .db-box .field-label {{ color: #888; font-size: 11px; }}
    .match {{ color: {CYAN}; }}
    .mismatch {{ color: {RED}; font-weight: 600; }}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════════════════════════
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
]
CREDENTIALS_FILE = r"c:\Users\SPXBR26731\OneDrive - Seagroup\Área de Trabalho\codes\credentials.json"
TOKEN_FILE = r"c:\Users\SPXBR26731\OneDrive - Seagroup\Área de Trabalho\codes\token_write.pickle"


def get_gc():
    if "gcp_service_account" in st.secrets:
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


def eq_cls(person, field):
    return "match" if person.get(field, False) else "mismatch"


def render_employee_card(person):
    tipo = "FTE" if person.get('spx', False) else "BPO"
    tipo_bg = BLUE if tipo == "FTE" else ORANGE
    active = "Ativo" if person.get('active', False) else "Inativo"
    active_bg = CYAN if active == "Ativo" else RED
    in_hr = person.get('in_hr', False)
    in_att = person.get('in_att', False)
    in_perf = person.get('in_perf', False)

    html = f'''
    <div class="emp-card">
        <h3>{person.get('sot_name', 'N/A')}</h3>
        <div style="margin-bottom:10px;">
            <span class="emp-badge" style="background:{tipo_bg}">{tipo}</span>
            <span class="emp-badge" style="background:{active_bg}">{active}</span>
            <span style="font-size:13px;color:#666;margin-left:10px;">
                Staff ID: <b>{person.get('staff_id', 'N/A')}</b>
            </span>
        </div>
        <div style="font-size:13px;margin-bottom:8px;">
            {"✅" if in_hr else "❌"} HR &nbsp;&nbsp;
            {"✅" if in_att else "❌"} Attendance &nbsp;&nbsp;
            {"✅" if in_perf else "❌"} Performance
        </div>
        <div style="font-size:12px;color:#888;margin-bottom:6px;">
            Location SoT: <b>{person.get('loc_sot', '-')}</b> ·
            Site Type: <b>{person.get('loc_type', '-')}</b> ·
            Cargo SoT: <b>{person.get('sot_func', '-')}</b>
        </div>
    '''
    bpo_name = person.get('bpo_name', 'N/A')
    cat = person.get('categoria', 'N/A')
    contrato = person.get('tipo_contrato', 'N/A')
    status = person.get('status_hr', 'N/A')
    if any(v not in ('N/A', '', '-') for v in [bpo_name, cat, contrato, status]):
        html += f'''
        <div style="font-size:12px;color:#888;margin-bottom:12px;">
            BPO: <b>{bpo_name}</b> ·
            Categoria: <b>{cat}</b> ·
            Contrato: <b>{contrato}</b> ·
            Status HR: <b>{status}</b>
        </div>
        '''

    html += '<div class="db-grid">'
    # HR box
    html += f'''
    <div class="db-box">
        <h5>{"✅" if in_hr else "❌"} HR</h5>
        <div class="field"><span class="field-label">Nome:</span>
            <span class="{eq_cls(person, 'name_eq_hr')}">{person.get('name_hr', '-')}</span></div>
        <div class="field"><span class="field-label">Cargo:</span>
            <span class="{eq_cls(person, 'func_eq_hr')}">{person.get('func_hr', '-')}</span></div>
        <div class="field"><span class="field-label">Sort Code:</span>
            <span class="{eq_cls(person, 'loc_eq_hr')}">{person.get('sc_hr', '-')}</span></div>
        <div class="field"><span class="field-label">CNPJ:</span> {person.get('cnpj_hr', '-')}</div>
        <div class="field"><span class="field-label">Subteam:</span> {person.get('subteam_hr', '-')}</div>
    </div>
    '''
    # Attendance box
    html += f'''
    <div class="db-box">
        <h5>{"✅" if in_att else "❌"} Attendance</h5>
        <div class="field"><span class="field-label">Nome:</span>
            <span class="{eq_cls(person, 'name_eq_att')}">{person.get('name_att', '-')}</span></div>
        <div class="field"><span class="field-label">Cargo:</span>
            <span class="{eq_cls(person, 'func_eq_att')}">{person.get('func_att', '-')}</span></div>
        <div class="field"><span class="field-label">Sort Code:</span>
            <span class="{eq_cls(person, 'loc_eq_att')}">{person.get('sc_att', '-')}</span></div>
        <div class="field"><span class="field-label">CNPJ:</span> {person.get('cnpj_att', '-')}</div>
        <div class="field"><span class="field-label">Subteam:</span> {person.get('subteam_att', '-')}</div>
    </div>
    '''
    # Performance box
    html += f'''
    <div class="db-box">
        <h5>{"✅" if in_perf else "❌"} Performance</h5>
        <div class="field"><span class="field-label">Nome:</span>
            <span class="{eq_cls(person, 'name_eq_perf')}">{person.get('name_perf', '-')}</span></div>
        <div class="field"><span class="field-label">Cargo:</span>
            <span class="{eq_cls(person, 'func_eq_perf')}">{person.get('func_perf', '-')}</span></div>
        <div class="field"><span class="field-label">Sort Code:</span>
            <span class="{eq_cls(person, 'loc_eq_perf')}">{person.get('sc_perf', '-')}</span></div>
        <div class="field"><span class="field-label">CNPJ:</span> {person.get('cnpj_perf', '-')}</div>
    </div>
    '''
    html += '</div>'

    if person.get('moving', False) or person.get('new_hub', False):
        html += f'''
        <div style="background:#fff3cd;border-radius:6px;padding:8px 12px;margin-top:8px;
                     font-size:12px;border:1px solid #ffc107;">
            ⚠️ <b>Movimentação:</b>
            Same Hub: {"Sim" if person.get('same_hub', False) else "Não"} ·
            Moving: {"Sim" if person.get('moving', False) else "Não"} ·
            New Hub: {"Sim" if person.get('new_hub', False) else "Não"}
        </div>
        '''

    html += '</div>'
    return html


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

    # KPI row 1
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

    # KPI row 2
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

    # Charts row 1
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("##### HC por Database")
        fig = go.Figure(go.Bar(
            x=['HR', 'Attendance', 'Performance'],
            y=[n_in_hr, n_in_att, n_in_perf],
            marker_color=[NAVY, CYAN, ORANGE],
            text=[fmt(n_in_hr), fmt(n_in_att), fmt(n_in_perf)],
            textposition='outside'))
        fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=30),
                          yaxis_title="", xaxis_title="", font=dict(size=11))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("##### HC por Site Type")
        by_type = fdf['loc_type'].value_counts().reset_index()
        by_type.columns = ['Site Type', 'Count']
        by_type = by_type[by_type['Site Type'].str.strip().ne('') & by_type['Site Type'].ne('-')]
        palette = [NAVY, BLUE, LBLUE, CYAN, ORANGE, RED, YELLOW, GOLD, GRAY]
        fig2 = px.bar(by_type, x='Site Type', y='Count', text_auto=True,
                      color='Site Type', color_discrete_sequence=palette)
        fig2.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=30),
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

    # Charts row 2 - Divergences
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
        fig_d.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=30),
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

    # SoT Rules
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

    # ── Sub-tabs: Todos | Desligamentos | Admissão | Mudanças ──
    sub_todos, sub_deslig, sub_admis, sub_mud = st.tabs(
        ["Todos", "Desligamentos", "Admissão", "Mudanças"])

    def render_recon_table(sub_df, key_suffix):
        st.caption(f"{len(sub_df):,} registros")

        qs1, qs2, qs3, qs4 = st.columns(4)
        with qs1:
            n_not_all = int((~sub_df['all_dbs']).sum())
            st.metric("Isn't in all DBs", fmt(n_not_all))
        with qs2:
            adb = sub_df[sub_df['all_dbs']]
            st.metric("Sort Code Incorreto", fmt(int((~adb['loc_eq_total']).sum()) if len(adb) > 0 else 0))
        with qs3:
            st.metric("Cargo Incorreto", fmt(int((~adb['func_eq_total']).sum()) if len(adb) > 0 else 0))
        with qs4:
            st.metric("Nome Incorreto", fmt(int((~adb['name_eq_total']).sum()) if len(adb) > 0 else 0))

        detail_filter = st.selectbox("Filtro rápido:", [
            "Todos", "Isn't in all DBs", "Sort Code Incorreto",
            "Cargo Incorreto", "Nome Incorreto",
        ], key=f"detail_{key_suffix}")

        show_df = sub_df.copy()
        if detail_filter == "Isn't in all DBs":
            show_df = show_df[~show_df['all_dbs']]
        elif detail_filter == "Sort Code Incorreto":
            show_df = show_df[show_df['all_dbs'] & ~show_df['loc_eq_total']]
        elif detail_filter == "Cargo Incorreto":
            show_df = show_df[show_df['all_dbs'] & ~show_df['func_eq_total']]
        elif detail_filter == "Nome Incorreto":
            show_df = show_df[show_df['all_dbs'] & ~show_df['name_eq_total']]

        show_cols = ['staff_id', 'sot_name', 'spx', 'bpo', 'active',
                     'in_hr', 'in_att', 'in_perf', 'all_dbs',
                     'loc_sot', 'loc_type', 'loc_eq_total',
                     'sot_func', 'func_eq_total',
                     'same_hub', 'moving', 'new_hub']
        if 'bpo_name' in show_df.columns:
            show_cols += ['bpo_name', 'categoria', 'tipo_contrato', 'status_hr']

        display_df = show_df[[c for c in show_cols if c in show_df.columns]].copy()
        rename = {
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
        display_df = display_df.rename(columns=rename)
        st.dataframe(display_df, use_container_width=True, height=450, hide_index=True)

        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            f"📥 Exportar CSV ({len(display_df):,} linhas)",
            csv, f"recon_{key_suffix}.csv", "text/csv",
            use_container_width=True, key=f"csv_{key_suffix}")

    with sub_todos:
        render_recon_table(fdf, "todos")

    with sub_deslig:
        render_recon_table(fdf[~fdf['active']], "deslig")

    with sub_admis:
        render_recon_table(fdf[fdf['in_hr'] & ~fdf['all_dbs'] & fdf['active']], "admis")

    with sub_mud:
        render_recon_table(fdf[fdf['moving']], "mud")

    # ── Tabela Original Ind. Summary ──
    st.markdown("---")
    with st.expander("📋 Tabela Original - Ind. Summary"):
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

    if len(results) > 50:
        st.warning("Muitos resultados. Mostrando os primeiros 50. Refine a busca.")
        results = results.head(50)

    for _, person in results.iterrows():
        st.markdown(render_employee_card(person), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════
def main():
    df_cc = load_crosscheck()
    df_hr = load_hr()
    raw_summary = load_ind_summary()

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
    tab_graficos, tab_recon, tab_consulta = st.tabs([
        "📊 Gráficos", "📋 Recon", "🔍 Consulta Colaborador(a)"])

    with tab_graficos:
        page_graficos(fdf)

    with tab_recon:
        page_recon(fdf, raw_summary)

    with tab_consulta:
        page_consulta(df)

    st.markdown("")
    st.caption("v3.0 · Dados cached 5 min · Fonte: CrossCheck + Ind.Summary + HR")


if __name__ == '__main__':
    main()
