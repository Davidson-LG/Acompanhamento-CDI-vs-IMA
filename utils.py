"""
Utilities: feriados ANBIMA, VNA/IPCA, CDI com COPOM, IMA-B5, Focus API, ETTJ.
Metodologia idêntica à planilha de referência (ANBIMA/VNA).
"""

import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime


# ──────────────────────────────────────────────────────────────────────────────
# FERIADOS ANBIMA
# ──────────────────────────────────────────────────────────────────────────────

FERIADOS_NACIONAIS = [
    "2024-01-01","2024-02-12","2024-02-13","2024-03-29","2024-04-21",
    "2024-05-01","2024-05-30","2024-09-07","2024-10-12","2024-11-02",
    "2024-11-15","2024-11-20","2024-12-25",
    "2025-01-01","2025-03-03","2025-03-04","2025-04-18","2025-04-21",
    "2025-05-01","2025-06-19","2025-09-07","2025-10-12","2025-11-02",
    "2025-11-15","2025-11-20","2025-12-25",
    "2026-01-01","2026-02-16","2026-02-17","2026-04-03","2026-04-21",
    "2026-05-01","2026-06-04","2026-09-07","2026-10-12","2026-11-02",
    "2026-11-15","2026-11-20","2026-12-25",
    "2027-01-01","2027-02-08","2027-02-09","2027-03-26","2027-04-21",
    "2027-05-01","2027-05-27","2027-09-07","2027-10-12","2027-11-02",
    "2027-11-15","2027-11-20","2027-12-25",
    "2028-01-01","2028-02-28","2028-02-29","2028-04-14","2028-04-21",
    "2028-05-01","2028-06-15","2028-09-07","2028-10-12","2028-11-02",
    "2028-11-15","2028-11-20","2028-12-25",
]

_feriados_set = {date.fromisoformat(d) for d in FERIADOS_NACIONAIS}


def is_business_day(d: date) -> bool:
    return d.weekday() < 5 and d not in _feriados_set


def count_business_days(start: date, end: date) -> int:
    count, cur = 0, start
    while cur < end:
        if is_business_day(cur):
            count += 1
        cur += timedelta(days=1)
    return count


def business_days_list(start: date, end: date) -> list:
    days, cur = [], start
    while cur <= end:
        if is_business_day(cur):
            days.append(cur)
        cur += timedelta(days=1)
    return days


def date_plus_du(start: date, du: int) -> date:
    count, d = 0, start
    while count < du:
        if is_business_day(d):
            count += 1
        if count < du:
            d += timedelta(days=1)
    return d


# ──────────────────────────────────────────────────────────────────────────────
# VNA / IPCA — METODOLOGIA ANBIMA (interpolação pro-rata dias corridos)
# ──────────────────────────────────────────────────────────────────────────────

def _get_vna_na_data(target: date, ipca_sorted: list) -> float:
    """
    VNA interpolado geometricamente (pro-rata dias corridos) para a data target.
    Metodologia ANBIMA: VNA(t) = VNA(ant) × (VNA(cur)/VNA(ant))^(dias_parciais/dias_total)
    """
    if not ipca_sorted:
        return 1000.0
    if target <= ipca_sorted[0]['data_fechamento']:
        return ipca_sorted[0]['vna']
    if target >= ipca_sorted[-1]['data_fechamento']:
        return ipca_sorted[-1]['vna']
    for i in range(1, len(ipca_sorted)):
        d_ant = ipca_sorted[i - 1]['data_fechamento']
        d_cur = ipca_sorted[i]['data_fechamento']
        if d_ant <= target < d_cur:
            dias_total = (d_cur - d_ant).days
            dias_parciais = (target - d_ant).days
            vna_ant = ipca_sorted[i - 1]['vna']
            vna_cur = ipca_sorted[i]['vna']
            if dias_total <= 0:
                return vna_ant
            fator = (vna_cur / vna_ant) ** (dias_parciais / dias_total)
            return vna_ant * fator
    return ipca_sorted[-1]['vna']


def calc_ipca_periodo(data_inicio: date, data_fim: date, ipca_table: list) -> float:
    """IPCA acumulado no período (decimal). Usa VNA interpolado ANBIMA."""
    if not ipca_table:
        return 0.0
    ipca_sorted = sorted(ipca_table, key=lambda x: x['data_fechamento'])
    vna_i = _get_vna_na_data(data_inicio, ipca_sorted)
    vna_f = _get_vna_na_data(data_fim, ipca_sorted)
    return (vna_f / vna_i) - 1.0 if vna_i > 0 else 0.0


def build_ipca_table(ipca_list: list, vna_base: float, data_fech_base: date) -> list:
    """
    Constrói tabela de IPCA/VNA projetados.
    ipca_list: [(mes_str, var_pct), ...] ex: [('04/2026', 0.57), ...]
    vna_base: VNA do último mês já divulgado
    data_fech_base: data de fechamento do último IPCA divulgado
    """
    resultado = [{'data_ref': None, 'data_fechamento': data_fech_base,
                  'variacao': 0.0, 'vna': vna_base}]
    vna = vna_base
    for mes_ano, var_pct in ipca_list:
        try:
            partes = mes_ano.strip().split('/')
            mes, ano = int(partes[0]), int(partes[1])
            vna = vna * (1 + var_pct / 100.0)
            if mes == 12:
                data_fech = date(ano + 1, 1, 15)
            else:
                data_fech = date(ano, mes + 1, 15)
            while not is_business_day(data_fech):
                data_fech += timedelta(days=1)
            resultado.append({'data_ref': date(ano, mes, 15),
                               'data_fechamento': data_fech,
                               'variacao': var_pct, 'vna': vna})
        except Exception:
            continue
    return resultado


def build_ipca_table_from_focus(focus_mensal: list, vna_base: float,
                                data_fech_base: date) -> list:
    if not focus_mensal:
        return []
    ipca_list = []
    for item in focus_mensal:
        ref = item.get('data_referencia', '')
        var = item.get('mediana') or item.get('media') or 0.0
        if ref:
            ipca_list.append((ref, float(var)))
    return build_ipca_table(ipca_list, vna_base, data_fech_base)


# ──────────────────────────────────────────────────────────────────────────────
# CDI / SELIC — com calendário COPOM
# ──────────────────────────────────────────────────────────────────────────────

COPOM_CALENDARIO = [
    {'data': date(2025, 1, 29),  'reuniao': '1R/2025'},
    {'data': date(2025, 3, 19),  'reuniao': '2R/2025'},
    {'data': date(2025, 5, 7),   'reuniao': '3R/2025'},
    {'data': date(2025, 6, 18),  'reuniao': '4R/2025'},
    {'data': date(2025, 7, 30),  'reuniao': '5R/2025'},
    {'data': date(2025, 9, 17),  'reuniao': '6R/2025'},
    {'data': date(2025, 11, 5),  'reuniao': '7R/2025'},
    {'data': date(2025, 12, 10), 'reuniao': '8R/2025'},
    {'data': date(2026, 1, 28),  'reuniao': '1R/2026'},
    {'data': date(2026, 3, 18),  'reuniao': '2R/2026'},
    {'data': date(2026, 4, 29),  'reuniao': '3R/2026'},
    {'data': date(2026, 6, 17),  'reuniao': '4R/2026'},
    {'data': date(2026, 8, 5),   'reuniao': '5R/2026'},
    {'data': date(2026, 9, 16),  'reuniao': '6R/2026'},
    {'data': date(2026, 11, 4),  'reuniao': '7R/2026'},
    {'data': date(2026, 12, 9),  'reuniao': '8R/2026'},
    {'data': date(2027, 1, 13),  'reuniao': '1R/2027'},
    {'data': date(2027, 2, 24),  'reuniao': '2R/2027'},
    {'data': date(2027, 4, 9),   'reuniao': '3R/2027'},
    {'data': date(2027, 5, 24),  'reuniao': '4R/2027'},
    {'data': date(2027, 7, 8),   'reuniao': '5R/2027'},
    {'data': date(2027, 8, 20),  'reuniao': '6R/2027'},
    {'data': date(2027, 10, 4),  'reuniao': '7R/2027'},
    {'data': date(2027, 11, 18), 'reuniao': '8R/2027'},
]


def cdi_retorno_com_copom(taxa_inicial_aa: float, copom_schedule: list,
                          data_inicio: date, data_fim: date) -> float:
    """Retorno CDI com múltiplas mudanças de Selic via COPOM."""
    du_list = business_days_list(data_inicio, data_fim)
    if not du_list:
        return 0.0
    copom_sorted = sorted(copom_schedule, key=lambda x: x['data'])
    taxa_atual = taxa_inicial_aa / 100.0
    produto = 1.0
    for d in du_list:
        for c in copom_sorted:
            if c['data'] == d:
                taxa_atual = c['nova_taxa'] / 100.0
                break
        produto *= (1 + taxa_atual) ** (1 / 252)
    return produto - 1.0


def cdi_retorno_simples(taxa_aa: float, du: int) -> float:
    return (1 + taxa_aa / 100.0) ** (du / 252) - 1


def build_copom_schedule_from_focus(focus_copom: list, selic_atual: float,
                                    data_inicio: date, data_fim: date) -> list:
    """Constrói schedule COPOM a partir dos dados do Focus."""
    focus_map = {}
    for item in focus_copom:
        reuniao = item.get('reuniao', '')
        mediana = item.get('mediana')
        if reuniao and mediana is not None:
            focus_map[reuniao] = float(mediana)

    schedule = []
    taxa = selic_atual
    for c in COPOM_CALENDARIO:
        if c['data'] < data_inicio or c['data'] > data_fim:
            continue
        nova_taxa = focus_map.get(c['reuniao'], taxa)
        schedule.append({'data': c['data'], 'nova_taxa': nova_taxa,
                         'reuniao': c['reuniao']})
        taxa = nova_taxa
    return schedule


def build_copom_schedule_manual(projecoes: dict, data_inicio: date,
                                data_fim: date) -> list:
    """projecoes: {'3R/2026': 14.5, '4R/2026': 14.25, ...}"""
    schedule = []
    for c in COPOM_CALENDARIO:
        if c['data'] < data_inicio or c['data'] > data_fim:
            continue
        if c['reuniao'] in projecoes:
            schedule.append({'data': c['data'], 'nova_taxa': projecoes[c['reuniao']],
                             'reuniao': c['reuniao']})
    return schedule


# ──────────────────────────────────────────────────────────────────────────────
# IMA-B 5 — carrego + marcação a mercado
# ──────────────────────────────────────────────────────────────────────────────

def imab5_retorno_total(yield_real_aa: float, du: int, variacao_bps: float,
                        duration_du: float, ipca_periodo: float) -> dict:
    """
    Retorno total IMA-B5 = (1 + IPCA) × (1 + carrego + marcação) - 1
    
    yield_real_aa: yield real (% a.a.)
    du: dias úteis do período
    variacao_bps: variação do yield em basis points (ex: -80 = fechamento 80bps)
    duration_du: duration em dias úteis
    ipca_periodo: IPCA acumulado (decimal, ex: 0.0265)
    """
    taxa = yield_real_aa / 100.0
    carrego = (1 + taxa) ** (du / 252) - 1
    duration_anos = duration_du / 252.0
    delta_y = variacao_bps / 10000.0
    marcacao = -duration_anos * delta_y / (1 + taxa)
    retorno_real = carrego + marcacao
    retorno_nominal = (1 + ipca_periodo) * (1 + retorno_real) - 1
    return {
        'carrego': carrego,
        'marcacao': marcacao,
        'retorno_real': retorno_real,
        'ipca_periodo': ipca_periodo,
        'retorno_total': retorno_nominal,
        'yield_final': yield_real_aa + variacao_bps / 100.0,
    }


# ──────────────────────────────────────────────────────────────────────────────
# FOCUS — API BCB
# ──────────────────────────────────────────────────────────────────────────────

BCB_URL = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata"


def _bcb_get(endpoint, params="", timeout=10):
    try:
        url = f"{BCB_URL}/{endpoint}?{params}&$format=json"
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {'value': [], '_error': str(e)}


def fetch_focus_ipca_mensal():
    data = _bcb_get("ExpectativaMercadoMensais",
                    "$filter=Indicador%20eq%20'IPCA'&$orderby=Data%20desc&$top=120"
                    "&$select=Indicador,Data,DataReferencia,Mediana,Media,Minimo,Maximo")
    visto = {}
    for item in data.get('value', []):
        ref = item.get('DataReferencia', '')
        if ref and ref not in visto:
            visto[ref] = {'data_referencia': ref,
                          'mediana': item.get('Mediana'),
                          'media': item.get('Media'),
                          'minimo': item.get('Minimo'),
                          'maximo': item.get('Maximo')}
    return sorted(visto.values(), key=lambda x: x['data_referencia'])


def fetch_focus_ipca_anual():
    data = _bcb_get("ExpectativasMercadoAnuais",
                    "$filter=Indicador%20eq%20'IPCA'&$orderby=Data%20desc&$top=20"
                    "&$select=Indicador,Data,DataReferencia,Mediana,Media")
    visto = {}
    for item in data.get('value', []):
        ref = str(item.get('DataReferencia', ''))
        if ref and ref not in visto:
            visto[ref] = {'ano': ref, 'mediana': item.get('Mediana'),
                          'media': item.get('Media')}
    return sorted(visto.values(), key=lambda x: x['ano'])


def fetch_focus_selic_anual():
    data = _bcb_get("ExpectativasMercadoAnuais",
                    "$filter=Indicador%20eq%20'Selic'&$orderby=Data%20desc&$top=20"
                    "&$select=Indicador,Data,DataReferencia,Mediana,Media")
    visto = {}
    for item in data.get('value', []):
        ref = str(item.get('DataReferencia', ''))
        if ref and ref not in visto:
            visto[ref] = {'ano': ref, 'mediana': item.get('Mediana'),
                          'media': item.get('Media')}
    return sorted(visto.values(), key=lambda x: x['ano'])


def fetch_focus_selic_copom():
    data = _bcb_get("ExpectativasMercadoSelic",
                    "$orderby=Data%20desc&$top=200"
                    "&$select=Reuniao,Data,Mediana,Media,DataReferencia")
    visto = {}
    for item in data.get('value', []):
        r = item.get('Reuniao', '')
        if r and r not in visto:
            visto[r] = {'reuniao': r, 'mediana': item.get('Mediana'),
                        'media': item.get('Media'),
                        'data_ref': item.get('DataReferencia', '')}
    return sorted(visto.values(), key=lambda x: x['data_ref'])


def fetch_focus_all():
    try:
        return {'ipca_mensal': fetch_focus_ipca_mensal(),
                'ipca_anual': fetch_focus_ipca_anual(),
                'selic_anual': fetch_focus_selic_anual(),
                'selic_copom': fetch_focus_selic_copom(),
                'ok': True}
    except Exception as e:
        return {'ipca_mensal': [], 'ipca_anual': [], 'selic_anual': [],
                'selic_copom': [], 'ok': False, 'erro': str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# ETTJ — Estrutura a Termo das Taxas de Juros (ANBIMA)
# ──────────────────────────────────────────────────────────────────────────────

def fetch_ettj_anbima(data_ref: date) -> dict:
    """
    Busca ETTJ pré e real da ANBIMA para a data de referência.
    Tenta arquivos públicos .txt. Retorna {'pre': [...], 'real': [...], 'ok': bool}
    """
    resultado = {'pre': [], 'real': [], 'ok': False, 'data': data_ref}
    data_str6 = data_ref.strftime('%y%m%d')
    data_str8 = data_ref.strftime('%Y%m%d')

    urls = [
        f"https://www.anbima.com.br/informacoes/curvas/arqs/curvas_{data_str8}.txt",
        f"https://www.anbima.com.br/informacoes/curvas/download/curvas_{data_str8}.txt",
        f"https://www.anbima.com.br/informacoes/merc-sec/arqs/ms{data_str6}.txt",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=12, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200 and len(r.text) > 100:
                parsed = _parse_ettj_txt(r.text)
                if parsed.get('pre') or parsed.get('real'):
                    resultado.update(parsed)
                    resultado['ok'] = True
                    resultado['fonte'] = url
                    return resultado
        except Exception:
            continue
    return resultado


def _parse_ettj_txt(text: str) -> dict:
    pre_rows, real_rows = [], []
    lines = text.replace('\r', '').split('\n')
    secao = None
    for line in lines:
        s = line.strip()
        if not s:
            continue
        su = s.upper()
        if 'PRE' in su and ('TAXA' in su or 'SPOT' in su or 'ANBIMA' in su):
            secao = 'pre'
            continue
        if 'NTN-B' in su or ('REAL' in su and 'TAXA' in su):
            secao = 'real'
            continue
        parts = s.split()
        if len(parts) >= 2:
            try:
                prazo = int(parts[0])
                taxa = float(parts[1].replace(',', '.'))
                row = {'prazo_du': prazo,
                       'prazo_anos': round(prazo / 252, 2),
                       'taxa': taxa}
                if secao == 'pre':
                    pre_rows.append(row)
                elif secao == 'real':
                    real_rows.append(row)
            except (ValueError, IndexError):
                continue
    return {'pre': pre_rows, 'real': real_rows}


def get_vencimentos_ntnb_padrao():
    return [2027, 2028, 2030, 2032, 2035, 2040, 2045, 2050, 2055]


# ──────────────────────────────────────────────────────────────────────────────
# FORMATAÇÃO
# ──────────────────────────────────────────────────────────────────────────────

def fmt_pct(val, decimals=2):
    return f"{val * 100:.{decimals}f}%" if val is not None else "—"


def fmt_pct_aa(val_pct, decimals=2):
    return f"{val_pct:.{decimals}f}% a.a." if val_pct is not None else "—"


def fmt_brl(val):
    if val is None:
        return "—"
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_brl_short(val):
    if val is None:
        return "—"
    if abs(val) >= 1e9:
        return f"R$ {val/1e9:.2f}B"
    if abs(val) >= 1e6:
        return f"R$ {val/1e6:.1f}M"
    return fmt_brl(val)
