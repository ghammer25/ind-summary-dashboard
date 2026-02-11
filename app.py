import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
import os
import pickle

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ind. Summary - HC Reconciliation",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }

    .kpi-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5986 100%);
        border-radius: 12px; padding: 20px; text-align: center;
        color: white; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 10px;
    }
    .kpi-card h3 { margin: 0; font-size: 14px; opacity: 0.85; font-weight: 400; }
    .kpi-card h1 { margin: 5px 0 0 0; font-size: 28px; font-weight: 700; }
    .kpi-card-green { background: linear-gradient(135deg, #1a5c3a 0%, #2d8659 100%); }
    .kpi-card-red   { background: linear-gradient(135deg, #8b1a1a 0%, #c0392b 100%); }
    .kpi-card-orange { background: linear-gradient(135deg, #7d5a00 0%, #b8860b 100%); }

    .summary-table {
        width: 100%; border-collapse: collapse;
        font-size: 13px; font-family: 'Segoe UI', sans-serif;
    }
    .summary-table th {
        background: #1e3a5f; color: white; padding: 8px 10px;
        text-align: center; font-weight: 600; border: 1px solid #16304d;
        position: sticky; top: 0; z-index: 10;
    }
    .summary-table th.group-header {
        background: #2d5986; font-size: 14px; letter-spacing: 0.5px;
    }
    .summary-table td {
        padding: 6px 10px; border: 1px solid #e0e4e8; text-align: right;
    }
    .summary-table td:first-child {
        text-align: left; font-weight: 500; white-space: nowrap;
    }
    .summary-table tr:nth-child(even) { background: #f8f9fb; }
    .summary-table tr:hover { background: #e8edf3; }
    .summary-table tr.level-0 { font-weight: 700; background: #e6ecf3; }
    .summary-table tr.level-1 { font-weight: 600; }
    .summary-table tr.level-3 { font-size: 12px; color: #555; }
    .summary-table tr.level-4 { font-size: 11px; color: #777; }
    .summary-table tr.separator td { background: #d4dbe5; height: 3px; padding: 0; }

    .val-zero   { color: #28a745; font-weight: 600; }
    .val-high   { color: #dc3545; font-weight: 600; }
    .val-medium { color: #fd7e14; }
    .val-na     { color: #adb5bd; font-style: italic; }

    .sot-note {
        background: #f0f2f6; border-left: 3px solid #1e3a5f;
        padding: 10px 15px; margin: 5px 0; font-size: 13px;
        border-radius: 0 8px 8px 0;
    }

    div[data-testid="stExpander"] details {
        border: 1px solid #e0e4e8; border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ─── Auth & Data Loading ─────────────────────────────────────────────────────
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]
CREDENTIALS_FILE = r"c:\Users\SPXBR26731\OneDrive - Seagroup\Área de Trabalho\codes\credentials.json"
TOKEN_FILE = r"c:\Users\SPXBR26731\OneDrive - Seagroup\Área de Trabalho\codes\token_write.pickle"


def get_gspread_client():
    """Authenticate with Google Sheets.
    Cloud (Streamlit Cloud): service account via st.secrets
    Local: OAuth2 via credentials.json + token_write.pickle
    """
    # ── Streamlit Cloud: service account from secrets ──
    if "gcp_service_account" in st.secrets:
        from google.oauth2.service_account import Credentials as SACredentials
        creds = SACredentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=SCOPES,
        )
        return gspread.authorize(creds)

    # ── Local: OAuth2 com token pickle ──
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


@st.cache_data(ttl=300)
def load_data():
    """Load Ind. Summary data from Google Sheets (cached 5 min)."""
    gc = get_gspread_client()
    SPREADSHEET_ID = "1f3RtvA7F2SCdJ5XJkhXh0W8JOb6qnuyDj1zzhB1BanY"
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    for ws in spreadsheet.worksheets():
        if ws.id == 2047376970:
            return ws.get_all_values()
    return []


# ─── Helpers ──────────────────────────────────────────────────────────────────
def parse_number(val):
    if not val or val in ('', 'N/A'):
        return None
    try:
        return int(val.replace(',', '').replace('.', ''))
    except (ValueError, AttributeError):
        return None


def fmt(val):
    return "N/A" if val is None else f"{val:,}"


def indent_level(label):
    spaces = len(label) - len(label.lstrip())
    if spaces == 0:   return 0
    if spaces <= 3:    return 1
    if spaces <= 6:    return 2
    if spaces <= 9:    return 3
    if spaces <= 12:   return 4
    if spaces <= 15:   return 5
    if spaces <= 18:   return 6
    return 7


def css_class(val_str, parsed):
    if val_str in ('N/A', ''):  return 'val-na'
    if parsed == 0:             return 'val-zero'
    if parsed and parsed > 500: return 'val-high'
    if parsed and parsed > 100: return 'val-medium'
    return ''


# ─── Dashboard ────────────────────────────────────────────────────────────────
def main():
    raw = load_data()
    if not raw:
        st.error("Erro ao carregar dados. Verifique as credenciais / permissões.")
        return

    # ── Title ──
    st.markdown("# 📊 HC Reconciliation — Ind. Summary")
    st.markdown("*Reconciliação de Headcount entre databases HR, Attendance e Performance*")
    st.divider()

    # ── Parse key rows ──
    r_hcs      = raw[3]   # # of HCs
    r_inactive = raw[4]
    r_active   = raw[7]
    r_ftes     = raw[8]
    r_bpos     = raw[30]

    total_hr     = parse_number(r_hcs[2])
    total_attend = parse_number(r_hcs[3])
    total_perf   = parse_number(r_hcs[4])
    total_total  = parse_number(r_hcs[5])
    active_total   = parse_number(r_active[5])
    inactive_total = parse_number(r_inactive[5])
    ftes_total     = parse_number(r_ftes[5])
    bpos_total     = parse_number(r_bpos[5])

    # ── KPI cards ──
    cols = st.columns(5)
    cards = [
        ("Total HCs",       total_total,   ""),
        ("Active",          active_total,  "kpi-card-green"),
        ("Inactive",        inactive_total,"kpi-card-red"),
        ("FTEs (Active)",   ftes_total,    ""),
        ("BPOs (Active)",   bpos_total,    "kpi-card-orange"),
    ]
    for col, (title, val, extra) in zip(cols, cards):
        col.markdown(
            f'<div class="kpi-card {extra}"><h3>{title}</h3><h1>{fmt(val)}</h1></div>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── Charts row ──
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### HC por Database")
        fig = px.bar(
            pd.DataFrame({
                'Database': ['HR', 'Attendance', 'Performance', 'Total (Union)'],
                'HCs': [total_hr or 0, total_attend or 0, total_perf or 0, total_total or 0],
            }),
            x='Database', y='HCs', color='Database',
            color_discrete_sequence=['#1e3a5f', '#2d8659', '#b8860b', '#6c757d'],
            text_auto=True,
        )
        fig.update_layout(showlegend=False, height=320,
                          margin=dict(l=20, r=20, t=30, b=40),
                          yaxis_title="", xaxis_title="")
        fig.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("### HC por Operação (Total)")
        ops = ['FMH', 'SOC', 'HUB', 'Almox', 'CB', 'RTS']
        ops_cols = [10, 15, 20, 25, 30, 35]
        fig2 = px.bar(
            pd.DataFrame({'Operação': ops,
                           'HCs': [parse_number(r_hcs[c]) or 0 for c in ops_cols]}),
            x='Operação', y='HCs', color='Operação',
            color_discrete_sequence=['#1e3a5f','#2d5986','#4a90d9','#7ab8e0','#a0c4e8','#c8ddf0'],
            text_auto=True,
        )
        fig2.update_layout(showlegend=False, height=320,
                           margin=dict(l=20, r=20, t=30, b=40),
                           yaxis_title="", xaxis_title="")
        fig2.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ══════════════════════════════════════════════════════════════════════
    #  DETAILED TABLE
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("### Tabela Detalhada de Reconciliação")

    GROUPS = [
        ("All",   [2, 3, 4, 5]),
        ("FMH",   [7, 8, 9, 10]),
        ("SOC",   [12, 13, 14, 15]),
        ("HUB",   [17, 18, 19, 20]),
        ("Almox", [22, 23, 24, 25]),
        ("CB",    [27, 28, 29, 30]),
        ("RTS",   [32, 33, 34, 35]),
    ]

    sel = st.multiselect("Filtrar Operações:", [g[0] for g in GROUPS], default=["All"])
    if not sel:
        sel = ["All"]
    groups = [g for g in GROUPS if g[0] in sel]

    DATA_ROWS = list(range(3, 51))

    html = ('<div style="overflow-x:auto;max-height:700px;overflow-y:auto;'
            'border-radius:8px;border:1px solid #e0e4e8;">'
            '<table class="summary-table">')

    # header row 1
    html += '<tr><th rowspan="2" style="min-width:280px;text-align:left;">KPI</th>'
    for name, _ in groups:
        html += f'<th colspan="4" class="group-header">{name}</th>'
    html += '<th rowspan="2" style="min-width:200px;max-width:300px;text-align:left;">Comments</th></tr>'

    # header row 2
    html += '<tr>'
    for _ in groups:
        html += '<th>HR</th><th>Attend.</th><th>Perf.</th><th>Total</th>'
    html += '</tr>'

    for ri in DATA_ROWS:
        row = raw[ri]
        label = row[1] if len(row) > 1 else ''
        if not label.strip():
            html += '<tr class="separator"><td colspan="100"></td></tr>'
            continue

        lvl = indent_level(label)
        px_indent = lvl * 18
        lbl = f'<span style="padding-left:{px_indent}px">{label.strip()}</span>'

        html += f'<tr class="level-{min(lvl,4)}"><td>{lbl}</td>'
        for _, cidxs in groups:
            for ci in cidxs:
                v = row[ci] if ci < len(row) else ''
                p = parse_number(v)
                html += f'<td class="{css_class(v,p)}">{v}</td>'

        comment = row[37] if len(row) > 37 else ''
        if comment:
            short = comment[:80] + ('...' if len(comment) > 80 else '')
            html += (f'<td style="text-align:left;font-size:11px;color:#666" '
                     f'title="{comment}">{short}</td>')
        else:
            html += '<td></td>'
        html += '</tr>'

    html += '</table></div>'
    st.markdown(html, unsafe_allow_html=True)

    st.divider()

    # ══════════════════════════════════════════════════════════════════════
    #  DIVERGENCE ANALYSIS
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("### Análise de Divergências")

    r_fte_miss  = raw[9]
    r_fte_sc    = raw[20]
    r_fte_jt    = raw[26]
    r_fte_nm    = raw[28]
    r_bpo_miss  = raw[31]
    r_bpo_sc    = raw[42]
    r_bpo_jt    = raw[48]
    r_bpo_nm    = raw[50]

    c1, c2 = st.columns(2)

    def div_bar(title, rows_data, container):
        with container:
            st.markdown(f"#### {title}")
            df = pd.DataFrame({
                'Tipo': ["Isn't in DB", 'Incorrect Sort Code',
                         'Incorrect Job Title', 'Incorrect Name'],
                'Total': [parse_number(r[5]) or 0 for r in rows_data],
            })
            fig = px.bar(df, x='Tipo', y='Total', color='Tipo',
                         color_discrete_sequence=['#dc3545','#fd7e14','#ffc107','#17a2b8'],
                         text_auto=True)
            fig.update_layout(showlegend=False, height=300,
                              margin=dict(l=20,r=20,t=30,b=40),
                              yaxis_title="", xaxis_title="")
            fig.update_traces(texttemplate='%{y:,.0f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

    div_bar("FTEs — Divergências", [r_fte_miss, r_fte_sc, r_fte_jt, r_fte_nm], c1)
    div_bar("BPOs — Divergências", [r_bpo_miss, r_bpo_sc, r_bpo_jt, r_bpo_nm], c2)

    # ── Stacked: "Isn't in DB" by operation ──
    st.markdown("#### Isn't in DB — por Operação")
    ops_names = ['FMH', 'SOC', 'HUB', 'Almox', 'CB', 'RTS']
    t_cols = [10, 15, 20, 25, 30, 35]
    fig_s = go.Figure()
    fig_s.add_trace(go.Bar(name='FTEs', x=ops_names,
                           y=[parse_number(r_fte_miss[c]) or 0 for c in t_cols],
                           marker_color='#2d5986', text=[parse_number(r_fte_miss[c]) or 0 for c in t_cols],
                           textposition='inside'))
    fig_s.add_trace(go.Bar(name='BPOs', x=ops_names,
                           y=[parse_number(r_bpo_miss[c]) or 0 for c in t_cols],
                           marker_color='#b8860b', text=[parse_number(r_bpo_miss[c]) or 0 for c in t_cols],
                           textposition='inside'))
    fig_s.update_layout(barmode='stack', height=350,
                        margin=dict(l=20,r=20,t=30,b=40),
                        yaxis_title="HCs", xaxis_title="",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                    xanchor="center", x=0.5))
    st.plotly_chart(fig_s, use_container_width=True)

    # ── Sort Code: Correct vs Incorrect ──
    st.markdown("#### Sort Code — Correto vs Incorreto")
    r_fte_ok = raw[19]
    r_bpo_ok = raw[41]

    fig_sc = go.Figure()
    correct_vals = [
        (parse_number(r_fte_ok[c]) or 0) + (parse_number(r_bpo_ok[c]) or 0)
        for c in t_cols
    ]
    incorrect_vals = [
        (parse_number(r_fte_sc[c]) or 0) + (parse_number(r_bpo_sc[c]) or 0)
        for c in t_cols
    ]
    fig_sc.add_trace(go.Bar(name='Correct', x=ops_names, y=correct_vals,
                            marker_color='#28a745'))
    fig_sc.add_trace(go.Bar(name='Incorrect', x=ops_names, y=incorrect_vals,
                            marker_color='#dc3545'))
    fig_sc.update_layout(barmode='group', height=350,
                         margin=dict(l=20,r=20,t=30,b=40),
                         yaxis_title="HCs", xaxis_title="",
                         legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                     xanchor="center", x=0.5))
    st.plotly_chart(fig_sc, use_container_width=True)

    st.divider()

    # ══════════════════════════════════════════════════════════════════════
    #  FOR REPORT SUMMARY
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("### Resumo para Report")

    report_items = [
        (9,  "Não contém nas bases — FTE"),
        (19, "OK — FTE (Sort Code correto)"),
        (20, "Location divergente — FTE"),
        (31, "Não contém nas bases — BPO"),
        (41, "OK — BPO (Sort Code correto)"),
        (42, "Location divergente — BPO"),
    ]
    rpt_ops  = ['HUB', 'SOC', 'Almox', 'CB', 'RTS', 'Total']
    rpt_cols = [39, 40, 41, 42, 43, 44]

    h = ('<div style="overflow-x:auto;border-radius:8px;border:1px solid #e0e4e8;">'
         '<table class="summary-table"><tr><th style="text-align:left">Categoria</th>')
    for op in rpt_ops:
        h += f'<th>{op}</th>'
    h += '</tr>'
    for ri, label in report_items:
        row = raw[ri]
        h += f'<tr><td>{label}</td>'
        for ci in rpt_cols:
            v = row[ci] if ci < len(row) else ''
            p = parse_number(v)
            h += f'<td class="{css_class(v,p)}">{v}</td>'
        h += '</tr>'
    h += '</table></div>'
    st.markdown(h, unsafe_allow_html=True)

    st.divider()

    # ══════════════════════════════════════════════════════════════════════
    #  SOT RULES
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("### Source of Truth (SoT)")

    c_sc, c_jt = st.columns(2)
    with c_sc:
        st.markdown("**Sort Code:**")
        for sc, rule in [
            ("FTE & Same CNPJ",             "Performance > Attendance > HR"),
            ("FTE, Diff CNPJ & Moving",     "Performance > Attendance > HR"),
            ("FTE, Diff CNPJ & Non-Moving",  "Attendance > Performance > HR"),
            ("BPO & Same CNPJ",             "Performance > HR"),
            ("BPO, Diff CNPJ & Moving",     "Performance > HR"),
            ("BPO, Diff CNPJ & Non-Moving",  "HR > Performance"),
        ]:
            st.markdown(f'<div class="sot-note"><b>{sc}:</b> {rule}</div>',
                        unsafe_allow_html=True)

    with c_jt:
        st.markdown("**Job Title & Name:**")
        for sc, rule in [
            ("FTE", "Attendance > HR > Performance"),
            ("BPO", "HR > Performance"),
        ]:
            st.markdown(f'<div class="sot-note"><b>{sc}:</b> {rule}</div>',
                        unsafe_allow_html=True)

    # ── Suggestions ──
    with st.expander("📋 Sugestões de Ação"):
        for ri in range(3, 51):
            row = raw[ri]
            lbl = row[1].strip() if len(row) > 1 else ''
            sug = row[63] if len(row) > 63 else ''
            if lbl and sug and sug.strip():
                st.markdown(f"**{lbl}:** {sug}")
                st.markdown("---")

    st.markdown("")
    st.caption("Dados atualizados a cada 5 min · Fonte: Google Sheets — Ind. Summary · v1.0")


if __name__ == '__main__':
    main()
