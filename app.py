"""
📈 Dashboard IMA-B 5 × CDI — Rentabilidade
Metodologia ANBIMA/VNA · Focus/BCB · ETTJ Pré + Juro Real
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta, datetime
import io, csv

from utils import (
    is_business_day, count_business_days, business_days_list, date_plus_du,
    _get_vna_na_data, calc_ipca_periodo, build_ipca_table, build_ipca_table_from_focus,
    imab5_retorno_total,
    cdi_retorno_com_copom, cdi_retorno_simples,
    build_copom_schedule_from_focus, build_copom_schedule_manual, COPOM_CALENDARIO,
    fetch_focus_all,
    fetch_ettj_anbima, get_vencimentos_ntnb_padrao,
    fmt_pct, fmt_pct_aa, fmt_brl, fmt_brl_short,
)

# ──────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="IMA-B 5 × CDI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ── Base ── */
.stApp { background: #0a0e1a; }
[data-testid="stSidebar"] { background: #0d1117; border-right: 1px solid #1e2738; }

/* ── Métricas ── */
div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #111827 0%, #0f1923 100%);
    border: 1px solid #1e2d45;
    border-radius: 10px;
    padding: 14px 18px;
    box-shadow: 0 2px 12px rgba(0,0,0,.4);
}
div[data-testid="metric-container"] label { color: #5a7099 !important; font-size:.78rem !important; text-transform:uppercase; letter-spacing:.06em; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #c8d8f0 !important; font-size:1.5rem !important; font-weight:700; }

/* ── Seções ── */
.sec { font-size:.9rem; font-weight:700; color:#4fc3a1; text-transform:uppercase;
       letter-spacing:.1em; padding:6px 0 4px; border-bottom:1px solid #1e3a2f;
       margin-bottom:14px; }

/* ── Info box ── */
.ibox { background:#0a1e2e; border-left:3px solid #3b82f6; border-radius:0 6px 6px 0;
        padding:10px 14px; font-size:.84rem; color:#8ab4cc; margin:6px 0 12px; line-height:1.5; }

/* ── Cenário badges ── */
.b-green { background:#0a2e1e; color:#34d399; padding:2px 9px; border-radius:16px; font-size:.76rem; font-weight:700; border:1px solid #065f46; }
.b-yellow{ background:#2a1e00; color:#fbbf24; padding:2px 9px; border-radius:16px; font-size:.76rem; font-weight:700; border:1px solid #78350f; }
.b-red   { background:#2a0a0a; color:#f87171; padding:2px 9px; border-radius:16px; font-size:.76rem; font-weight:700; border:1px solid #7f1d1d; }

/* ── Vencedor ── */
.winner { color:#fbbf24; font-weight:700; }

h1,h2,h3,h4 { color:#c8d8f0 !important; }
hr { border-color:#1e2738; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="padding:18px 0 6px">
  <span style="font-size:2rem">📈</span>
  <span style="font-size:1.6rem; font-weight:800; margin-left:10px;
    background:linear-gradient(90deg,#4fc3a1,#60a5fa);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
    IMA-B 5 × CDI — Dashboard de Rentabilidade
  </span><br>
  <span style="color:#4a6080; font-size:.85rem; margin-left:3.2rem;">
    Metodologia ANBIMA · VNA · Marcação a Mercado · Focus/BCB
  </span>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# FOCUS DATA (cache)
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_focus():
    return fetch_focus_all()

@st.cache_data(ttl=86400, show_spinner=False)
def load_ettj(data_str):
    return fetch_ettj_anbima(date.fromisoformat(data_str))

# Carrega dados Focus na inicialização
if 'focus' not in st.session_state:
    with st.spinner("Buscando Focus/BCB..."):
        st.session_state['focus'] = load_focus()

focus = st.session_state.get('focus', {})

# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Parâmetros")
    if st.button("🔄 Atualizar Focus/BCB", use_container_width=True):
        load_focus.clear()
        st.session_state['focus'] = load_focus()
        focus = st.session_state['focus']
        st.success("Dados atualizados!")

    st.markdown("---")
    st.markdown("### 📊 IMA-B 5")
    c1s, c2s = st.columns(2)
    with c1s:
        yield_b5 = st.number_input("Yield (% a.a.)", value=7.7519, step=0.01,
                                    format="%.4f", key="yb5")
    with c2s:
        dur_b5 = st.number_input("Duration (d.u.)", value=496, step=1, key="db5")

    st.markdown("### 📊 IMA-B 5+")
    c3s, c4s = st.columns(2)
    with c3s:
        yield_b5p = st.number_input("Yield (% a.a.)", value=7.2157, step=0.01,
                                     format="%.4f", key="yb5p")
    with c4s:
        dur_b5p = st.number_input("Duration (d.u.)", value=2437, step=1, key="db5p")

    st.markdown("### 📅 Janela")
    d_ini = st.date_input("Início", value=date(2026, 4, 10), key="dini")
    d_fim = st.date_input("Fim", value=date_plus_du(date(2026, 4, 10), 181), key="dfim")
    du_total = count_business_days(d_ini, d_fim)
    st.info(f"📆 **{du_total}** dias úteis")

    st.markdown("### 💰 Selic atual (% a.a.)")
    selic_ini = st.number_input("Selic", value=14.75, step=0.25, format="%.2f")

    st.markdown("---")
    st.markdown("### 📐 VNA Base")
    vna_base = st.number_input("VNA (último IPCA divulgado)", value=4673.2559,
                                format="%.4f", step=0.0001, key="vna")
    d_fech_vna = st.date_input("Data fechamento IPCA", value=date(2026, 4, 15),
                                key="dfvna",
                                help="Data de fechamento do último IPCA já divulgado")


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def ipca_anual_focus():
    ano = str(date.today().year)
    for a in focus.get('ipca_anual', []):
        if str(a['ano']) == ano:
            return a.get('mediana') or a.get('media')
    return None

def selic_anual_focus():
    ano = str(date.today().year)
    for a in focus.get('selic_anual', []):
        if str(a['ano']) == ano:
            return a.get('mediana') or a.get('media')
    return None

def color_delta(v):
    if v > 0.001: return "#34d399"
    if v < -0.001: return "#f87171"
    return "#94a3b8"


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Comparativo de Cenários",
    "📅 Projeção Mês a Mês",
    "📉 Curvas de Juros (ETTJ)",
    "💼 Simulação de Alocação",
])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — COMPARATIVO DE CENÁRIOS
# ════════════════════════════════════════════════════════════════════════════

with tab1:

    # ── Dados Focus no topo ──
    ipca_a = ipca_anual_focus()
    selic_a = selic_anual_focus()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🎯 IPCA Focus (ano)", f"{ipca_a:.2f}%" if ipca_a else "—")
    m2.metric("🏦 Selic Focus (a.a.)", f"{selic_a:.2f}%" if selic_a else "—")
    m3.metric("📆 Dias úteis (janela)", f"{du_total} d.u.")
    status = "✅ Online" if focus.get('ok') else "⚠️ Offline"
    m4.metric("Focus/BCB", status)

    st.markdown("---")

    # ── IPCA projetado ──
    st.markdown("<div class='sec'>📌 IPCA Projetado</div>", unsafe_allow_html=True)

    modo_ipca = st.radio("Fonte", ["Focus (mediana)", "Manual", "Cenários IPCA"],
                          horizontal=True, key="modo_ipca")

    ipca_table_main = []

    if modo_ipca == "Focus (mediana)":
        if focus.get('ok') and focus.get('ipca_mensal'):
            ipca_table_main = build_ipca_table_from_focus(
                focus['ipca_mensal'], vna_base, d_fech_vna)
            st.success(f"✅ {len(ipca_table_main)-1} meses do Focus carregados")
        else:
            st.warning("Focus indisponível — use 'Manual'")

    elif modo_ipca == "Manual":
        # Meses do período + 6
        meses_seq = []
        d_tmp = d_fech_vna
        for _ in range(20):
            m_tmp = d_tmp.month + 1 if d_tmp.month < 12 else 1
            a_tmp = d_tmp.year if d_tmp.month < 12 else d_tmp.year + 1
            d_tmp = date(a_tmp, m_tmp, 15)
            meses_seq.append(f"{d_tmp.month:02d}/{d_tmp.year}")
            if d_tmp > d_fim + timedelta(days=180):
                break

        defs = {"04/2026":0.573,"05/2026":0.320,"06/2026":0.343,"07/2026":0.173,
                "08/2026":0.093,"09/2026":0.437,"10/2026":0.177,"11/2026":0.197,
                "12/2026":0.427,"01/2027":0.360,"02/2027":0.280,"03/2027":0.380}

        ipca_manual = []
        cols_m = st.columns(6)
        for i, ms in enumerate(meses_seq[:12]):
            with cols_m[i % 6]:
                v = st.number_input(ms, value=defs.get(ms, 0.30), step=0.01,
                                    format="%.2f", key=f"im_{ms}")
                ipca_manual.append((ms, v))
        ipca_table_main = build_ipca_table(ipca_manual, vna_base, d_fech_vna)

    else:  # Cenários IPCA
        c_ot, c_ne, c_pe = st.columns(3)
        with c_ot: ipca_ot_aa = st.number_input("🟢 Otimista (% a.a.)", value=5.0, step=0.1)
        with c_ne: ipca_ne_aa = st.number_input("🟡 Neutro (% a.a.)", value=ipca_a or 6.0, step=0.1)
        with c_pe: ipca_pe_aa = st.number_input("🔴 Pessimista (% a.a.)", value=7.5, step=0.1)

        def aa_to_list(taxa_aa, n_meses=18):
            men = ((1 + taxa_aa/100)**(1/12) - 1) * 100
            d_tmp = d_fech_vna
            lst = []
            for _ in range(n_meses):
                m_tmp = d_tmp.month+1 if d_tmp.month<12 else 1
                a_tmp = d_tmp.year if d_tmp.month<12 else d_tmp.year+1
                d_tmp = date(a_tmp, m_tmp, 15)
                lst.append((f"{d_tmp.month:02d}/{d_tmp.year}", men))
            return lst

        ipca_table_ot = build_ipca_table(aa_to_list(ipca_ot_aa), vna_base, d_fech_vna)
        ipca_table_ne = build_ipca_table(aa_to_list(ipca_ne_aa), vna_base, d_fech_vna)
        ipca_table_pe = build_ipca_table(aa_to_list(ipca_pe_aa), vna_base, d_fech_vna)
        ipca_table_main = ipca_table_ne

    # VNA final display
    if ipca_table_main:
        ipca_p_main = calc_ipca_periodo(d_ini, d_fim, ipca_table_main)
        vna_fim_disp = _get_vna_na_data(d_fim, sorted(ipca_table_main, key=lambda x: x['data_fechamento']))
        st.markdown(f"""<div class='ibox'>
        IPCA acumulado no período: <b>{ipca_p_main*100:.3f}%</b> &nbsp;·&nbsp;
        VNA em {d_ini.strftime('%d/%m/%Y')}: <b>{_get_vna_na_data(d_ini, sorted(ipca_table_main, key=lambda x: x['data_fechamento'])):.4f}</b> &nbsp;·&nbsp;
        VNA em {d_fim.strftime('%d/%m/%Y')}: <b>{vna_fim_disp:.4f}</b>
        </div>""", unsafe_allow_html=True)
    else:
        ipca_p_main = 0.025

    st.markdown("---")

    # ── Selic / COPOM ──
    st.markdown("<div class='sec'>💰 Selic & COPOM</div>", unsafe_allow_html=True)
    modo_selic = st.radio("Projeção Selic", ["Focus (automático)", "Manual"], horizontal=True)

    if modo_selic == "Focus (automático)" and focus.get('selic_copom'):
        copom_sched_focus = build_copom_schedule_from_focus(
            focus['selic_copom'], selic_ini, d_ini, d_fim)
        copom_sched_c1 = copom_sched_focus
        copom_sched_c2 = copom_sched_focus
        copom_sched_c3 = copom_sched_focus
        if copom_sched_focus:
            reunioes_str = ", ".join([f"{c['reuniao']}→{c['nova_taxa']:.2f}%" for c in copom_sched_focus])
            st.markdown(f"<div class='ibox'>COPOM no período: {reunioes_str}</div>",
                        unsafe_allow_html=True)
    else:
        # Manual — mostrar reuniões no período
        reunioes_periodo = [c for c in COPOM_CALENDARIO if d_ini <= c['data'] <= d_fim]
        if reunioes_periodo:
            st.markdown("**Reuniões do COPOM no período (defina a nova Selic):**")
            cols_cop = st.columns(min(len(reunioes_periodo), 5))
            projecoes_manual = {}
            taxa_acum = selic_ini
            for i, reuniao in enumerate(reunioes_periodo):
                with cols_cop[i % 5]:
                    nova = st.number_input(
                        reuniao['reuniao'],
                        value=max(10.0, taxa_acum - 0.25),
                        step=0.25, format="%.2f",
                        key=f"cop_{reuniao['reuniao']}")
                    projecoes_manual[reuniao['reuniao']] = nova
                    taxa_acum = nova
            copom_sched_c1 = copom_sched_c2 = copom_sched_c3 = \
                build_copom_schedule_manual(projecoes_manual, d_ini, d_fim)
        else:
            copom_sched_c1 = copom_sched_c2 = copom_sched_c3 = []
            st.info("Nenhuma reunião do COPOM na janela selecionada.")

    def calc_cdi(schedule, du):
        if schedule:
            return cdi_retorno_com_copom(selic_ini, schedule, d_ini, d_fim)
        return cdi_retorno_simples(selic_ini, du)

    st.markdown("---")

    # ── Cenários de yield ──
    st.markdown("<div class='sec'>🎬 Cenários de Curva</div>", unsafe_allow_html=True)
    st.markdown("""<div class='ibox'>
    Defina a variação de yield para cada cenário em pontos base (bps).<br>
    Negativo = fechamento (queda de juros reais) → marcação positiva.<br>
    Positivo = abertura (alta de juros reais) → marcação negativa.
    </div>""", unsafe_allow_html=True)

    col_c1, col_c2, col_c3 = st.columns(3)

    with col_c1:
        st.markdown("<span class='b-green'>🟢 Cenário 1 — Fechamento</span>",
                    unsafe_allow_html=True)
        vb5_c1  = st.number_input("Δ IMA-B5 (bps)", value=-80, step=5, key="c1b5")
        vb5p_c1 = st.number_input("Δ IMA-B5+ (bps)", value=-23, step=5, key="c1b5p")

    with col_c2:
        st.markdown("<span class='b-yellow'>🟡 Cenário 2 — Manutenção</span>",
                    unsafe_allow_html=True)
        vb5_c2  = st.number_input("Δ IMA-B5 (bps)", value=0, step=5, key="c2b5")
        vb5p_c2 = st.number_input("Δ IMA-B5+ (bps)", value=0, step=5, key="c2b5p")

    with col_c3:
        st.markdown("<span class='b-red'>🔴 Cenário 3 — Abertura</span>",
                    unsafe_allow_html=True)
        vb5_c3  = st.number_input("Δ IMA-B5 (bps)", value=73, step=5, key="c3b5")
        vb5p_c3 = st.number_input("Δ IMA-B5+ (bps)", value=50, step=5, key="c3b5p")

    # IPCA por cenário
    if modo_ipca == "Cenários IPCA":
        ipca_c = [calc_ipca_periodo(d_ini, d_fim, ipca_table_ot),
                  calc_ipca_periodo(d_ini, d_fim, ipca_table_ne),
                  calc_ipca_periodo(d_ini, d_fim, ipca_table_pe)]
    else:
        ip = calc_ipca_periodo(d_ini, d_fim, ipca_table_main) if ipca_table_main else 0.025
        ipca_c = [ip, ip, ip]

    # ── Cálculo ──
    def calc_cen(vb5_bps, vb5p_bps, ipca_p, sched):
        b5  = imab5_retorno_total(yield_b5,  du_total, vb5_bps,  dur_b5,  ipca_p)
        b5p = imab5_retorno_total(yield_b5p, du_total, vb5p_bps, dur_b5p, ipca_p)
        cdi = calc_cdi(sched, du_total)
        return b5, b5p, cdi

    r1 = calc_cen(vb5_c1, vb5p_c1, ipca_c[0], copom_sched_c1)
    r2 = calc_cen(vb5_c2, vb5p_c2, ipca_c[1], copom_sched_c2)
    r3 = calc_cen(vb5_c3, vb5p_c3, ipca_c[2], copom_sched_c3)

    cenarios_calc = [
        ("🟢 Fechamento",  r1, ipca_c[0], vb5_c1, vb5p_c1),
        ("🟡 Manutenção",  r2, ipca_c[1], vb5_c2, vb5p_c2),
        ("🔴 Abertura",    r3, ipca_c[2], vb5_c3, vb5p_c3),
    ]

    st.markdown("---")
    st.markdown("<div class='sec'>📊 Resultados por Cenário</div>", unsafe_allow_html=True)

    for label, (b5, b5p, cdi), ipca_p, db5_bps, db5p_bps in cenarios_calc:
        valores = {'IMA-B 5': b5['retorno_total'],
                   'IMA-B 5+': b5p['retorno_total'],
                   'CDI': cdi}
        vencedor = max(valores, key=valores.get)
        vencedor_val = valores[vencedor]

        st.markdown(
            f"#### {label} &nbsp; "
            f"<span class='winner'>🏆 {vencedor}: {vencedor_val*100:.2f}%</span>",
            unsafe_allow_html=True)

        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        delta_b5 = b5['retorno_total'] - cdi
        delta_b5p = b5p['retorno_total'] - cdi

        mc1.metric("IMA-B 5", f"{b5['retorno_total']*100:.2f}%",
                   f"{delta_b5*100:+.2f}pp vs CDI")
        mc2.metric("IMA-B 5+", f"{b5p['retorno_total']*100:.2f}%",
                   f"{delta_b5p*100:+.2f}pp vs CDI")
        mc3.metric("CDI", f"{cdi*100:.2f}%")
        mc4.metric("IPCA Período", f"{ipca_p*100:.3f}%")
        real_b5 = (1 + b5['retorno_total']) / (1 + ipca_p) - 1
        mc5.metric("IMA-B5 Real", f"{real_b5*100:.2f}%")

        with st.expander("🔍 Decomposição"):
            dc1, dc2, dc3 = st.columns(3)
            with dc1:
                st.markdown("**IMA-B 5**")
                st.write(f"• Carrego: {b5['carrego']*100:.3f}%")
                st.write(f"• Marcação: {b5['marcacao']*100:+.3f}%  ({db5_bps:+d} bps)")
                st.write(f"• Retorno real: {b5['retorno_real']*100:.3f}%")
                st.write(f"• Yield final: {b5['yield_final']:.4f}% a.a.")
            with dc2:
                st.markdown("**IMA-B 5+**")
                st.write(f"• Carrego: {b5p['carrego']*100:.3f}%")
                st.write(f"• Marcação: {b5p['marcacao']*100:+.3f}%  ({db5p_bps:+d} bps)")
                st.write(f"• Retorno real: {b5p['retorno_real']*100:.3f}%")
                st.write(f"• Yield final: {b5p['yield_final']:.4f}% a.a.")
            with dc3:
                st.markdown("**CDI (com COPOM)**")
                sched_disp = copom_sched_c1 if label.startswith("🟢") else (
                    copom_sched_c2 if label.startswith("🟡") else copom_sched_c3)
                if sched_disp:
                    for c in sched_disp:
                        st.write(f"• {c['reuniao']}: → {c['nova_taxa']:.2f}%")
                else:
                    st.write(f"• Selic fixa: {selic_ini:.2f}%")
                st.write(f"• Retorno CDI: {cdi*100:.3f}%")

    # ── Gráfico comparativo ──
    st.markdown("---")
    st.markdown("<div class='sec'>📉 Gráficos</div>", unsafe_allow_html=True)

    labels_graf = ["🟢 Fechamento", "🟡 Manutenção", "🔴 Abertura"]
    cores = {'IMA-B 5': '#4fc3a1', 'IMA-B 5+': '#60a5fa', 'CDI': '#fbbf24'}

    fig = go.Figure()
    for idx, cor in cores.items():
        ys = []
        for _, (b5, b5p, cdi), _, _, _ in cenarios_calc:
            v = b5['retorno_total'] if idx == 'IMA-B 5' else (
                b5p['retorno_total'] if idx == 'IMA-B 5+' else cdi)
            ys.append(v * 100)
        fig.add_trace(go.Bar(name=idx, x=labels_graf, y=ys, marker_color=cor,
                             text=[f"{v:.2f}%" for v in ys], textposition='outside'))

    # Linha IPCA
    fig.add_trace(go.Scatter(
        name='IPCA', x=labels_graf, y=[c[2]*100 for c in cenarios_calc],
        mode='lines+markers',
        marker=dict(symbol='diamond', size=9, color='#f87171'),
        line=dict(color='#f87171', dash='dot', width=1.5)))

    fig.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)', barmode='group', height=400,
        legend=dict(orientation='h', y=1.08, x=1, xanchor='right'),
        yaxis=dict(ticksuffix='%', gridcolor='#1e2738'),
        title=dict(text=f"Retorno Total — {du_total} d.u. ({d_ini:%d/%m/%Y} → {d_fim:%d/%m/%Y})",
                   font=dict(color='#c8d8f0', size=13)),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Gráfico retorno real
    fig2 = go.Figure()
    for idx, cor in cores.items():
        ys_real = []
        for _, (b5, b5p, cdi), ipca_p, _, _ in cenarios_calc:
            nom = b5['retorno_total'] if idx == 'IMA-B 5' else (
                b5p['retorno_total'] if idx == 'IMA-B 5+' else cdi)
            ys_real.append(((1+nom)/(1+ipca_p)-1)*100)
        fig2.add_trace(go.Bar(name=f"{idx} (real)", x=labels_graf, y=ys_real,
                              marker_color=cor, opacity=0.8,
                              text=[f"{v:.2f}%" for v in ys_real], textposition='outside'))

    fig2.add_hline(y=0, line=dict(color='#4a5568', width=1))
    fig2.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)', barmode='group', height=360,
        legend=dict(orientation='h', y=1.08, x=1, xanchor='right'),
        yaxis=dict(ticksuffix='%', gridcolor='#1e2738'),
        title=dict(text="Retorno Real (descontado IPCA)", font=dict(color='#c8d8f0', size=13)),
    )
    st.plotly_chart(fig2, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — PROJEÇÃO MÊS A MÊS
# ════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("<div class='sec'>📅 Projeção Mês a Mês — IMA-B 5 × IMA-B 5+ × CDI</div>",
                unsafe_allow_html=True)
    st.markdown("""<div class='ibox'>
    Retorno mensal esperado de cada índice. Metodologia idêntica à aba
    <b>IMA MÊS A MÊS</b> e <b>Projeção IMA VS CDI MaM</b> da planilha de referência.
    O IPCA de cada mês é calculado via VNA pro-rata (metodologia ANBIMA).
    </div>""", unsafe_allow_html=True)

    col_mam1, col_mam2 = st.columns([1, 2])
    with col_mam1:
        var_mam_sel = st.selectbox("Variação de curva (marcação mensal)", [
            "Manutenção (0 bps)", "Fechamento (−20 bps)", "Fechamento Forte (−50 bps)",
            "Alta (+20 bps)", "Alta Forte (+50 bps)", "Personalizado",
        ])
        var_map = {"Manutenção (0 bps)": 0, "Fechamento (−20 bps)": -20,
                   "Fechamento Forte (−50 bps)": -50, "Alta (+20 bps)": 20,
                   "Alta Forte (+50 bps)": 50}
        if var_mam_sel == "Personalizado":
            var_mam_bps = st.number_input("bps por mês", value=0, step=5)
        else:
            var_mam_bps = var_map.get(var_mam_sel, 0)

    with col_mam2:
        usar_focus_mam = st.checkbox(
            "Usar IPCA do Focus para cada mês", value=bool(ipca_table_main))

    # Usa ipca_table_main (já configurada na aba 1)
    ipca_tab_mam = ipca_table_main if (usar_focus_mam and ipca_table_main) else ipca_table_main

    def build_mam(d_start, d_end, yield_b5_, dur_b5_, yield_b5p_, dur_b5p_,
                  selic_, var_bps, ipca_tab):
        rows = []
        cur = date(d_start.year, d_start.month, 1)
        while not is_business_day(cur):
            cur += timedelta(days=1)

        while cur < d_end:
            # Fim do mês corrente
            if cur.month == 12:
                prox_mes = date(cur.year + 1, 1, 1)
            else:
                prox_mes = date(cur.year, cur.month + 1, 1)
            fim = prox_mes - timedelta(days=1)
            fim = min(fim, d_end)
            while fim > cur and not is_business_day(fim):
                fim -= timedelta(days=1)
            if fim <= cur:
                cur = prox_mes
                while not is_business_day(cur) and cur <= d_end:
                    cur += timedelta(days=1)
                continue

            du_m = count_business_days(cur, fim)
            if du_m <= 0:
                cur = prox_mes
                continue

            ipca_m = calc_ipca_periodo(cur, fim, ipca_tab) if ipca_tab else 0.003
            b5  = imab5_retorno_total(yield_b5_,  du_m, var_bps, dur_b5_,  ipca_m)
            b5p = imab5_retorno_total(yield_b5p_, du_m, var_bps, dur_b5p_, ipca_m)
            cdi_m = cdi_retorno_simples(selic_, du_m)

            melhor = max([('IMA-B5', b5['retorno_total']),
                          ('IMA-B5+', b5p['retorno_total']),
                          ('CDI', cdi_m)], key=lambda x: x[1])[0]

            rows.append({'Mês': cur.strftime('%b/%Y'), 'Início': cur, 'Fim': fim,
                         'D.U.': du_m, 'IPCA (%)': ipca_m*100,
                         'IMA-B5 (%)': b5['retorno_total']*100,
                         'IMA-B5+ (%)': b5p['retorno_total']*100,
                         'CDI (%)': cdi_m*100,
                         'IMA-B5 Carrego': b5['carrego']*100,
                         'IMA-B5 Marcação': b5['marcacao']*100,
                         'IMA-B5 vs CDI (pp)': (b5['retorno_total']-cdi_m)*100,
                         'Melhor': melhor})

            cur = prox_mes
            while not is_business_day(cur) and cur <= d_end:
                cur += timedelta(days=1)
        return pd.DataFrame(rows)

    df_mam = build_mam(d_ini, d_fim, yield_b5, dur_b5, yield_b5p, dur_b5p,
                       selic_ini, var_mam_bps, ipca_tab_mam)

    if not df_mam.empty:
        fig_mam = go.Figure()
        for nome, cor, col in [('IMA-B5','#4fc3a1','IMA-B5 (%)'),
                                 ('IMA-B5+','#60a5fa','IMA-B5+ (%)'),
                                 ('CDI','#fbbf24','CDI (%)')]:
            fig_mam.add_trace(go.Bar(name=nome, x=df_mam['Mês'], y=df_mam[col],
                                     marker_color=cor, opacity=0.85))
        fig_mam.add_trace(go.Scatter(name='IPCA', x=df_mam['Mês'], y=df_mam['IPCA (%)'],
                                     mode='lines+markers',
                                     marker=dict(symbol='diamond', size=7, color='#f87171'),
                                     line=dict(color='#f87171', dash='dot', width=1.5)))
        fig_mam.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)', barmode='group', height=380,
            legend=dict(orientation='h', y=1.08, x=1, xanchor='right'),
            yaxis=dict(ticksuffix='%', gridcolor='#1e2738'),
            xaxis=dict(gridcolor='#1e2738', tickangle=-30),
            title=dict(text=f"Retorno Mensal ({var_mam_sel})",
                       font=dict(color='#c8d8f0', size=13)),
        )
        st.plotly_chart(fig_mam, use_container_width=True)

        # Acumulado
        df_mam['B5 Acum'] = (1 + df_mam['IMA-B5 (%)']/100).cumprod() - 1
        df_mam['B5P Acum'] = (1 + df_mam['IMA-B5+ (%)']/100).cumprod() - 1
        df_mam['CDI Acum'] = (1 + df_mam['CDI (%)']/100).cumprod() - 1

        fig_ac = go.Figure()
        fig_ac.add_trace(go.Scatter(name='IMA-B5', x=df_mam['Mês'], y=df_mam['B5 Acum']*100,
                                    line=dict(color='#4fc3a1', width=2.5),
                                    fill='tozeroy', fillcolor='rgba(79,195,161,.05)'))
        fig_ac.add_trace(go.Scatter(name='IMA-B5+', x=df_mam['Mês'], y=df_mam['B5P Acum']*100,
                                    line=dict(color='#60a5fa', width=2, dash='dash')))
        fig_ac.add_trace(go.Scatter(name='CDI', x=df_mam['Mês'], y=df_mam['CDI Acum']*100,
                                    line=dict(color='#fbbf24', width=2)))
        fig_ac.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)', height=340,
            legend=dict(orientation='h', y=1.08, x=1, xanchor='right'),
            yaxis=dict(ticksuffix='%', gridcolor='#1e2738'),
            xaxis=dict(gridcolor='#1e2738', tickangle=-30),
            title=dict(text="Retorno Acumulado", font=dict(color='#c8d8f0', size=13)),
        )
        st.plotly_chart(fig_ac, use_container_width=True)

        # Tabela + resumo
        st.dataframe(
            df_mam[['Mês','D.U.','IPCA (%)','IMA-B5 (%)','IMA-B5+ (%)','CDI (%)','IMA-B5 vs CDI (pp)','Melhor']].style.format({
                'IPCA (%)': '{:.3f}%', 'IMA-B5 (%)': '{:.3f}%',
                'IMA-B5+ (%)': '{:.3f}%', 'CDI (%)': '{:.3f}%',
                'IMA-B5 vs CDI (pp)': '{:+.3f}',
            }), use_container_width=True, height=320)

        r1c, r2c, r3c = st.columns(3)
        ac_b5  = (1+df_mam['IMA-B5 (%)']/100).prod()-1
        ac_cdi = (1+df_mam['CDI (%)']/100).prod()-1
        sp = ac_b5 - ac_cdi
        r1c.metric("IMA-B5 Acumulado", f"{ac_b5*100:.2f}%")
        r2c.metric("CDI Acumulado", f"{ac_cdi*100:.2f}%")
        r3c.metric("Spread IMA-B5 vs CDI", f"{sp*100:+.2f}%",
                   delta="IMA-B5 vence" if sp > 0 else "CDI vence")


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — CURVAS DE JUROS (ETTJ)
# ════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("<div class='sec'>📉 ETTJ — Curvas de Juros Semana vs Semana</div>",
                unsafe_allow_html=True)
    st.markdown("""<div class='ibox'>
    Curvas de juros pré (LTN/NTN-F) e real (NTN-B / ETTJ Juro Real) da ANBIMA,
    comparadas entre a semana atual e a semana anterior. Apresentação convencional:
    eixo X = prazo/vencimento, eixo Y = taxa (% a.a.).
    </div>""", unsafe_allow_html=True)

    col_d1, col_d2, col_tc = st.columns(3)
    with col_d1:
        hoje_ref = date.today() - timedelta(days=1 if date.today().weekday() == 0 else 0)
        d_atual_c = st.date_input("Data atual", value=hoje_ref, key="dc1")
    with col_d2:
        d_ant_c = st.date_input("Semana anterior", value=d_atual_c - timedelta(days=7), key="dc2")
    with col_tc:
        tipo_c = st.selectbox("Tipo de curva", ["Juro Real (NTN-B)", "Pré (LTN/NTN-F)", "Ambas"])

    col_btn, col_manual = st.columns([1, 3])
    with col_btn:
        btn_ettj = st.button("🔄 Buscar ANBIMA", use_container_width=True)
    with col_manual:
        usar_manual = st.checkbox("Usar entrada manual (recomendado)", value=True,
                                   help="A ANBIMA frequentemente requer autenticação. Entrada manual é mais confiável.")

    # ── Entrada manual ──
    venc_padrao = get_vencimentos_ntnb_padrao()

    with st.expander("📝 Entrada Manual de Curva", expanded=usar_manual):
        st.markdown("**Juro Real (NTN-B)** — Vencimentos e yields (% a.a.):")

        # Default: yield atual do IMA-B5 como ponto ancoragem
        y_def_atual = [yield_b5 - 0.02, yield_b5 + 0.01, yield_b5 + 0.04,
                       yield_b5 + 0.07, yield_b5 + 0.10, yield_b5 + 0.13,
                       yield_b5 + 0.16, yield_b5 + 0.19, yield_b5 + 0.21]
        y_def_ant   = [y - 0.20 for y in y_def_atual]

        cols_venc = st.columns(len(venc_padrao))
        yields_real_atual, yields_real_ant = [], []
        for i, (venc, ya, yaa) in enumerate(zip(venc_padrao, y_def_atual, y_def_ant)):
            with cols_venc[i]:
                st.markdown(f"<div style='text-align:center;color:#94a3b8;font-size:.75rem'><b>{venc}</b></div>",
                            unsafe_allow_html=True)
                va = st.number_input(f"Atual_{venc}", value=round(ya,4), step=0.01,
                                     format="%.4f", key=f"vra_{venc}", label_visibility="collapsed")
                vaa = st.number_input(f"Ant_{venc}", value=round(yaa,4), step=0.01,
                                      format="%.4f", key=f"vraa_{venc}", label_visibility="collapsed")
                yields_real_atual.append(va)
                yields_real_ant.append(vaa)

        st.markdown("**Pré (LTN/NTN-F)** — Vértices padrão ANBIMA (dias úteis → taxa):")
        vert_pre = [21, 63, 126, 252, 504, 756, 1008, 1260, 1764, 2520]
        # Defaults baseados em prêmio típico sobre CDI
        base_pre = selic_ini
        y_pre_def_a   = [base_pre - 0.5 + i*0.12 for i in range(len(vert_pre))]
        y_pre_def_aa  = [y - 0.25 for y in y_pre_def_a]

        col_pre_labels = st.columns(len(vert_pre))
        yields_pre_atual, yields_pre_ant = [], []
        for i, (vert, ya, yaa) in enumerate(zip(vert_pre, y_pre_def_a, y_pre_def_aa)):
            with col_pre_labels[i]:
                anos = round(vert/252, 1)
                st.markdown(f"<div style='text-align:center;color:#94a3b8;font-size:.72rem'><b>{anos}a</b></div>",
                            unsafe_allow_html=True)
                va = st.number_input(f"PrA_{vert}", value=round(ya,2), step=0.01,
                                     format="%.2f", key=f"pra_{vert}", label_visibility="collapsed")
                vaa = st.number_input(f"PrAa_{vert}", value=round(yaa,2), step=0.01,
                                      format="%.2f", key=f"praa_{vert}", label_visibility="collapsed")
                yields_pre_atual.append(va)
                yields_pre_ant.append(vaa)

    # Tenta API se solicitado
    ettj_atual_api = {'pre': [], 'real': [], 'ok': False}
    ettj_ant_api   = {'pre': [], 'real': [], 'ok': False}
    if btn_ettj and not usar_manual:
        with st.spinner("Buscando ANBIMA..."):
            ettj_atual_api = load_ettj(d_atual_c.isoformat())
            ettj_ant_api   = load_ettj(d_ant_c.isoformat())
        if not ettj_atual_api['ok']:
            st.warning("API ANBIMA indisponível. Usando entrada manual.")
            usar_manual = True

    # ── Monta DataFrames ──
    if usar_manual or not ettj_atual_api['ok']:
        df_real_atual = pd.DataFrame({'venc': venc_padrao, 'taxa': yields_real_atual,
                                       'prazo': [v - d_atual_c.year + 0.5 for v in venc_padrao]})
        df_real_ant   = pd.DataFrame({'venc': venc_padrao, 'taxa': yields_real_ant,
                                       'prazo': [v - d_ant_c.year + 0.5 for v in venc_padrao]})
        df_pre_atual  = pd.DataFrame({'prazo': [v/252 for v in vert_pre], 'taxa': yields_pre_atual})
        df_pre_ant    = pd.DataFrame({'prazo': [v/252 for v in vert_pre], 'taxa': yields_pre_ant})
    else:
        def api_to_df(rows):
            return pd.DataFrame(rows) if rows else pd.DataFrame()
        df_real_atual = api_to_df(ettj_atual_api.get('real', []))
        df_real_ant   = api_to_df(ettj_ant_api.get('real', []))
        df_pre_atual  = api_to_df(ettj_atual_api.get('pre', []))
        df_pre_ant    = api_to_df(ettj_ant_api.get('pre', []))

    # ── Gráfico curvas ──
    def plot_curva(df_atual, df_ant, x_col, y_col, titulo, label_x,
                   d_at_lbl, d_an_lbl, linha_ancoragem=None):
        fig = go.Figure()
        if not df_atual.empty:
            fig.add_trace(go.Scatter(
                name=f"Atual ({d_at_lbl})", x=df_atual[x_col], y=df_atual[y_col],
                mode='lines+markers', line=dict(color='#4fc3a1', width=2.5),
                marker=dict(size=7), fill='tozeroy', fillcolor='rgba(79,195,161,.04)'))
        if not df_ant.empty:
            fig.add_trace(go.Scatter(
                name=f"Semana ant. ({d_an_lbl})", x=df_ant[x_col], y=df_ant[y_col],
                mode='lines+markers', line=dict(color='#60a5fa', width=2, dash='dash'),
                marker=dict(size=6, symbol='square')))
        if linha_ancoragem:
            fig.add_hline(y=linha_ancoragem[0],
                          line=dict(color='#fbbf24', width=1.2, dash='dot'),
                          annotation_text=linha_ancoragem[1],
                          annotation_font_color='#fbbf24')
        fig.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)', height=420,
            xaxis=dict(title=label_x, gridcolor='#1e2738', tickangle=-30),
            yaxis=dict(title='Taxa (% a.a.)', ticksuffix='%', gridcolor='#1e2738'),
            legend=dict(orientation='h', y=1.08, x=1, xanchor='right'),
            hovermode='x unified',
            title=dict(text=titulo, font=dict(color='#c8d8f0', size=13)))
        return fig

    mostrar_real = tipo_c in ["Juro Real (NTN-B)", "Ambas"]
    mostrar_pre  = tipo_c in ["Pré (LTN/NTN-F)", "Ambas"]

    if mostrar_real and not df_real_atual.empty:
        x_col = 'venc' if 'venc' in df_real_atual.columns else 'prazo_anos'
        fig_real = plot_curva(df_real_atual, df_real_ant, x_col, 'taxa',
                               "ETTJ Juro Real — NTN-B", "Vencimento",
                               d_atual_c.strftime('%d/%m/%Y'), d_ant_c.strftime('%d/%m/%Y'),
                               (yield_b5, f"IMA-B5 atual: {yield_b5:.4f}%"))
        st.plotly_chart(fig_real, use_container_width=True)

    if mostrar_pre and not df_pre_atual.empty:
        x_col_pre = 'prazo' if 'prazo' in df_pre_atual.columns else 'prazo_anos'
        fig_pre = plot_curva(df_pre_atual, df_pre_ant, x_col_pre, 'taxa',
                              "ETTJ Pré — LTN / NTN-F", "Prazo (anos)",
                              d_atual_c.strftime('%d/%m/%Y'), d_ant_c.strftime('%d/%m/%Y'))
        st.plotly_chart(fig_pre, use_container_width=True)

    # ── Variação da curva ──
    if mostrar_real and not df_real_atual.empty and not df_real_ant.empty:
        st.markdown("**📊 Variação Semanal da Curva Real (bps)**")
        n = min(len(df_real_atual), len(df_real_ant))
        delta_vals = [(df_real_atual['taxa'].iloc[i] - df_real_ant['taxa'].iloc[i]) * 100
                      for i in range(n)]
        xv = df_real_atual[('venc' if 'venc' in df_real_atual.columns else 'prazo_anos')].values[:n]

        fig_delt = go.Figure(go.Bar(
            x=xv, y=delta_vals,
            marker_color=['#f87171' if v > 0 else '#4fc3a1' for v in delta_vals],
            text=[f"{v:+.1f}" for v in delta_vals], textposition='outside'))
        fig_delt.add_hline(y=0, line=dict(color='#4a5568', width=1))
        fig_delt.update_layout(
            template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)', height=280, showlegend=False,
            yaxis=dict(title='Δ (bps)', gridcolor='#1e2738'),
            title=dict(text="Variação Semanal por Vencimento (bps)",
                       font=dict(color='#c8d8f0', size=12)))
        st.plotly_chart(fig_delt, use_container_width=True)

    # ── Histórico Redemption Yield ──
    st.markdown("---")
    with st.expander("📈 Histórico Redemption Yield IMA-B 5 (cole ou carregue CSV)"):
        hist_csv = st.text_area("data,yield (uma linha por data — ex: 2026-04-10,7.7519)",
                                height=120, placeholder="2026-01-02,7.55\n2026-02-03,7.58\n...")
        upload_hist = st.file_uploader("Ou carregue CSV", type=['csv'], key="hist_upload")

        hist_rows = []
        if upload_hist:
            content = upload_hist.read().decode('utf-8')
            reader = csv.reader(io.StringIO(content))
            for row in reader:
                try:
                    hist_rows.append({'data': date.fromisoformat(row[0].strip()),
                                      'yield': float(row[1].strip())})
                except Exception:
                    continue
        elif hist_csv.strip():
            for linha in hist_csv.strip().split('\n'):
                try:
                    p = linha.split(',')
                    hist_rows.append({'data': date.fromisoformat(p[0].strip()),
                                      'yield': float(p[1].strip())})
                except Exception:
                    continue
        else:
            # Defaults
            defaults_hist = {"2023-06-30": 5.72, "2023-09-29": 5.87, "2023-12-29": 5.89,
                             "2024-03-28": 5.97, "2024-06-28": 6.10, "2024-09-30": 6.35,
                             "2024-12-31": 7.20, "2025-03-31": 7.45, "2025-06-30": 7.60,
                             "2025-09-30": 7.68, "2025-12-31": 7.72, "2026-01-30": 7.75,
                             "2026-02-27": 7.75, "2026-03-31": 7.75, "2026-04-10": 7.7519}
            hist_rows = [{'data': date.fromisoformat(k), 'yield': v}
                         for k, v in defaults_hist.items()]

        if hist_rows:
            df_hist = pd.DataFrame(sorted(hist_rows, key=lambda x: x['data']))
            media_h = df_hist['yield'].mean()
            dp_h    = df_hist['yield'].std()
            fig_h = go.Figure()
            fig_h.add_trace(go.Scatter(x=df_hist['data'], y=df_hist['yield'],
                                       name='Yield IMA-B5',
                                       line=dict(color='#4fc3a1', width=2),
                                       fill='tozeroy', fillcolor='rgba(79,195,161,.05)'))
            for nivel, cor, lbl in [(media_h, '#60a5fa', f'Média {media_h:.2f}%'),
                                     (media_h+dp_h, '#fbbf24', f'+1σ {media_h+dp_h:.2f}%'),
                                     (media_h-dp_h, '#fbbf24', f'-1σ {media_h-dp_h:.2f}%'),
                                     (yield_b5, '#f87171', f'Atual {yield_b5:.4f}%')]:
                fig_h.add_hline(y=nivel, line=dict(color=cor, width=1.2, dash='dot'),
                                annotation_text=lbl, annotation_font_color=cor)
            fig_h.update_layout(
                template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)', height=360,
                yaxis=dict(ticksuffix='%', gridcolor='#1e2738'),
                title=dict(text='Histórico Yield Real IMA-B 5',
                           font=dict(color='#c8d8f0', size=13)))
            st.plotly_chart(fig_h, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — SIMULAÇÃO DE ALOCAÇÃO
# ════════════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown("<div class='sec'>💼 Simulação de Alocação — Carteira RF</div>",
                unsafe_allow_html=True)
    st.markdown("""<div class='ibox'>
    Análise de retorno e volatilidade esperados da carteira de renda fixa,
    com fundos <b>SAFRA FF RF IMAB 5</b> e <b>SF FF CAIXA FI RF DI</b>.
    Simula o impacto de realocações nos três cenários de mercado.
    </div>""", unsafe_allow_html=True)

    # ── Totais do plano ──
    col_tot1, col_tot2 = st.columns(2)
    with col_tot1:
        total_rf_plano = st.number_input("Total RF do Plano (R$)",
                                          value=788_101_113.52, step=1e6, format="%.2f")
    with col_tot2:
        total_pl_plano = st.number_input("Total PL do Plano B (R$)",
                                          value=15_391_694_217.47, step=10e6, format="%.2f")

    # ── Fundos ──
    st.markdown("---")
    col_f1, col_f2 = st.columns(2)

    with col_f1:
        st.markdown("### 🟢 SAFRA FF RF IMAB 5")
        val_imab5 = st.number_input("Patrimônio Líquido (R$)", value=427_117_255.03,
                                     step=1e6, format="%.2f", key="vimab5")
        vol_imab5 = st.number_input("Volatilidade histórica (%)", value=1.0620,
                                     step=0.01, format="%.4f", key="volimab5")

    with col_f2:
        st.markdown("### 🟡 SF FF CAIXA FI RF DI")
        val_cdi_f = st.number_input("Patrimônio Líquido (R$)", value=1_206_960_782.31,
                                     step=1e6, format="%.2f", key="vcdi")
        vol_cdi_f = st.number_input("Volatilidade histórica (%)", value=0.0,
                                     step=0.01, format="%.4f", key="volcdi")

    total_cart = val_imab5 + val_cdi_f
    pct_imab5_at = val_imab5 / total_cart if total_cart > 0 else 0
    pct_cdi_at   = val_cdi_f / total_cart if total_cart > 0 else 0

    # Participação no plano
    st.markdown("---")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("SAFRA IMAB 5", fmt_brl_short(val_imab5),
               f"{pct_imab5_at*100:.1f}% da carteira RF")
    mc2.metric("SF CAIXA DI", fmt_brl_short(val_cdi_f),
               f"{pct_cdi_at*100:.1f}% da carteira RF")
    mc3.metric("% Total RF do Plano",
               f"{(total_cart/total_rf_plano*100):.1f}%" if total_rf_plano > 0 else "—")
    mc4.metric("% PL Total do Plano",
               f"{(total_cart/total_pl_plano*100):.2f}%" if total_pl_plano > 0 else "—")

    # ── Movimentação ──
    st.markdown("---")
    st.markdown("### 🔄 Simulação de Movimentação")
    col_mv1, col_mv2 = st.columns(2)
    with col_mv1:
        mov_imab5 = st.number_input("Movimentação SAFRA IMAB 5 (R$)",
                                     value=50_000_000.0, step=5e6, format="%.2f",
                                     help="+= aporte; -= resgate")
    with col_mv2:
        mov_cdi_f = -mov_imab5
        st.metric("Movimentação SF CAIXA DI (R$)", fmt_brl_short(mov_cdi_f),
                  help="Compensatório automático")

    val_imab5_pos = max(0, val_imab5 + mov_imab5)
    val_cdi_pos   = max(0, val_cdi_f + mov_cdi_f)
    total_pos = val_imab5_pos + val_cdi_pos
    pct_imab5_pos = val_imab5_pos / total_pos if total_pos > 0 else 0
    pct_cdi_pos   = val_cdi_pos   / total_pos if total_pos > 0 else 0

    st.markdown("**Posição após movimentação:**")
    pp1, pp2, pp3 = st.columns(3)
    dp1 = (pct_imab5_pos - pct_imab5_at) * 100
    dp2 = (pct_cdi_pos   - pct_cdi_at)   * 100
    pp1.metric("SAFRA IMAB 5", fmt_brl_short(val_imab5_pos),
               f"{pct_imab5_pos*100:.1f}% ({dp1:+.1f}pp)")
    pp2.metric("SF CAIXA DI", fmt_brl_short(val_cdi_pos),
               f"{pct_cdi_pos*100:.1f}% ({dp2:+.1f}pp)")
    pp3.metric("Total Carteira RF", fmt_brl_short(total_pos))

    # ── Retorno × Cenários ──
    st.markdown("---")
    st.markdown("### 📈 Retorno e Risco por Cenário")

    # Usa retornos calculados na aba 1
    rets_cen = {
        '🟢 Fechamento':  (r1[0]['retorno_total'], r1[2]),
        '🟡 Manutenção':  (r2[0]['retorno_total'], r2[2]),
        '🔴 Abertura':    (r3[0]['retorno_total'], r3[2]),
    }

    rows_aloc = []
    for lbl, (ret_b5, ret_cdi) in rets_cen.items():
        ret_at  = pct_imab5_at  * ret_b5 + pct_cdi_at  * ret_cdi
        ret_pos = pct_imab5_pos * ret_b5 + pct_cdi_pos * ret_cdi
        vol_at  = pct_imab5_at  * (vol_imab5 / 100)
        vol_pos = pct_imab5_pos * (vol_imab5 / 100)

        # Em R$ (sobre PL total do plano)
        ret_rl_at  = total_pl_plano * ret_at  * (total_cart / total_pl_plano)
        ret_rl_pos = total_pl_plano * ret_pos * (total_cart / total_pl_plano)

        rows_aloc.append({
            'Cenário': lbl,
            'Ret. Atual (%)':   ret_at  * 100,
            'Ret. Pós-Mov. (%)': ret_pos * 100,
            'Δ Ret. (pp)':      (ret_pos - ret_at) * 100,
            'Vol. Atual (%)':   vol_at  * 100,
            'Vol. Pós-Mov. (%)': vol_pos * 100,
            'R$ (Atual)':       val_imab5*ret_b5 + val_cdi_f*ret_cdi,
            'R$ (Pós-Mov.)':    val_imab5_pos*ret_b5 + val_cdi_pos*ret_cdi,
        })

    df_aloc = pd.DataFrame(rows_aloc)

    # Gráfico
    fig_aloc = go.Figure()
    fig_aloc.add_trace(go.Bar(name='Atual', x=df_aloc['Cenário'],
                               y=df_aloc['Ret. Atual (%)'], marker_color='#60a5fa',
                               text=[f"{v:.2f}%" for v in df_aloc['Ret. Atual (%)']],
                               textposition='outside'))
    fig_aloc.add_trace(go.Bar(name='Pós-Movimentação', x=df_aloc['Cenário'],
                               y=df_aloc['Ret. Pós-Mov. (%)'], marker_color='#4fc3a1',
                               text=[f"{v:.2f}%" for v in df_aloc['Ret. Pós-Mov. (%)']],
                               textposition='outside'))
    fig_aloc.update_layout(
        template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)', barmode='group', height=380,
        legend=dict(orientation='h', y=1.08, x=1, xanchor='right'),
        yaxis=dict(ticksuffix='%', gridcolor='#1e2738'),
        title=dict(text='Retorno Esperado da Carteira RF — Antes vs Depois da Movimentação',
                   font=dict(color='#c8d8f0', size=13)))
    st.plotly_chart(fig_aloc, use_container_width=True)

    # Tabela
    st.dataframe(df_aloc[['Cenário','Ret. Atual (%)','Ret. Pós-Mov. (%)','Δ Ret. (pp)',
                            'Vol. Atual (%)','Vol. Pós-Mov. (%)','R$ (Atual)','R$ (Pós-Mov.)']].style.format({
        'Ret. Atual (%)':    '{:.3f}%',
        'Ret. Pós-Mov. (%)': '{:.3f}%',
        'Δ Ret. (pp)':       '{:+.4f}',
        'Vol. Atual (%)':    '{:.3f}%',
        'Vol. Pós-Mov. (%)': '{:.3f}%',
        'R$ (Atual)':        'R$ {:,.0f}',
        'R$ (Pós-Mov.)':     'R$ {:,.0f}',
    }), use_container_width=True)

    # Gráficos de pizza
    col_pie1, col_pie2 = st.columns(2)
    for col_pie, vals, pcts, title_ in [
        (col_pie1, [val_imab5, val_cdi_f], [pct_imab5_at, pct_cdi_at], "Alocação Atual"),
        (col_pie2, [val_imab5_pos, val_cdi_pos], [pct_imab5_pos, pct_cdi_pos], "Pós-Movimentação"),
    ]:
        with col_pie:
            fig_pie = go.Figure(go.Pie(
                labels=['SAFRA IMAB 5', 'SF CAIXA DI'],
                values=vals, hole=0.52,
                marker_colors=['#4fc3a1', '#fbbf24'],
                textinfo='label+percent',
                textfont=dict(size=11),
            ))
            fig_pie.update_layout(
                template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
                title=dict(text=title_, font=dict(color='#c8d8f0', size=12)),
                height=280, showlegend=False,
                margin=dict(t=40, b=10, l=10, r=10),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # Resumo retorno real
    st.markdown("---")
    st.markdown("### 📊 Resumo — Retorno Nominal e Real da Carteira")
    res_cols = st.columns(3)
    for col_, lbl in zip(res_cols, rets_cen.keys()):
        ret_b5_v, ret_cdi_v = rets_cen[lbl]
        ret_nom = pct_imab5_at * ret_b5_v + pct_cdi_at * ret_cdi_v
        ipca_v = ipca_c[0] if "Fechamento" in lbl else (ipca_c[1] if "Manutenção" in lbl else ipca_c[2])
        ret_real = (1 + ret_nom) / (1 + ipca_v) - 1
        col_.metric(lbl, f"{ret_nom*100:.2f}% nominal", f"{ret_real*100:.2f}% real")

# ── Footer ──
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#2d3f55; font-size:.75rem; padding:10px 0;">
  📈 Dashboard IMA-B 5 × CDI · Metodologia ANBIMA · Focus/BCB · 
  Uso interno · Não constitui recomendação de investimento
</div>
""", unsafe_allow_html=True)
