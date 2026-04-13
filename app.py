"""
📈 Dashboard IMA-B 5 × CDI — Rentabilidade
Light theme · Metodologia ANBIMA/VNA · Focus/BCB · ETTJ pyettj/B3
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io, csv
from datetime import date, timedelta

from utils import (
    is_business_day, count_business_days, business_days_list, date_plus_du,
    _get_vna_na_data, calc_ipca_periodo, build_ipca_table, build_ipca_table_from_focus,
    imab5_retorno_total,
    cdi_retorno_com_copom, cdi_retorno_simples,
    build_copom_schedule_from_focus, build_copom_schedule_manual, COPOM_CALENDARIO,
    fetch_focus_all,
    get_ettj_b3, parse_ettj_for_curve, last_business_day, last_business_day_1y_ago,
    fmt_pct, fmt_brl, fmt_brl_short,
)

# ──────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG + LIGHT THEME CSS
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="IMA-B 5 × CDI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ── Base light ── */
html, body, .stApp { background:#f5f7fa !important; color:#1e293b !important; }
[data-testid="stSidebar"] { background:#ffffff !important; border-right:1px solid #e2e8f0; }
[data-testid="stSidebar"] * { color:#1e293b !important; }

/* ── Métricas ── */
div[data-testid="metric-container"] {
    background:#ffffff;
    border:1px solid #e2e8f0;
    border-radius:10px;
    padding:14px 18px;
    box-shadow:0 1px 6px rgba(0,0,0,.06);
}
div[data-testid="metric-container"] label {
    color:#64748b !important; font-size:.75rem !important;
    text-transform:uppercase; letter-spacing:.07em;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color:#0f172a !important; font-size:1.45rem !important; font-weight:700;
}
div[data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size:.8rem !important; }

/* ── Section header ── */
.sec {
    font-size:.82rem; font-weight:700; color:#0369a1;
    text-transform:uppercase; letter-spacing:.1em;
    padding:5px 0 3px; border-bottom:2px solid #bae6fd;
    margin-bottom:12px;
}

/* ── Info box ── */
.ibox {
    background:#eff6ff; border-left:3px solid #3b82f6;
    border-radius:0 6px 6px 0; padding:9px 13px;
    font-size:.83rem; color:#1e40af; margin:6px 0 10px; line-height:1.55;
}
.ibox b { color:#1d4ed8; }

/* ── Success/warning boxes ── */
.sbox { background:#f0fdf4; border-left:3px solid #22c55e; border-radius:0 6px 6px 0;
        padding:8px 13px; font-size:.82rem; color:#166534; margin:4px 0 8px; }
.wbox { background:#fefce8; border-left:3px solid #eab308; border-radius:0 6px 6px 0;
        padding:8px 13px; font-size:.82rem; color:#854d0e; margin:4px 0 8px; }

/* ── Badges ── */
.b-green  { background:#dcfce7; color:#166534; padding:2px 9px; border-radius:14px; font-size:.75rem; font-weight:700; border:1px solid #86efac; }
.b-yellow { background:#fef9c3; color:#854d0e; padding:2px 9px; border-radius:14px; font-size:.75rem; font-weight:700; border:1px solid #fde047; }
.b-red    { background:#fee2e2; color:#991b1b; padding:2px 9px; border-radius:14px; font-size:.75rem; font-weight:700; border:1px solid #fca5a5; }

/* ── Winner ── */
.winner { color:#b45309; font-weight:700; }

/* ── Tables ── */
.stDataFrame { border:1px solid #e2e8f0 !important; border-radius:8px; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background:#ffffff; border-radius:8px; padding:4px; border:1px solid #e2e8f0; }
.stTabs [data-baseweb="tab"] { color:#64748b !important; font-weight:600; }
.stTabs [aria-selected="true"] { color:#0369a1 !important; background:#eff6ff; border-radius:6px; }

/* ── Inputs ── */
.stNumberInput input, .stDateInput input, .stTextArea textarea {
    background:#ffffff !important; border:1px solid #cbd5e1 !important;
    color:#1e293b !important; border-radius:6px;
}
.stSelectbox > div > div { background:#ffffff !important; border:1px solid #cbd5e1 !important; }
.stRadio label { color:#1e293b !important; }

h1,h2,h3,h4,h5 { color:#0f172a !important; }
hr { border-color:#e2e8f0; }
p, span, label, div { color:#1e293b; }

/* Expander */
.streamlit-expanderHeader { color:#0369a1 !important; font-weight:600 !important; }
</style>
""", unsafe_allow_html=True)

# ── PLOTLY template for light theme ──
PLOT_LAYOUT = dict(
    template='plotly_white',
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='#fafafa',
    font=dict(color='#1e293b', family='Inter, sans-serif', size=12),
    legend=dict(bgcolor='rgba(255,255,255,.9)', bordercolor='#e2e8f0',
                borderwidth=1, orientation='h', y=1.08, x=1, xanchor='right'),
    margin=dict(t=55, b=30, l=10, r=10),
)

CORES = {'IMA-B 5': '#0ea5e9', 'IMA-B 5+': '#8b5cf6', 'CDI': '#f59e0b',
         'IPCA': '#ef4444', 'Pre': '#10b981'}

# ──────────────────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="padding:16px 0 4px; border-bottom:2px solid #e2e8f0; margin-bottom:18px;">
  <span style="font-size:1.9rem; font-weight:800; color:#0f172a;">
    📈 IMA-B 5 × CDI
  </span>
  <span style="font-size:1rem; color:#64748b; margin-left:14px; font-weight:400;">
    Dashboard de Rentabilidade — Metodologia ANBIMA · Focus/BCB
  </span>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# FOCUS CACHE
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_focus():
    return fetch_focus_all()

@st.cache_data(ttl=86400, show_spinner=False)
def load_ettj_cached(data_str: str, curva: str):
    from utils import get_ettj_b3
    d = date.fromisoformat(data_str)
    return get_ettj_b3(d, curva)

if 'focus' not in st.session_state:
    with st.spinner("Buscando dados Focus/BCB..."):
        st.session_state['focus'] = load_focus()
focus = st.session_state.get('focus', {})

# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Parâmetros")
    if st.button("🔄 Atualizar Focus/BCB", use_container_width=True, type="primary"):
        load_focus.clear()
        st.session_state['focus'] = load_focus()
        focus = st.session_state['focus']
        st.success("Dados atualizados!")
    st.markdown("---")

    st.markdown("### 📊 IMA-B 5")
    c1s, c2s = st.columns(2)
    yield_b5 = c1s.number_input("Yield (% a.a.)", value=7.7519, step=0.01,
                                  format="%.4f", key="yb5")
    dur_b5   = c2s.number_input("Duration (d.u.)", value=496, step=1)

    st.markdown("### 📊 IMA-B 5+")
    c3s, c4s = st.columns(2)
    yield_b5p = c3s.number_input("Yield (% a.a.)", value=7.2157, step=0.01,
                                   format="%.4f", key="yb5p")
    dur_b5p   = c4s.number_input("Duration (d.u.)", value=2437, step=1)

    st.markdown("### 📅 Janela de Simulação")
    d_ini = st.date_input("Início", value=date(2026, 4, 10))
    d_fim = st.date_input("Fim",    value=date_plus_du(date(2026, 4, 10), 181))

    # Valida janela máx 2 anos (504 du)
    du_total = count_business_days(d_ini, d_fim)
    if du_total > 504:
        st.warning("⚠️ Janela máxima: ~2 anos (504 d.u.)")
    st.info(f"📆 **{du_total}** dias úteis selecionados")

    st.markdown("### 💰 Selic atual (% a.a.)")
    selic_ini = st.number_input("Selic", value=14.75, step=0.25, format="%.2f")

    st.markdown("---")
    st.markdown("### 📐 VNA Base")
    vna_base     = st.number_input("VNA (último IPCA divulgado)", value=4673.2559,
                                    format="%.4f", step=0.0001)
    d_fech_vna   = st.date_input("Fechamento do VNA base", value=date(2026, 4, 15),
                                  help="Data de fechamento do último IPCA divulgado (dia 15 do mês seguinte)")
    # VNA do mês anterior para interpolar corretamente
    vna_ant      = st.number_input("VNA mês anterior", value=4632.49,
                                    format="%.4f", step=0.0001,
                                    help="VNA na data de fechamento do mês anterior ao VNA base")
    d_fech_vna_ant = st.date_input("Fechamento VNA anterior", value=date(2026, 3, 16),
                                    help="Data de fechamento do IPCA do mês anterior ao VNA base")


# ──────────────────────────────────────────────────────────────────────────────
# TABS
# ──────────────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Comparativo de Cenários",
    "📅 Projeção Mês a Mês",
    "📉 Curvas de Juros (ETTJ)",
    "💼 Simulação de Alocação",
])


# ════════════════════════════════════════════════════════════════════════════
# HELPERS compartilhados entre tabs
# ════════════════════════════════════════════════════════════════════════════

def ipca_anual_focus(ano=None):
    ano = str(ano or date.today().year)
    for a in focus.get('ipca_anual', []):
        if str(a['ano']) == ano:
            return a.get('mediana') or a.get('media')
    return None

def selic_anual_focus(ano=None):
    ano = str(ano or date.today().year)
    for a in focus.get('selic_anual', []):
        if str(a['ano']) == ano:
            return a.get('mediana') or a.get('media')
    return None


def make_ipca_table_base(extra_meses=None):
    """
    Constrói a tabela de VNA com âncora nos dois últimos meses divulgados
    para garantir interpolação correta no mês corrente.
    extra_meses: lista de (mes_str, var_pct) adicionais
    """
    lista = []
    if extra_meses:
        lista.extend(extra_meses)
    return build_ipca_table(lista, vna_base, d_fech_vna)


def make_ipca_table_completa(extra_meses=None):
    """
    Tabela de VNA com âncora dupla (mês anterior + mês base) para interpolação correta.
    
    IMPORTANTE: filtra automaticamente meses cujo fechamento já está coberto pelo
    vna_base (d_fech_vna). Evita dupla contagem quando Focus retorna meses já divulgados.
    """
    table = [
        {'data_ref': None, 'data_fechamento': d_fech_vna_ant, 'variacao': 0.0, 'vna': vna_ant},
        {'data_ref': None, 'data_fechamento': d_fech_vna,     'variacao': 0.0, 'vna': vna_base},
    ]
    vna = vna_base
    for mes_ano, var_pct in (extra_meses or []):
        try:
            partes = mes_ano.strip().split('/')
            mes, ano = int(partes[0]), int(partes[1])
            # Calcula data de fechamento deste mês
            if mes == 12:
                data_fech = date(ano + 1, 1, 15)
            else:
                data_fech = date(ano, mes + 1, 15)
            while not is_business_day(data_fech):
                data_fech += timedelta(days=1)
            # ── FILTRO CRÍTICO: ignora meses já cobertos pelo VNA base ──
            # Se o fechamento deste mês <= d_fech_vna, já está embutido no vna_base
            if data_fech <= d_fech_vna:
                continue
            vna = vna * (1 + var_pct / 100.0)
            table.append({'data_ref': date(ano, mes, 15),
                           'data_fechamento': data_fech,
                           'variacao': var_pct, 'vna': vna})
        except Exception:
            continue
    return table


def build_meses_futuros(n=30):
    """Gera lista de meses futuros a partir de d_fech_vna."""
    meses, d = [], d_fech_vna
    for _ in range(n):
        m = d.month + 1 if d.month < 12 else 1
        a = d.year if d.month < 12 else d.year + 1
        d = date(a, m, 15)
        meses.append(f"{d.month:02d}/{d.year}")
    return meses


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — COMPARATIVO DE CENÁRIOS
# ════════════════════════════════════════════════════════════════════════════

with tab1:

    # ── Top: dados Focus ──
    ipca_a  = ipca_anual_focus()
    ipca_a2 = ipca_anual_focus(date.today().year + 1)
    selic_a = selic_anual_focus()

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🎯 IPCA Focus " + str(date.today().year),
              f"{ipca_a:.2f}%" if ipca_a else "—")
    m2.metric("🎯 IPCA Focus " + str(date.today().year+1),
              f"{ipca_a2:.2f}%" if ipca_a2 else "—")
    m3.metric("🏦 Selic Focus",
              f"{selic_a:.2f}% a.a." if selic_a else "—")
    m4.metric("📆 Dias úteis",    f"{du_total} d.u.")
    m5.metric("Focus/BCB", "✅ Online" if focus.get('ok') else "⚠️ Offline")

    # ── Tabela Focus IPCA mensal ──
    if focus.get('ipca_mensal'):
        with st.expander("📋 Ver expectativas Focus IPCA mês a mês"):
            rows_f = []
            for item in focus['ipca_mensal']:
                ref = item.get('data_referencia', '')
                if not ref:
                    continue
                # Parse MM/YYYY para ordenação correta
                try:
                    partes = ref.split('/')
                    sort_key = int(partes[1]) * 100 + int(partes[0])
                except Exception:
                    sort_key = 0
                rows_f.append({'_sort': sort_key,
                                'Referência': ref,
                                'Mediana (%)': item.get('mediana'),
                                'Média (%)':   item.get('media'),
                                'Mínimo (%)':  item.get('minimo'),
                                'Máximo (%)':  item.get('maximo')})
            rows_f.sort(key=lambda x: x['_sort'])
            df_focus_show = pd.DataFrame([{k: v for k, v in r.items() if k != '_sort'}
                                           for r in rows_f])
            st.dataframe(df_focus_show.style.format({
                'Mediana (%)': '{:.2f}', 'Média (%)': '{:.2f}',
                'Mínimo (%)': '{:.2f}', 'Máximo (%)': '{:.2f}',
            }, na_rep='—'), use_container_width=True, height=300)

    # ── Tabela Focus COPOM ──
    if focus.get('selic_copom'):
        with st.expander("🏦 Ver expectativas Focus — Selic por reunião COPOM"):
            rows_cop = []
            for item in focus['selic_copom']:
                reuniao = item['reuniao']
                data_cal = next((c['data'] for c in COPOM_CALENDARIO
                                 if c['reuniao'] == reuniao), None)
                rows_cop.append({'Reunião': reuniao,
                                  'Data': data_cal.strftime('%d/%m/%Y') if data_cal else '—',
                                  'Mediana (%)': item.get('mediana'),
                                  'Média (%)':   item.get('media')})
            df_cop_show = pd.DataFrame(rows_cop)
            st.dataframe(df_cop_show.style.format({
                'Mediana (%)': '{:.2f}', 'Média (%)': '{:.2f}',
            }, na_rep='—'), use_container_width=True, height=260)

    st.markdown("---")

    # ── IPCA projetado ──
    st.markdown("<div class='sec'>📌 IPCA Projetado (até 2 anos)</div>", unsafe_allow_html=True)
    modo_ipca = st.radio("Fonte", ["Focus (mediana)", "Manual", "Cenários IPCA"],
                          horizontal=True, key="modo_ipca1")

    meses_futuros = build_meses_futuros(28)

    DEFAULTS_IPCA = {
        "04/2026": 0.573,"05/2026": 0.320,"06/2026": 0.343,"07/2026": 0.173,
        "08/2026": 0.093,"09/2026": 0.437,"10/2026": 0.177,"11/2026": 0.197,
        "12/2026": 0.427,"01/2027": 0.360,"02/2027": 0.280,"03/2027": 0.380,
        "04/2027": 0.350,"05/2027": 0.300,"06/2027": 0.280,"07/2027": 0.150,
        "08/2027": 0.090,"09/2027": 0.420,"10/2027": 0.160,"11/2027": 0.180,
        "12/2027": 0.380,"01/2028": 0.330,"02/2028": 0.270,"03/2028": 0.360,
    }

    ipca_list_main = []
    ipca_table_ot = ipca_table_ne = ipca_table_pe = []

    if modo_ipca == "Focus (mediana)":
        if focus.get('ok') and focus.get('ipca_mensal'):
            # Filtra apenas meses FUTUROS ao d_fech_vna (evita dupla contagem)
            ipca_list_main = []
            for item in focus['ipca_mensal']:
                ref = item.get('data_referencia', '')
                if not ref:
                    continue
                try:
                    partes = ref.split('/')
                    mes, ano = int(partes[0]), int(partes[1])
                    # Data de fechamento desse mês do Focus
                    if mes == 12:
                        fech = date(ano + 1, 1, 15)
                    else:
                        fech = date(ano, mes + 1, 15)
                    # Só inclui se fechamento > d_fech_vna (mês ainda não embutido no VNA base)
                    if fech > d_fech_vna:
                        ipca_list_main.append((ref, float(item.get('mediana') or item.get('media') or 0)))
                except Exception:
                    continue
            st.markdown(f"<div class='sbox'>✅ {len(ipca_list_main)} meses futuros carregados do Focus "
                        f"(a partir de {d_fech_vna:%m/%Y})</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='wbox'>⚠️ Focus indisponível — usando defaults</div>",
                        unsafe_allow_html=True)
            ipca_list_main = [(m, DEFAULTS_IPCA.get(m, 0.30)) for m in meses_futuros[:24]]

    elif modo_ipca == "Manual":
        st.markdown("**Projeção mensal de IPCA (%):**")
        meses_exibir = [m for m in meses_futuros if m in DEFAULTS_IPCA or True][:24]
        cols_m = st.columns(6)
        for i, ms in enumerate(meses_exibir):
            with cols_m[i % 6]:
                v = st.number_input(ms, value=DEFAULTS_IPCA.get(ms, 0.30),
                                    step=0.01, format="%.2f", key=f"im1_{ms}")
                ipca_list_main.append((ms, v))

    else:  # Cenários
        c_ot, c_ne, c_pe = st.columns(3)
        ipca_ot_aa = c_ot.number_input("🟢 Otimista (% a.a.)", value=5.0,  step=0.1)
        ipca_ne_aa = c_ne.number_input("🟡 Neutro (% a.a.)",   value=ipca_a or 6.0, step=0.1)
        ipca_pe_aa = c_pe.number_input("🔴 Pessimista (% a.a.)", value=7.5, step=0.1)

        def aa_to_list(taxa_aa):
            men = ((1 + taxa_aa/100)**(1/12) - 1) * 100
            return [(m, men) for m in meses_futuros[:24]]

        ipca_table_ot = make_ipca_table_completa(aa_to_list(ipca_ot_aa))
        ipca_table_ne = make_ipca_table_completa(aa_to_list(ipca_ne_aa))
        ipca_table_pe = make_ipca_table_completa(aa_to_list(ipca_pe_aa))
        ipca_list_main = aa_to_list(ipca_ne_aa)

    ipca_table_main = make_ipca_table_completa(ipca_list_main)

    if modo_ipca != "Cenários IPCA":
        ipca_table_ot = ipca_table_ne = ipca_table_pe = ipca_table_main

    # Mostra IPCA do período
    ip_main = calc_ipca_periodo(d_ini, d_fim, ipca_table_main)
    vna_ini_val = _get_vna_na_data(d_ini, sorted(ipca_table_main, key=lambda x: x['data_fechamento']))
    vna_fim_val = _get_vna_na_data(d_fim, sorted(ipca_table_main, key=lambda x: x['data_fechamento']))
    st.markdown(f"""<div class='ibox'>
    IPCA acumulado no período: <b>{ip_main*100:.3f}%</b> &nbsp;·&nbsp;
    VNA em {d_ini:%d/%m/%Y}: <b>{vna_ini_val:.4f}</b> &nbsp;·&nbsp;
    VNA em {d_fim:%d/%m/%Y}: <b>{vna_fim_val:.4f}</b>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Selic / COPOM ──
    st.markdown("<div class='sec'>💰 Selic & Reuniões COPOM (até 2 anos)</div>",
                unsafe_allow_html=True)
    modo_selic = st.radio("Projeção Selic", ["Focus (automático)", "Manual"],
                           horizontal=True, key="mselic1")

    if modo_selic == "Focus (automático)" and focus.get('selic_copom'):
        copom_sched = build_copom_schedule_from_focus(
            focus['selic_copom'], selic_ini, d_ini, d_fim)
        if copom_sched:
            reunioes_txt = " → ".join([f"{c['reuniao']} {c['nova_taxa']:.2f}%" for c in copom_sched])
            st.markdown(f"<div class='sbox'>📅 COPOM no período: {reunioes_txt}</div>",
                        unsafe_allow_html=True)
    else:
        reunioes_periodo = [c for c in COPOM_CALENDARIO if d_ini <= c['data'] <= d_fim]
        projecoes_m = {}
        if reunioes_periodo:
            st.markdown(f"**{len(reunioes_periodo)} reuniões do COPOM na janela:**")
            cols_cop = st.columns(min(len(reunioes_periodo), 6))
            taxa_acum = selic_ini
            for i, reun in enumerate(reunioes_periodo):
                with cols_cop[i % 6]:
                    nova = st.number_input(
                        f"{reun['reuniao']}\n{reun['data']:%d/%m}",
                        value=max(10.0, taxa_acum - 0.25),
                        step=0.25, format="%.2f",
                        key=f"cop1_{reun['reuniao']}")
                    projecoes_m[reun['reuniao']] = nova
                    taxa_acum = nova
        copom_sched = build_copom_schedule_manual(projecoes_m, d_ini, d_fim)

    def calc_cdi_periodo(sched, di, df):
        if sched:
            return cdi_retorno_com_copom(selic_ini, sched, di, df)
        return cdi_retorno_simples(selic_ini, count_business_days(di, df))

    st.markdown("---")

    # ── Cenários de yield ──
    st.markdown("<div class='sec'>🎬 Cenários de Variação de Curva</div>",
                unsafe_allow_html=True)
    st.markdown("""<div class='ibox'>
    Variação em basis points (bps). Negativo = fechamento (queda de juro real → marcação positiva).
    Positivo = abertura (alta de juro real → marcação negativa).
    </div>""", unsafe_allow_html=True)

    col_c1, col_c2, col_c3 = st.columns(3)
    with col_c1:
        st.markdown("<span class='b-green'>🟢 Cenário 1 — Fechamento</span>",
                    unsafe_allow_html=True)
        vb5_c1  = st.number_input("Δ IMA-B5 (bps)",  value=-80, step=5, key="c1b5")
        vb5p_c1 = st.number_input("Δ IMA-B5+ (bps)", value=-23, step=5, key="c1b5p")
    with col_c2:
        st.markdown("<span class='b-yellow'>🟡 Cenário 2 — Manutenção</span>",
                    unsafe_allow_html=True)
        vb5_c2  = st.number_input("Δ IMA-B5 (bps)",  value=0,   step=5, key="c2b5")
        vb5p_c2 = st.number_input("Δ IMA-B5+ (bps)", value=0,   step=5, key="c2b5p")
    with col_c3:
        st.markdown("<span class='b-red'>🔴 Cenário 3 — Abertura</span>",
                    unsafe_allow_html=True)
        vb5_c3  = st.number_input("Δ IMA-B5 (bps)",  value=73,  step=5, key="c3b5")
        vb5p_c3 = st.number_input("Δ IMA-B5+ (bps)", value=50,  step=5, key="c3b5p")

    # IPCA por cenário
    ipca_c = [calc_ipca_periodo(d_ini, d_fim, t)
              for t in [ipca_table_ot, ipca_table_ne, ipca_table_pe]]

    def calc_cen(vb5, vb5p, ipca_p):
        b5  = imab5_retorno_total(yield_b5,  du_total, vb5,  dur_b5,  ipca_p)
        b5p = imab5_retorno_total(yield_b5p, du_total, vb5p, dur_b5p, ipca_p)
        cdi = calc_cdi_periodo(copom_sched, d_ini, d_fim)
        return b5, b5p, cdi

    r1 = calc_cen(vb5_c1, vb5p_c1, ipca_c[0])
    r2 = calc_cen(vb5_c2, vb5p_c2, ipca_c[1])
    r3 = calc_cen(vb5_c3, vb5p_c3, ipca_c[2])

    cenarios_calc = [
        ("🟢 Fechamento", r1, ipca_c[0], vb5_c1, vb5p_c1),
        ("🟡 Manutenção", r2, ipca_c[1], vb5_c2, vb5p_c2),
        ("🔴 Abertura",   r3, ipca_c[2], vb5_c3, vb5p_c3),
    ]

    st.markdown("---")
    st.markdown("<div class='sec'>📊 Resultados</div>", unsafe_allow_html=True)

    for label, (b5, b5p, cdi), ipca_p, db5_bps, db5p_bps in cenarios_calc:
        venc = max([('IMA-B 5', b5['retorno_total']),
                    ('IMA-B 5+', b5p['retorno_total']),
                    ('CDI', cdi)], key=lambda x: x[1])
        st.markdown(f"#### {label} &nbsp; <span class='winner'>🏆 {venc[0]}: {venc[1]*100:.2f}%</span>",
                    unsafe_allow_html=True)

        mc = st.columns(5)
        mc[0].metric("IMA-B 5",   f"{b5['retorno_total']*100:.2f}%",
                     f"{(b5['retorno_total']-cdi)*100:+.2f}pp vs CDI")
        mc[1].metric("IMA-B 5+",  f"{b5p['retorno_total']*100:.2f}%",
                     f"{(b5p['retorno_total']-cdi)*100:+.2f}pp vs CDI")
        mc[2].metric("CDI",        f"{cdi*100:.2f}%")
        mc[3].metric("IPCA Período", f"{ipca_p*100:.3f}%")
        mc[4].metric("IMA-B5 Real",
                     f"{((1+b5['retorno_total'])/(1+ipca_p)-1)*100:.2f}%")

        with st.expander("🔍 Decomposição"):
            d1, d2, d3 = st.columns(3)
            with d1:
                st.markdown("**IMA-B 5**")
                st.write(f"• Carrego: {b5['carrego']*100:.3f}%")
                st.write(f"• Marcação: {b5['marcacao']*100:+.3f}% ({db5_bps:+d} bps)")
                st.write(f"• Yield final: {b5['yield_final']:.4f}%")
            with d2:
                st.markdown("**IMA-B 5+**")
                st.write(f"• Carrego: {b5p['carrego']*100:.3f}%")
                st.write(f"• Marcação: {b5p['marcacao']*100:+.3f}% ({db5p_bps:+d} bps)")
                st.write(f"• Yield final: {b5p['yield_final']:.4f}%")
            with d3:
                st.markdown("**CDI / COPOM**")
                sched_disp = copom_sched
                if sched_disp:
                    for c in sched_disp:
                        st.write(f"• {c['reuniao']} ({c['data']:%d/%m/%Y}): {c['nova_taxa']:.2f}%")
                else:
                    st.write(f"• Selic fixa: {selic_ini:.2f}%")

    # ── Gráfico comparativo ──
    st.markdown("---")
    labels_g = ["🟢 Fechamento", "🟡 Manutenção", "🔴 Abertura"]
    fig = go.Figure()
    for idx, cor in CORES.items():
        if idx not in ['IMA-B 5', 'IMA-B 5+', 'CDI']:
            continue
        ys = []
        for _, (b5, b5p, cdi), _, _, _ in cenarios_calc:
            v = b5['retorno_total'] if idx == 'IMA-B 5' else (
                b5p['retorno_total'] if idx == 'IMA-B 5+' else cdi)
            ys.append(v * 100)
        fig.add_trace(go.Bar(name=idx, x=labels_g, y=ys, marker_color=cor,
                             text=[f"{v:.2f}%" for v in ys], textposition='outside'))

    fig.add_trace(go.Scatter(
        name='IPCA', x=labels_g, y=[c[2]*100 for c in cenarios_calc],
        mode='lines+markers',
        marker=dict(symbol='diamond', size=9, color=CORES['IPCA']),
        line=dict(color=CORES['IPCA'], dash='dot', width=1.5)))

    fig.update_layout(**PLOT_LAYOUT, barmode='group', height=400,
                      yaxis=dict(ticksuffix='%', gridcolor='#e2e8f0', zeroline=True),
                      title=dict(text=f"Retorno Total — {du_total} d.u. ({d_ini:%d/%m/%Y} → {d_fim:%d/%m/%Y})",
                                 font=dict(size=13, color='#0f172a')))
    st.plotly_chart(fig, use_container_width=True)

    # Gráfico retorno real
    fig2 = go.Figure()
    for idx, cor in CORES.items():
        if idx not in ['IMA-B 5', 'IMA-B 5+', 'CDI']:
            continue
        ys_r = []
        for _, (b5, b5p, cdi), ipca_p, _, _ in cenarios_calc:
            nom = b5['retorno_total'] if idx == 'IMA-B 5' else (
                b5p['retorno_total'] if idx == 'IMA-B 5+' else cdi)
            ys_r.append(((1+nom)/(1+ipca_p)-1)*100)
        fig2.add_trace(go.Bar(name=f"{idx} (real)", x=labels_g, y=ys_r,
                              marker_color=cor, opacity=0.85,
                              text=[f"{v:.2f}%" for v in ys_r], textposition='outside'))
    fig2.add_hline(y=0, line=dict(color='#94a3b8', width=1))
    fig2.update_layout(**PLOT_LAYOUT, barmode='group', height=360,
                       yaxis=dict(ticksuffix='%', gridcolor='#e2e8f0'),
                       title=dict(text="Retorno Real (descontado IPCA)",
                                  font=dict(size=13, color='#0f172a')))
    st.plotly_chart(fig2, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — PROJEÇÃO MÊS A MÊS
# ════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("<div class='sec'>📅 Projeção Mês a Mês — IMA-B 5 × IMA-B 5+ × CDI</div>",
                unsafe_allow_html=True)
    st.markdown("""<div class='ibox'>
    Retorno mensal de carrego + IPCA (via VNA ANBIMA) ± marcação a mercado.
    Idêntico à metodologia das abas <b>IMA MÊS A MÊS</b> e <b>Projeção IMA VS CDI MaM</b>.
    </div>""", unsafe_allow_html=True)

    col_mam1, col_mam2, col_mam3 = st.columns(3)
    with col_mam1:
        fonte_mam = st.radio("Fonte IPCA", ["Focus (mediana)", "Manual"],
                              horizontal=True, key="fonte_mam")
    with col_mam2:
        var_mam_sel = st.selectbox("Variação de curva (marcação)", [
            "Manutenção (0 bps)", "Fechamento (−20 bps)", "Fechamento Forte (−50 bps)",
            "Alta (+20 bps)", "Alta Forte (+50 bps)", "Personalizado"])
        var_map = {"Manutenção (0 bps)": 0, "Fechamento (−20 bps)": -20,
                   "Fechamento Forte (−50 bps)": -50, "Alta (+20 bps)": 20,
                   "Alta Forte (+50 bps)": 50}
        if var_mam_sel == "Personalizado":
            var_mam_bps = col_mam3.number_input("bps por mês", value=0, step=5, key="var_custom")
        else:
            var_mam_bps = var_map.get(var_mam_sel, 0)

    # IPCA para mam
    meses_futuros_mam = build_meses_futuros(28)
    ipca_list_mam = []

    if fonte_mam == "Focus (mediana)":
        if focus.get('ok') and focus.get('ipca_mensal'):
            ipca_list_mam = []
            for item in focus['ipca_mensal']:
                ref = item.get('data_referencia', '')
                if not ref:
                    continue
                try:
                    partes = ref.split('/')
                    mes, ano = int(partes[0]), int(partes[1])
                    fech = date(ano, mes + 1, 15) if mes < 12 else date(ano + 1, 1, 15)
                    # Só inclui meses futuros ao VNA base (evita dupla contagem)
                    if fech > d_fech_vna:
                        ipca_list_mam.append((ref, float(item.get('mediana') or item.get('media') or 0)))
                except Exception:
                    continue
            st.markdown(f"<div class='sbox'>✅ IPCA Focus: {len(ipca_list_mam)} meses futuros</div>",
                        unsafe_allow_html=True)
        else:
            ipca_list_mam = [(m, DEFAULTS_IPCA.get(m, 0.30)) for m in meses_futuros_mam[:24]]
            st.markdown("<div class='wbox'>Focus offline — usando defaults</div>",
                        unsafe_allow_html=True)
    else:
        st.markdown("**IPCA mensal projetado (%):**")
        meses_exibir_mam = meses_futuros_mam[:24]
        cols_mam_ipca = st.columns(6)
        for i, ms in enumerate(meses_exibir_mam):
            with cols_mam_ipca[i % 6]:
                v = st.number_input(ms, value=DEFAULTS_IPCA.get(ms, 0.30),
                                    step=0.01, format="%.2f", key=f"mam_ip_{ms}")
                ipca_list_mam.append((ms, v))

    ipca_table_mam = make_ipca_table_completa(ipca_list_mam)

    # CDI mam — usa Selic com COPOM se disponível
    def cdi_mes(du_m, d_i, d_f):
        sched_m = build_copom_schedule_from_focus(
            focus.get('selic_copom', []), selic_ini, d_i, d_f) if focus.get('ok') else []
        if sched_m:
            return cdi_retorno_com_copom(selic_ini, sched_m, d_i, d_f)
        return cdi_retorno_simples(selic_ini, du_m)

    def build_mam(d_start, d_end, y_b5, du_b5, y_b5p, du_b5p, var_bps, ip_tab):
        rows = []
        # Começa no primeiro dia útil do mês de d_start
        # mas nunca antes de d_start para evitar interpolação fora do âmbito
        cur = date(d_start.year, d_start.month, 1)
        # Avança para o primeiro dia útil >= d_start
        cur = max(cur, d_start)
        while cur <= d_end and not is_business_day(cur):
            cur += timedelta(days=1)

        while cur < d_end:
            if cur.month == 12:
                prox = date(cur.year + 1, 1, 1)
            else:
                prox = date(cur.year, cur.month + 1, 1)
            fim = prox - timedelta(days=1)
            fim = min(fim, d_end)
            while fim > cur and not is_business_day(fim):
                fim -= timedelta(days=1)
            if fim <= cur:
                cur = prox
                while not is_business_day(cur) and cur <= d_end:
                    cur += timedelta(days=1)
                continue

            du_m = count_business_days(cur, fim)
            if du_m <= 0:
                cur = prox
                continue

            ipca_m = calc_ipca_periodo(cur, fim, ip_tab) if ip_tab else 0.003
            b5_m   = imab5_retorno_total(y_b5,  du_m, var_bps, du_b5,  ipca_m)
            b5p_m  = imab5_retorno_total(y_b5p, du_m, var_bps, du_b5p, ipca_m)
            cdi_m  = cdi_mes(du_m, cur, fim)
            melhor = max([('IMA-B5', b5_m['retorno_total']),
                          ('IMA-B5+', b5p_m['retorno_total']),
                          ('CDI', cdi_m)], key=lambda x: x[1])[0]

            rows.append({'Mês': cur.strftime('%b/%Y'), 'Início': cur, 'Fim': fim,
                         'D.U.': du_m, 'IPCA (%)': ipca_m*100,
                         'IMA-B5 (%)':  b5_m['retorno_total']*100,
                         'IMA-B5+ (%)': b5p_m['retorno_total']*100,
                         'CDI (%)': cdi_m*100,
                         'Carrego B5 (%)':  b5_m['carrego']*100,
                         'Marcação B5 (%)': b5_m['marcacao']*100,
                         'B5 vs CDI (pp)': (b5_m['retorno_total']-cdi_m)*100,
                         'Melhor': melhor})
            cur = prox
            while not is_business_day(cur) and cur <= d_end:
                cur += timedelta(days=1)
        return pd.DataFrame(rows)

    df_mam = build_mam(d_ini, d_fim, yield_b5, dur_b5, yield_b5p, dur_b5p,
                       var_mam_bps, ipca_table_mam)

    if not df_mam.empty:
        # Gráfico barras mensais
        fig_mam = go.Figure()
        for nome, cor, col_n in [('IMA-B5','#0ea5e9','IMA-B5 (%)'),
                                  ('IMA-B5+','#8b5cf6','IMA-B5+ (%)'),
                                  ('CDI','#f59e0b','CDI (%)')]:
            fig_mam.add_trace(go.Bar(name=nome, x=df_mam['Mês'],
                                     y=df_mam[col_n], marker_color=cor, opacity=0.9))
        fig_mam.add_trace(go.Scatter(
            name='IPCA', x=df_mam['Mês'], y=df_mam['IPCA (%)'],
            mode='lines+markers',
            marker=dict(symbol='diamond', size=7, color='#ef4444'),
            line=dict(color='#ef4444', dash='dot', width=1.5)))
        fig_mam.update_layout(**PLOT_LAYOUT, barmode='group', height=380,
                              yaxis=dict(ticksuffix='%', gridcolor='#e2e8f0'),
                              xaxis=dict(tickangle=-35),
                              title=dict(text=f"Retorno Mensal ({var_mam_sel})",
                                         font=dict(size=13, color='#0f172a')))
        st.plotly_chart(fig_mam, use_container_width=True)

        # Acumulado
        df_mam['B5 Acum']  = (1+df_mam['IMA-B5 (%)']/100).cumprod()-1
        df_mam['B5P Acum'] = (1+df_mam['IMA-B5+ (%)']/100).cumprod()-1
        df_mam['CDI Acum'] = (1+df_mam['CDI (%)']/100).cumprod()-1

        fig_ac = go.Figure()
        fig_ac.add_trace(go.Scatter(name='IMA-B5', x=df_mam['Mês'],
                                    y=df_mam['B5 Acum']*100,
                                    line=dict(color='#0ea5e9', width=2.5),
                                    fill='tozeroy', fillcolor='rgba(14,165,233,.07)'))
        fig_ac.add_trace(go.Scatter(name='IMA-B5+', x=df_mam['Mês'],
                                    y=df_mam['B5P Acum']*100,
                                    line=dict(color='#8b5cf6', width=2, dash='dash')))
        fig_ac.add_trace(go.Scatter(name='CDI', x=df_mam['Mês'],
                                    y=df_mam['CDI Acum']*100,
                                    line=dict(color='#f59e0b', width=2)))
        fig_ac.update_layout(**PLOT_LAYOUT, height=340,
                             yaxis=dict(ticksuffix='%', gridcolor='#e2e8f0'),
                             xaxis=dict(tickangle=-35),
                             title=dict(text="Retorno Acumulado",
                                        font=dict(size=13, color='#0f172a')))
        st.plotly_chart(fig_ac, use_container_width=True)

        # Tabela
        st.dataframe(
            df_mam[['Mês','D.U.','IPCA (%)','IMA-B5 (%)','IMA-B5+ (%)','CDI (%)','B5 vs CDI (pp)','Melhor']].style.format({
                'IPCA (%)': '{:.3f}%', 'IMA-B5 (%)': '{:.3f}%',
                'IMA-B5+ (%)': '{:.3f}%', 'CDI (%)': '{:.3f}%',
                'B5 vs CDI (pp)': '{:+.3f}',
            }), use_container_width=True, height=320)

        # Resumo
        r1c, r2c, r3c = st.columns(3)
        ac_b5  = (1+df_mam['IMA-B5 (%)']/100).prod()-1
        ac_cdi = (1+df_mam['CDI (%)']/100).prod()-1
        sp     = ac_b5 - ac_cdi
        r1c.metric("IMA-B5 Acumulado",   f"{ac_b5*100:.2f}%")
        r2c.metric("CDI Acumulado",       f"{ac_cdi*100:.2f}%")
        r3c.metric("Spread IMA-B5 vs CDI", f"{sp*100:+.2f}%",
                   delta="IMA-B5 vence" if sp > 0 else "CDI vence")


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — CURVAS DE JUROS (ETTJ via B3)
# ════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("<div class='sec'>📉 ETTJ — Curvas de Juros (B3)</div>",
                unsafe_allow_html=True)
    st.markdown("""<div class='ibox'>
    Curvas <b>Pré</b> (LTN / NTN-F) e <b>IPCA</b> (NTN-B / DI × IPCA) da B3.
    Compara a última data disponível com uma semana atrás e um ano atrás.
    Dados do dia útil anterior — nunca projetados.
    </div>""", unsafe_allow_html=True)

    col_tc1, col_tc2, col_tc3 = st.columns(3)
    with col_tc1:
        d_ref_c   = st.date_input("Data atual",        value=last_business_day(),           key="drc")
    with col_tc2:
        d_sem_ant = st.date_input("Semana anterior",   value=last_business_day(d_ref_c, n=4), key="dsa")
    with col_tc3:
        d_ano_ant = st.date_input("1 ano atrás",       value=last_business_day_1y_ago(d_ref_c), key="daa")

    col_sel, col_btn = st.columns([2, 1])
    with col_sel:
        tipo_ettj = st.radio("Curvas a exibir", ["Pré", "IPCA", "Ambas"],
                              horizontal=True)
    with col_btn:
        btn_ettj = st.button("🔄 Buscar curvas (B3)", use_container_width=True,
                              type="primary")

    # ── Busca ──
    if btn_ettj:
        with st.spinner("Buscando curvas na B3..."):
            st.session_state['ettj_atual']   = get_ettj_b3(d_ref_c)
            st.session_state['ettj_sem_ant'] = get_ettj_b3(d_sem_ant)
            st.session_state['ettj_ano_ant'] = get_ettj_b3(d_ano_ant)
        ok = not st.session_state['ettj_atual'].empty
        if ok:
            st.markdown("<div class='sbox'>✅ Curvas carregadas com sucesso.</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown("<div class='wbox'>⚠️ B3 não retornou dados para esta data. "
                        "Tente outra data (dia útil recente).</div>",
                        unsafe_allow_html=True)

    ettj_atual   = st.session_state.get('ettj_atual',   pd.DataFrame())
    ettj_sem_ant = st.session_state.get('ettj_sem_ant', pd.DataFrame())
    ettj_ano_ant = st.session_state.get('ettj_ano_ant', pd.DataFrame())

    # ── Extrai curvas ──
    # B3 usa "DI x IPCA" internamente; exibimos como "IPCA" para o usuário
    if not ettj_atual.empty:
        df_pre_at  = parse_ettj_for_curve(ettj_atual,   'PRE')
        df_pre_sa  = parse_ettj_for_curve(ettj_sem_ant, 'PRE')
        df_pre_aa  = parse_ettj_for_curve(ettj_ano_ant, 'PRE')
        df_ipca_at = parse_ettj_for_curve(ettj_atual,   'DI x IPCA')
        df_ipca_sa = parse_ettj_for_curve(ettj_sem_ant, 'DI x IPCA')
        df_ipca_aa = parse_ettj_for_curve(ettj_ano_ant, 'DI x IPCA')
    else:
        df_pre_at  = df_pre_sa  = df_pre_aa  = pd.DataFrame()
        df_ipca_at = df_ipca_sa = df_ipca_aa = pd.DataFrame()

    # ── Função de plot ──
    def plot_curva_3datas(df_at, df_sa, df_aa, x_col, titulo, label_x,
                          lab_at, lab_sa, lab_aa, linha_ref=None):
        fig = go.Figure()
        estilos = [
            (df_at, lab_at, '#0369a1', 'circle',  2.5, None),
            (df_sa, lab_sa, '#f59e0b', 'square',  2.0, 'dash'),
            (df_aa, lab_aa, '#94a3b8', 'diamond', 1.5, 'dot'),
        ]
        for df_, lbl, cor, sym, wid, dash in estilos:
            if df_ is None or df_.empty:
                continue
            lkw = dict(color=cor, width=wid)
            if dash:
                lkw['dash'] = dash
            fig.add_trace(go.Scatter(
                name=lbl, x=df_[x_col], y=df_['taxa'],
                mode='lines+markers',
                line=lkw,
                marker=dict(size=8, symbol=sym, color=cor,
                            line=dict(color='white', width=1)),
                hovertemplate=f'<b>{lbl}</b><br>%{{x}}: %{{y:.4f}}%<extra></extra>'))
        if linha_ref:
            fig.add_hline(y=linha_ref[0],
                          line=dict(color='#dc2626', width=1.4, dash='dot'),
                          annotation_text=linha_ref[1],
                          annotation_font_color='#dc2626',
                          annotation_font_size=11)
        fig.update_layout(
            template='plotly_white',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='#fafafa',
            font=dict(color='#1e293b', family='Inter, sans-serif', size=12),
            height=450,
            margin=dict(t=70, b=40, l=10, r=10),
            hovermode='x unified',
            title=dict(text=titulo, font=dict(size=13, color='#0f172a')),
            xaxis=dict(
                title=dict(text=label_x, font=dict(size=12, color='#374151')),
                tickfont=dict(size=11, color='#374151'),
                gridcolor='#e5e7eb', showgrid=True,
                tickangle=-30, linecolor='#d1d5db', linewidth=1,
            ),
            yaxis=dict(
                title=dict(text='Taxa (% a.a.)', font=dict(size=12, color='#374151')),
                tickfont=dict(size=11, color='#374151'),
                ticksuffix='%', gridcolor='#e5e7eb', showgrid=True,
                zeroline=False, linecolor='#d1d5db', linewidth=1,
            ),
            legend=dict(
                bgcolor='rgba(255,255,255,0.95)',
                bordercolor='#e2e8f0', borderwidth=1,
                font=dict(size=11, color='#1e293b'),
                orientation='h', y=1.12, x=0, xanchor='left',
            ),
        )
        return fig

    # ── Curva IPCA ──
    x_col_ipca = ('venc' if not df_ipca_at.empty and 'venc' in df_ipca_at.columns
                  else 'prazo_anos')

    if tipo_ettj in ["IPCA", "Ambas"]:
        if df_ipca_at.empty:
            st.markdown("<div class='wbox'>⚠️ Clique em <b>Buscar curvas</b> para carregar os dados.</div>",
                        unsafe_allow_html=True)
        else:
            fig_ipca = plot_curva_3datas(
                df_ipca_at, df_ipca_sa, df_ipca_aa, x_col_ipca,
                "Curva IPCA — NTN-B", "Prazo (d.u.)",
                f"Atual ({d_ref_c:%d/%m/%Y})",
                f"Semana ant. ({d_sem_ant:%d/%m/%Y})",
                f"1 ano atrás ({d_ano_ant:%d/%m/%Y})",
                (yield_b5, f"IMA-B5 atual: {yield_b5:.4f}%"))
            st.plotly_chart(fig_ipca, use_container_width=True)

    # ── Curva Pré ──
    if tipo_ettj in ["Pré", "Ambas"]:
        if df_pre_at.empty:
            st.markdown("<div class='wbox'>⚠️ Clique em <b>Buscar curvas</b> para carregar os dados.</div>",
                        unsafe_allow_html=True)
        else:
            fig_pre = plot_curva_3datas(
                df_pre_at, df_pre_sa, df_pre_aa, 'prazo_anos',
                "Curva Pré — LTN / NTN-F", "Prazo (anos)",
                f"Atual ({d_ref_c:%d/%m/%Y})",
                f"Semana ant. ({d_sem_ant:%d/%m/%Y})",
                f"1 ano atrás ({d_ano_ant:%d/%m/%Y})")
            st.plotly_chart(fig_pre, use_container_width=True)

    # ── Variação semanal da curva IPCA ──
    if not df_ipca_at.empty and not df_ipca_sa.empty:
        st.markdown("**📊 Variação semanal — Curva IPCA (bps)**")
        n = min(len(df_ipca_at), len(df_ipca_sa))
        x_v    = df_ipca_at.iloc[:n][x_col_ipca].values
        delta_v = (df_ipca_at.iloc[:n]['taxa'].values -
                   df_ipca_sa.iloc[:n]['taxa'].values) * 100
        fig_delta = go.Figure(go.Bar(
            x=x_v, y=delta_v,
            marker_color=['#ef4444' if v > 0 else '#22c55e' for v in delta_v],
            text=[f"{v:+.1f}" for v in delta_v], textposition='outside'))
        fig_delta.add_hline(y=0, line=dict(color='#94a3b8', width=1))
        fig_delta.update_layout(
            template='plotly_white',
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#fafafa',
            height=270, showlegend=False,
            margin=dict(t=50, b=30, l=10, r=10),
            xaxis=dict(title=dict(text='Prazo (d.u.)', font=dict(color='#374151')),
                       tickfont=dict(size=11, color='#374151'),
                       gridcolor='#e5e7eb'),
            yaxis=dict(title=dict(text='Δ (bps)', font=dict(color='#374151')),
                       tickfont=dict(size=11, color='#374151'),
                       gridcolor='#e5e7eb'),
            title=dict(text="Variação semanal por vértice — Curva IPCA (bps)",
                       font=dict(size=12, color='#0f172a')))
        st.plotly_chart(fig_delta, use_container_width=True)

    # ── Histórico Redemption Yield ──
    st.markdown("---")
    st.markdown("<div class='sec'>📈 Histórico Redemption Yield IMA-B 5</div>",
                unsafe_allow_html=True)

    hist_rows = []
    upload_hist = st.file_uploader("Carregue CSV (data,yield)", type=['csv'],
                                    key="hist_upload",
                                    help="Formato: 2024-01-02,7.55 — uma linha por dia")
    hist_txt = st.text_area("Ou cole os dados (data,yield — uma linha por data)",
                             height=100, placeholder="2024-01-02,7.55\n2024-02-01,7.60\n...")

    if upload_hist:
        content = upload_hist.read().decode('utf-8')
        for row in csv.reader(io.StringIO(content)):
            try:
                hist_rows.append({'data': date.fromisoformat(row[0].strip()),
                                   'yield': float(row[1].strip())})
            except Exception:
                continue
    elif hist_txt.strip():
        for linha in hist_txt.strip().split('\n'):
            try:
                p = linha.split(',')
                hist_rows.append({'data': date.fromisoformat(p[0].strip()),
                                   'yield': float(p[1].strip())})
            except Exception:
                continue
    else:
        # Defaults baseados na aba Redemption Yield da planilha
        defaults_hist = {
            "2023-05-31": 6.0494, "2023-06-30": 5.7224, "2023-07-31": 5.8,
            "2023-08-31": 5.82,   "2023-09-29": 5.87,   "2023-10-31": 5.91,
            "2023-11-30": 5.95,   "2023-12-29": 5.89,   "2024-01-31": 5.93,
            "2024-02-29": 5.97,   "2024-03-28": 5.97,   "2024-04-30": 6.02,
            "2024-05-31": 6.05,   "2024-06-28": 6.10,   "2024-07-31": 6.18,
            "2024-08-30": 6.25,   "2024-09-30": 6.35,   "2024-10-31": 6.65,
            "2024-11-29": 7.00,   "2024-12-31": 7.20,   "2025-01-31": 7.35,
            "2025-02-28": 7.40,   "2025-03-31": 7.45,   "2025-04-30": 7.52,
            "2025-05-30": 7.60,   "2025-06-30": 7.60,   "2025-07-31": 7.63,
            "2025-08-29": 7.65,   "2025-09-30": 7.68,   "2025-10-31": 7.70,
            "2025-11-28": 7.71,   "2025-12-31": 7.72,   "2026-01-30": 7.75,
            "2026-02-27": 7.75,   "2026-03-31": 7.75,   "2026-04-10": 7.7519,
        }
        hist_rows = [{'data': date.fromisoformat(k), 'yield': v}
                     for k, v in defaults_hist.items()]

    if hist_rows:
        df_h = pd.DataFrame(sorted(hist_rows, key=lambda x: x['data']))
        media_h = df_h['yield'].mean()
        dp_h    = df_h['yield'].std()
        n_obs   = len(df_h)
        data_ini_h = df_h['data'].iloc[0]
        data_fim_h = df_h['data'].iloc[-1]

        fig_h = go.Figure()

        # Área de 2 desvios
        fig_h.add_trace(go.Scatter(
            x=pd.concat([df_h['data'], df_h['data'][::-1]]),
            y=[media_h + 2*dp_h]*n_obs + [media_h - 2*dp_h]*n_obs,
            fill='toself', fillcolor='rgba(14,165,233,.06)',
            line=dict(width=0), showlegend=False,
            hoverinfo='skip', name='±2σ'))

        # Área de 1 desvio
        fig_h.add_trace(go.Scatter(
            x=pd.concat([df_h['data'], df_h['data'][::-1]]),
            y=[media_h + dp_h]*n_obs + [media_h - dp_h]*n_obs,
            fill='toself', fillcolor='rgba(14,165,233,.11)',
            line=dict(width=0), showlegend=False,
            hoverinfo='skip', name='±1σ'))

        # Série principal
        fig_h.add_trace(go.Scatter(
            name='Yield IMA-B5', x=df_h['data'], y=df_h['yield'],
            mode='lines',
            line=dict(color='#0ea5e9', width=2.2),
            hovertemplate='%{x|%d/%m/%Y}: <b>%{y:.4f}%</b><extra></extra>'))

        # Pontos nos extremos e atual
        fig_h.add_trace(go.Scatter(
            x=[df_h['data'].iloc[0], df_h['data'].iloc[-1]],
            y=[df_h['yield'].iloc[0], df_h['yield'].iloc[-1]],
            mode='markers',
            marker=dict(size=8, color='#0ea5e9', symbol='circle'),
            showlegend=False,
            hovertemplate='%{x|%d/%m/%Y}: <b>%{y:.4f}%</b><extra></extra>'))

        # Linha da média — linha horizontal reta
        fig_h.add_shape(type='line',
                        x0=data_ini_h, x1=data_fim_h,
                        y0=media_h, y1=media_h,
                        line=dict(color='#64748b', width=1.5, dash='dash'))
        fig_h.add_annotation(x=data_fim_h, y=media_h,
                              text=f"Média: {media_h:.2f}%",
                              showarrow=False, xanchor='right', yanchor='bottom',
                              font=dict(color='#64748b', size=11))

        # Linha +1σ
        fig_h.add_shape(type='line',
                        x0=data_ini_h, x1=data_fim_h,
                        y0=media_h+dp_h, y1=media_h+dp_h,
                        line=dict(color='#94a3b8', width=1, dash='dot'))
        fig_h.add_annotation(x=data_fim_h, y=media_h+dp_h,
                              text=f"+1σ: {media_h+dp_h:.2f}%",
                              showarrow=False, xanchor='right', yanchor='bottom',
                              font=dict(color='#94a3b8', size=10))

        # Linha -1σ
        fig_h.add_shape(type='line',
                        x0=data_ini_h, x1=data_fim_h,
                        y0=media_h-dp_h, y1=media_h-dp_h,
                        line=dict(color='#94a3b8', width=1, dash='dot'))
        fig_h.add_annotation(x=data_fim_h, y=media_h-dp_h,
                              text=f"-1σ: {media_h-dp_h:.2f}%",
                              showarrow=False, xanchor='right', yanchor='bottom',
                              font=dict(color='#94a3b8', size=10))

        # Yield atual
        fig_h.add_shape(type='line',
                        x0=data_ini_h, x1=data_fim_h,
                        y0=yield_b5, y1=yield_b5,
                        line=dict(color='#ef4444', width=1.5, dash='dot'))
        fig_h.add_annotation(x=data_ini_h, y=yield_b5,
                              text=f"Atual: {yield_b5:.4f}%",
                              showarrow=False, xanchor='left', yanchor='top',
                              font=dict(color='#ef4444', size=11, weight=700))

        fig_h.update_layout(
            **PLOT_LAYOUT, height=400,
            xaxis=dict(title='', gridcolor='#e2e8f0', showgrid=False),
            yaxis=dict(title='Yield Real (% a.a.)', ticksuffix='%',
                       gridcolor='#f1f5f9', zeroline=False),
            title=dict(
                text=f"Histórico Redemption Yield IMA-B 5  |  Média desde {data_ini_h:%b/%Y}: {media_h:.2f}%  ·  σ: {dp_h:.2f}%  ·  {n_obs} obs.",
                font=dict(size=12, color='#0f172a')),
            hovermode='x unified',
            showlegend=False,
        )
        st.plotly_chart(fig_h, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — SIMULAÇÃO DE ALOCAÇÃO
# ════════════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown("<div class='sec'>💼 Simulação de Alocação — Carteira RF</div>",
                unsafe_allow_html=True)
    st.markdown("""<div class='ibox'>
    Análise da carteira de renda fixa composta por <b>SAFRA FF RF IMAB 5</b>
    e <b>SF FF CAIXA FI RF DI</b>. Simula retorno esperado e volatilidade
    antes e após movimentações, nos três cenários de mercado.
    </div>""", unsafe_allow_html=True)

    # ── Contexto do plano ──
    st.markdown("### 🏦 Plano B — Patrimônio de Referência")
    col_ref1, col_ref2, col_ref3 = st.columns(3)
    with col_ref1:
        total_rf_ref = st.number_input(
            "Total RF Referência (R$)",
            value=1_995_061_895.83, step=10e6, format="%.2f",
            help="Total da carteira RF ampla do Plano B (denominador para % Total RF)")
    with col_ref2:
        total_pl_plano = st.number_input(
            "Total PL Plano B (R$)",
            value=15_391_694_217.47, step=100e6, format="%.2f")
    with col_ref3:
        total_rf_sub = st.number_input(
            "Total RF Curto (R$)",
            value=788_101_113.52, step=10e6, format="%.2f",
            help="Segmento RF curto (apenas para referência)")

    # ── Fundos ──
    st.markdown("---")
    col_f1, col_f2 = st.columns(2)

    with col_f1:
        st.markdown("### 🟢 SAFRA FF RF IMAB 5")
        val_imab5 = st.number_input("Patrimônio Líquido (R$)", value=427_117_255.03,
                                     step=1e6, format="%.2f", key="vimab5")
        vol_imab5 = st.number_input("Volatilidade histórica (%)", value=1.0620,
                                     step=0.01, format="%.4f",
                                     help="Volatilidade anualizada histórica do fundo")

    with col_f2:
        st.markdown("### 🟡 SF FF CAIXA FI RF DI")
        val_cdi_f = st.number_input("Patrimônio Líquido (R$)", value=1_206_960_782.31,
                                     step=1e6, format="%.2f", key="vcdi")
        vol_cdi_f = st.number_input("Volatilidade histórica (%)", value=0.0,
                                     step=0.01, format="%.4f")

    total_cart = val_imab5 + val_cdi_f
    pct_imab5_at = val_imab5 / total_cart if total_cart > 0 else 0
    pct_cdi_at   = val_cdi_f / total_cart if total_cart > 0 else 0

    # ── Participações ──
    st.markdown("---")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("SAFRA IMAB 5", fmt_brl_short(val_imab5),
               f"{pct_imab5_at*100:.1f}% da carteira")
    mc2.metric("SF CAIXA DI",  fmt_brl_short(val_cdi_f),
               f"{pct_cdi_at*100:.1f}% da carteira")
    mc3.metric("% Total RF",
               f"{(total_cart/total_rf_ref*100):.1f}%" if total_rf_ref > 0 else "—",
               help="Total dos dois fundos / Total RF de referência (1.995 B)")
    mc4.metric("% PL Plano B",
               f"{(total_cart/total_pl_plano*100):.2f}%" if total_pl_plano > 0 else "—")

    # ── Movimentação ──
    st.markdown("---")
    st.markdown("### 🔄 Simulação de Movimentação")
    col_mv1, col_mv2 = st.columns(2)
    with col_mv1:
        mov_imab5 = st.number_input("Movimentação SAFRA IMAB 5 (R$)",
                                     value=50_000_000.0, step=5e6, format="%.2f",
                                     help="Positivo = aporte; Negativo = resgate")
    mov_cdi_auto = -mov_imab5
    col_mv2.metric("Movimentação SF CAIXA DI", fmt_brl_short(mov_cdi_auto),
                   help="Compensatório automático")

    val_imab5_pos = max(0.0, val_imab5 + mov_imab5)
    val_cdi_pos   = max(0.0, val_cdi_f  + mov_cdi_auto)
    total_pos     = val_imab5_pos + val_cdi_pos
    pct_imab5_pos = val_imab5_pos / total_pos if total_pos > 0 else 0
    pct_cdi_pos   = val_cdi_pos   / total_pos if total_pos > 0 else 0

    st.markdown("**Posição após movimentação:**")
    pp1, pp2, pp3 = st.columns(3)
    pp1.metric("SAFRA IMAB 5", fmt_brl_short(val_imab5_pos),
               f"{pct_imab5_pos*100:.1f}% ({(pct_imab5_pos-pct_imab5_at)*100:+.1f}pp)")
    pp2.metric("SF CAIXA DI",  fmt_brl_short(val_cdi_pos),
               f"{pct_cdi_pos*100:.1f}% ({(pct_cdi_pos-pct_cdi_at)*100:+.1f}pp)")
    pp3.metric("Total Carteira RF", fmt_brl_short(total_pos))

    # ── Retorno × Cenários ──
    st.markdown("---")
    st.markdown("### 📈 Retorno Esperado por Cenário")

    # Usa retornos do tab1 (calculados acima — Streamlit executa tabs em sequência)
    # Guard: garante que as variáveis existem mesmo se tab1 não calculou
    _zero = {'retorno_total': 0.0}
    _r1 = r1 if 'r1' in dir() else (_zero, _zero, 0.0)
    _r2 = r2 if 'r2' in dir() else (_zero, _zero, 0.0)
    _r3 = r3 if 'r3' in dir() else (_zero, _zero, 0.0)
    _ipca_c = ipca_c if 'ipca_c' in dir() else [0.025, 0.025, 0.025]

    rets_cen = {
        '🟢 Fechamento':  (_r1[0]['retorno_total'], _r1[2]),
        '🟡 Manutenção':  (_r2[0]['retorno_total'], _r2[2]),
        '🔴 Abertura':    (_r3[0]['retorno_total'], _r3[2]),
    }

    rows_aloc = []
    for lbl, (ret_b5_v, ret_cdi_v) in rets_cen.items():
        ret_at   = pct_imab5_at  * ret_b5_v + pct_cdi_at  * ret_cdi_v
        ret_pos  = pct_imab5_pos * ret_b5_v + pct_cdi_pos * ret_cdi_v
        vol_at   = pct_imab5_at  * (vol_imab5 / 100)
        vol_pos  = pct_imab5_pos * (vol_imab5 / 100)
        rows_aloc.append({
            'Cenário':           lbl,
            'Ret. Atual (%)':    ret_at  * 100,
            'Ret. Pós-Mov. (%)': ret_pos * 100,
            'Δ Ret. (pp)':       (ret_pos - ret_at) * 100,
            'Vol. Atual (%)':    vol_at  * 100,
            'Vol. Pós-Mov. (%)': vol_pos * 100,
            'R$ Resultado (Atual)':   val_imab5*ret_b5_v + val_cdi_f*ret_cdi_v,
            'R$ Resultado (Pós)':     val_imab5_pos*ret_b5_v + val_cdi_pos*ret_cdi_v,
        })

    df_aloc = pd.DataFrame(rows_aloc)

    fig_aloc = go.Figure()
    fig_aloc.add_trace(go.Bar(name='Atual', x=df_aloc['Cenário'],
                               y=df_aloc['Ret. Atual (%)'], marker_color='#60a5fa',
                               text=[f"{v:.2f}%" for v in df_aloc['Ret. Atual (%)']],
                               textposition='outside'))
    fig_aloc.add_trace(go.Bar(name='Pós-Movimentação', x=df_aloc['Cenário'],
                               y=df_aloc['Ret. Pós-Mov. (%)'], marker_color='#0ea5e9',
                               text=[f"{v:.2f}%" for v in df_aloc['Ret. Pós-Mov. (%)']],
                               textposition='outside'))
    fig_aloc.update_layout(
        **PLOT_LAYOUT, barmode='group', height=380,
        yaxis=dict(ticksuffix='%', gridcolor='#e2e8f0'),
        title=dict(text='Retorno Esperado — Antes vs Depois da Movimentação',
                   font=dict(size=13, color='#0f172a')))
    st.plotly_chart(fig_aloc, use_container_width=True)

    st.dataframe(df_aloc.style.format({
        'Ret. Atual (%)':    '{:.3f}%',
        'Ret. Pós-Mov. (%)': '{:.3f}%',
        'Δ Ret. (pp)':       '{:+.4f}',
        'Vol. Atual (%)':    '{:.3f}%',
        'Vol. Pós-Mov. (%)': '{:.3f}%',
        'R$ Resultado (Atual)': 'R$ {:,.0f}',
        'R$ Resultado (Pós)':   'R$ {:,.0f}',
    }), use_container_width=True)

    # Pizzas
    col_pie1, col_pie2 = st.columns(2)
    for col_pie, v_b5, v_cdi, title_ in [
        (col_pie1, val_imab5,     val_cdi_f,   "Alocação Atual"),
        (col_pie2, val_imab5_pos, val_cdi_pos,  "Pós-Movimentação"),
    ]:
        with col_pie:
            tot = v_b5 + v_cdi
            fig_pie = go.Figure(go.Pie(
                labels=['SAFRA IMAB 5', 'SF CAIXA DI'],
                values=[v_b5, v_cdi], hole=0.52,
                marker_colors=['#0ea5e9', '#f59e0b'],
                textinfo='label+percent',
                textfont=dict(size=11, color='#1e293b'),
                pull=[0.02, 0],
            ))
            fig_pie.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                title=dict(text=title_, font=dict(size=12, color='#0f172a')),
                height=280, showlegend=False,
                margin=dict(t=40, b=10, l=10, r=10),
                font=dict(color='#1e293b'),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # Resumo retorno real
    st.markdown("---")
    st.markdown("### 📊 Retorno Real da Carteira (descontado IPCA)")
    res_cols = st.columns(3)
    for col_, lbl in zip(res_cols, rets_cen.keys()):
        ret_b5_v, ret_cdi_v = rets_cen[lbl]
        ret_nom = pct_imab5_at * ret_b5_v + pct_cdi_at * ret_cdi_v
        ipca_v  = _ipca_c[0] if "Fechamento" in lbl else (
                  _ipca_c[1] if "Manutenção" in lbl else _ipca_c[2])
        ret_real = (1+ret_nom)/(1+ipca_v)-1
        col_.metric(lbl, f"{ret_nom*100:.2f}% nominal", f"{ret_real*100:.2f}% real")

# ── Footer ──
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#94a3b8; font-size:.73rem; padding:10px 0;">
  📈 Dashboard IMA-B 5 × CDI · Metodologia ANBIMA/VNA · Focus/BCB · pyettj/B3 ·
  Uso interno · Não constitui recomendação de investimento
</div>
""", unsafe_allow_html=True)
