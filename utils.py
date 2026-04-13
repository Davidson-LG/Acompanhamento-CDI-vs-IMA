"""
Utilities: feriados ANBIMA, VNA/IPCA, CDI com COPOM, IMA-B5, Focus API, ETTJ via pyettj.
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
# VNA / IPCA — METODOLOGIA ANBIMA
# ──────────────────────────────────────────────────────────────────────────────

def _get_vna_na_data(target: date, ipca_sorted: list) -> float:
    """
    VNA interpolado geometricamente pro-rata (metodologia ANBIMA).
    ipca_sorted deve ter 'data_fechamento' e 'vna', ordenado por data_fechamento.
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
            dias_total    = (d_cur - d_ant).days
            dias_parciais = (target - d_ant).days
            vna_ant = ipca_sorted[i - 1]['vna']
            vna_cur = ipca_sorted[i]['vna']
            if dias_total <= 0:
                return vna_ant
            return vna_ant * (vna_cur / vna_ant) ** (dias_parciais / dias_total)
    return ipca_sorted[-1]['vna']


def calc_ipca_periodo(data_inicio: date, data_fim: date, ipca_table: list) -> float:
    """IPCA acumulado no período (decimal). Usa VNA interpolado ANBIMA."""
    if not ipca_table:
        return 0.0
    s = sorted(ipca_table, key=lambda x: x['data_fechamento'])
    vi = _get_vna_na_data(data_inicio, s)
    vf = _get_vna_na_data(data_fim, s)
    return (vf / vi) - 1.0 if vi > 0 else 0.0


def build_ipca_table(ipca_list: list, vna_base: float, data_fech_base: date) -> list:
    """
    Constrói tabela VNA projetada.

    IMPORTANTE: para que o IPCA mensal seja calculado corretamente, a tabela
    deve conter TAMBÉM os meses anteriores ao período de análise (pelo menos
    o mês imediatamente anterior), pois a interpolação ANBIMA é feita entre
    datas de fechamento consecutivas.

    ipca_list : [(mes_str, var_pct), ...] ex: [('04/2026', 0.57), ...]
    vna_base  : VNA na data_fech_base (último mês já divulgado)
    data_fech_base: data de fechamento do último IPCA já divulgado
    """
    resultado = [{'data_ref': None,
                  'data_fechamento': data_fech_base,
                  'variacao': 0.0,
                  'vna': vna_base}]
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
                               'variacao': var_pct,
                               'vna': vna})
        except Exception:
            continue
    return resultado


def build_ipca_table_from_focus(focus_mensal: list, vna_base: float,
                                data_fech_base: date) -> list:
    """Constrói tabela a partir do Focus."""
    if not focus_mensal:
        return []
    ipca_list = [(item['data_referencia'], float(item.get('mediana') or item.get('media') or 0))
                 for item in focus_mensal if item.get('data_referencia')]
    return build_ipca_table(ipca_list, vna_base, data_fech_base)


# ──────────────────────────────────────────────────────────────────────────────
# COPOM
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
    {'data': date(2028, 2, 16),  'reuniao': '1R/2028'},
    {'data': date(2028, 3, 31),  'reuniao': '2R/2028'},
]


def cdi_retorno_com_copom(taxa_inicial_aa: float, copom_schedule: list,
                          data_inicio: date, data_fim: date) -> float:
    du_list = business_days_list(data_inicio, data_fim)
    if not du_list:
        return 0.0
    copom_sorted = sorted(copom_schedule, key=lambda x: x['data'])
    taxa = taxa_inicial_aa / 100.0
    produto = 1.0
    for d in du_list:
        for c in copom_sorted:
            if c['data'] == d:
                taxa = c['nova_taxa'] / 100.0
                break
        produto *= (1 + taxa) ** (1 / 252)
    return produto - 1.0


def cdi_retorno_simples(taxa_aa: float, du: int) -> float:
    return (1 + taxa_aa / 100.0) ** (du / 252) - 1


def build_copom_schedule_from_focus(focus_copom: list, selic_atual: float,
                                    data_inicio: date, data_fim: date) -> list:
    focus_map = {item['reuniao']: float(item['mediana'])
                 for item in focus_copom
                 if item.get('reuniao') and item.get('mediana') is not None}
    schedule, taxa = [], selic_atual
    for c in COPOM_CALENDARIO:
        if c['data'] < data_inicio or c['data'] > data_fim:
            continue
        nova = focus_map.get(c['reuniao'], taxa)
        schedule.append({'data': c['data'], 'nova_taxa': nova, 'reuniao': c['reuniao']})
        taxa = nova
    return schedule


def build_copom_schedule_manual(projecoes: dict, data_inicio: date, data_fim: date) -> list:
    return [{'data': c['data'], 'nova_taxa': projecoes[c['reuniao']],
             'reuniao': c['reuniao']}
            for c in COPOM_CALENDARIO
            if c['data'] >= data_inicio and c['data'] <= data_fim
            and c['reuniao'] in projecoes]


# ──────────────────────────────────────────────────────────────────────────────
# IMA-B 5 — retorno total
# ──────────────────────────────────────────────────────────────────────────────

def imab5_retorno_total(yield_real_aa: float, du: int, variacao_bps: float,
                        duration_du: float, ipca_periodo: float) -> dict:
    """
    Retorno total IMA-B5 = (1 + IPCA) × (1 + carrego + marcação) − 1
    variacao_bps: variação do yield em basis points (−80 = fechamento de 80bps)
    duration_du : duration em dias úteis
    """
    taxa     = yield_real_aa / 100.0
    carrego  = (1 + taxa) ** (du / 252) - 1
    marcacao = -(duration_du / 252.0) * (variacao_bps / 10000.0) / (1 + taxa)
    retorno_real    = carrego + marcacao
    retorno_nominal = (1 + ipca_periodo) * (1 + retorno_real) - 1
    return {'carrego': carrego, 'marcacao': marcacao,
            'retorno_real': retorno_real, 'ipca_periodo': ipca_periodo,
            'retorno_total': retorno_nominal,
            'yield_final': yield_real_aa + variacao_bps / 100.0}


# ──────────────────────────────────────────────────────────────────────────────
# FOCUS — API BCB
# ──────────────────────────────────────────────────────────────────────────────

_BCB = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata"


def _bcb_get(endpoint, params=""):
    try:
        r = requests.get(f"{_BCB}/{endpoint}?{params}&$format=json", timeout=12)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {'value': [], '_error': str(e)}


def fetch_focus_ipca_mensal():
    data = _bcb_get("ExpectativaMercadoMensais",
                    "$filter=Indicador%20eq%20'IPCA'&$orderby=Data%20desc&$top=200"
                    "&$select=Indicador,Data,DataReferencia,Mediana,Media,Minimo,Maximo")
    visto = {}
    for item in data.get('value', []):
        ref = item.get('DataReferencia', '')
        if ref and ref not in visto:
            visto[ref] = {'data_referencia': ref,
                          'mediana': item.get('Mediana'),
                          'media':   item.get('Media'),
                          'minimo':  item.get('Minimo'),
                          'maximo':  item.get('Maximo')}
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
                    "$orderby=Data%20desc&$top=300"
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
        return {'ipca_mensal':  fetch_focus_ipca_mensal(),
                'ipca_anual':   fetch_focus_ipca_anual(),
                'selic_anual':  fetch_focus_selic_anual(),
                'selic_copom':  fetch_focus_selic_copom(),
                'ok': True}
    except Exception as e:
        return {'ipca_mensal': [], 'ipca_anual': [], 'selic_anual': [],
                'selic_copom': [], 'ok': False, 'erro': str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# ETTJ — busca direta na B3 (sem pyettj, usa apenas requests + beautifulsoup4)
# Mesma lógica interna do pyettj, sem as dependências pesadas (scipy, matplotlib)
# ──────────────────────────────────────────────────────────────────────────────

def _b3_get_table(main_table) -> pd.DataFrame:
    """
    Replica o parser do pyettj.gettables.get_table() usando apenas bs4.
    Extrai uma tabela HTML da B3 em DataFrame com vértices × curvas.
    """
    table_names, sub_table_names = [], []
    dados, dados2 = [], []
    tabela = pd.DataFrame()

    for row in main_table.find_all('td'):
        row_str = str(row)
        txt = row.text.strip().replace('\r', ' ').replace('\n', ' ').replace('  ', ' ')
        if 'tabelaTitulo' in row_str and 'rowspan' in row_str:
            table_names.append(txt)
        elif 'tabelaTitulo' in row_str and 'colspan="1"' in row_str:
            table_names.append(txt)
        elif 'tabelaTitulo' in row_str and 'colspan="2"' in row_str:
            table_names.append(txt); table_names.append(txt)
        elif 'tabelaItem' in row_str:
            sub_table_names.append(txt)
        elif 'tabelaConteudo1' in row_str:
            dados.append(txt)
            if len(dados) == len(table_names):
                tabela = pd.concat([tabela, pd.DataFrame(dados).T])
                dados = []
        elif 'tabelaConteudo2' in row_str:
            dados2.append(txt)
            if len(dados2) == len(table_names):
                tabela = pd.concat([tabela, pd.DataFrame(dados2).T])
                dados2 = []

    if tabela.empty or not table_names:
        return pd.DataFrame()

    tn = table_names
    tn_part1 = [tn[i+1] if tn[i] == '' else tn[i] for i in range(len(tn)-1)]
    tn_part2 = tn_part1 + [tn[-1]]
    new_sub = [x + str(i) if sub_table_names.count(x) == 2 else x
               for i, x in enumerate(sub_table_names)]
    colunas = [tn_part2[0]] + [i + ' ' + j for i, j in zip(tn_part2[1:], new_sub)]
    colunas = [x.split('(')[0].split(')')[0].strip() for x in colunas]

    tabela.columns = colunas
    for i, col in enumerate(tabela.columns.tolist()):
        if i == 0:
            tabela[col] = pd.to_numeric(tabela[col], errors='coerce')
        else:
            tabela[col] = pd.to_numeric(
                tabela[col].astype(str).str.replace(',', '.'), errors='coerce')
    return tabela.dropna(subset=[tabela.columns[0]])


def get_ettj_b3(data_ref: date, curva: str = "TODOS") -> pd.DataFrame:
    """
    Busca ETTJ da B3 diretamente (sem pyettj).
    Requer apenas: requests, beautifulsoup4, lxml/html5lib.
    Retorna DataFrame com curvas nas colunas e vértices (du) no índice.
    """
    try:
        from bs4 import BeautifulSoup
        data_fmt = data_ref.strftime('%m/%d/%Y')
        curva_up = curva.upper()

        if curva_up == 'TODOS':
            url = (f"https://www2.bmf.com.br/pages/portal/bmfbovespa/boletim1/"
                   f"TxRef1.asp?Data={data_fmt}&Data1=20060201&slcTaxa=TODOS")
        else:
            url = (f"https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/"
                   f"lum-taxas-referenciais-bmf-ptBR.asp"
                   f"?Data={data_fmt}&Data1=20060201&slcTaxa={curva_up}")

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                  'AppleWebKit/537.36 Chrome/120.0 Safari/537.36',
                   'Accept-Language': 'pt-BR,pt;q=0.9'}
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'lxml')
        tables = soup.find_all('table')

        if len(tables) < 2:
            return pd.DataFrame()

        if 'Não há dados' in resp.text:
            return pd.DataFrame()

        if curva_up == 'TODOS':
            # 4 tabelas: PRE, DI×IPCA, DI×IGPM, DI×TJLP (índices 1-4)
            partes = []
            for t in tables[1:5]:
                df_t = _b3_get_table(t)
                if not df_t.empty:
                    partes.append(df_t)
            if not partes:
                return pd.DataFrame()
            # Merge pelo primeiro campo (vértice)
            result = partes[0]
            for p in partes[1:]:
                result = result.merge(p, on=result.columns[0], how='outer')
            result = result.set_index(result.columns[0])
            result.index.name = 'Vértice (du)'
            result['Data'] = data_ref.strftime('%Y-%m-%d')
            # Remove colunas duplicadas
            result = result.loc[:, ~result.columns.duplicated()]
            # Limpa nomes de coluna
            result.columns = [c.split('(')[0].strip() if '(' in str(c) else str(c)
                               for c in result.columns]
            return result
        else:
            df_t = pd.read_html(resp.text)[0]
            return df_t

    except Exception:
        return pd.DataFrame()


def parse_ettj_for_curve(df: pd.DataFrame, curva_nome: str) -> pd.DataFrame:
    """
    Extrai uma curva do DataFrame retornado por get_ettj_b3().
    curva_nome: 'PRE', 'DI x IPCA', etc.
    Retorna DataFrame com colunas: prazo_du, prazo_anos, taxa
    """
    if df.empty:
        return pd.DataFrame()
    # Busca coluna pelo nome (case-insensitive, parcial)
    busca = curva_nome.upper().replace(' ', '')
    cols = [c for c in df.columns
            if busca in str(c).upper().replace(' ', '')]
    if not cols:
        # Tenta match mais amplo
        partes = curva_nome.upper().split()
        for p in partes:
            cols = [c for c in df.columns if p in str(c).upper()]
            if cols:
                break
    if not cols:
        return pd.DataFrame()

    col = cols[0]
    sub = df[[col]].copy().reset_index()
    sub.columns = ['prazo_du', 'taxa']
    sub = sub.dropna()
    sub['prazo_du'] = pd.to_numeric(sub['prazo_du'], errors='coerce')
    sub['taxa']     = pd.to_numeric(sub['taxa'], errors='coerce')
    sub = sub.dropna()
    sub['prazo_anos'] = sub['prazo_du'] / 252.0
    return sub.sort_values('prazo_du').reset_index(drop=True)


def last_business_day(ref: date = None, n: int = 0) -> date:
    """Retorna o n-ésimo dia útil anterior a ref (0 = ontem/último DU)."""
    d = (ref or date.today()) - timedelta(days=1)
    steps = 0
    while True:
        if is_business_day(d):
            if steps == n:
                return d
            steps += 1
        d -= timedelta(days=1)


def last_business_day_1y_ago(ref: date = None) -> date:
    """Retorna o último dia útil ~1 ano antes de ref."""
    d = ref or date.today()
    d_1y = date(d.year - 1, d.month, d.day)
    for delta in range(5):
        candidate = d_1y - timedelta(days=delta)
        if is_business_day(candidate):
            return candidate
    return d_1y


# ──────────────────────────────────────────────────────────────────────────────
# FORMATAÇÃO
# ──────────────────────────────────────────────────────────────────────────────

def fmt_pct(val, decimals=2):
    return f"{val * 100:.{decimals}f}%" if val is not None else "—"

def fmt_pct_aa(val_pct, decimals=2):
    return f"{val_pct:.{decimals}f}% a.a." if val_pct is not None else "—"

def fmt_brl(val):
    if val is None: return "—"
    return f"R$ {val:,.2f}".replace(",","X").replace(".",",").replace("X",".")

def fmt_brl_short(val):
    if val is None: return "—"
    if abs(val) >= 1e9: return f"R$ {val/1e9:.2f}B"
    if abs(val) >= 1e6: return f"R$ {val/1e6:.1f}M"
    return fmt_brl(val)
