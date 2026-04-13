# 📈 Dashboard IMA-B 5 × CDI — Rentabilidade

> Dashboard de acompanhamento e simulação de rentabilidade de índices de renda fixa (IMA-B 5, IMA-B 5+ e CDI), com integração ao Focus/BCB e metodologia ANBIMA de VNA.

---

## 🚀 Deploy no Streamlit Cloud

### 1. Fork / Upload para o GitHub

Suba todos os arquivos desta pasta para um repositório GitHub:

```
investment-dashboard/
├── app.py
├── utils.py
├── requirements.txt
├── .streamlit/
│   └── config.toml
└── README.md
```

### 2. Acesse [share.streamlit.io](https://share.streamlit.io)

- Clique em **"New app"**
- Escolha o repositório do GitHub
- Defina **Main file path**: `app.py`
- Clique em **Deploy**

---

## 🔧 Rodando Localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 📚 Funcionalidades

### 📊 Aba 1 — Comparativo de Cenários
- Dados do **Focus/BCB** (IPCA mensal e anual, Selic)
- Parâmetros configuráveis: Yield IMA-B 5, Duration, janela temporal
- **3 cenários**: fechamento, manutenção e abertura de curva
- Cálculo com metodologia **ANBIMA/VNA** (igual à planilha de referência)
- Retorno nominal e real, breakdown por componente (carrego + marcação + IPCA)

### 📅 Aba 2 — Projeção Mês a Mês
- Retorno mensal detalhado por índice
- Comparativo acumulado com gráfico interativo
- Tabela com todos os componentes

### 📉 Aba 3 — Curvas de Juros
- Curva NTN-B semana atual vs semana anterior
- Entrada manual ou API ANBIMA
- Histórico de Redemption Yield com bandas de desvio padrão

### 💼 Aba 4 — Simulação de Alocação
- Dois fundos configuráveis (IMA-B 5 + CDI/DI)
- Simulação de movimentações entre fundos
- Retorno esperado e volatilidade ponderada por cenário
- Gráficos de composição da carteira

---

## 🧮 Metodologia

### VNA (Valor Nominal Atualizado)
O VNA é calculado por interpolação linear pro-rata entre datas de divulgação do IPCA,
exatamente como descrito pela metodologia ANBIMA para NTN-B:

```
VNA(t) = VNA(t₋₁) × (VNA_mês / VNA_mês₋₁)^(dias_corridos / dias_total_mês)
```

### Retorno IMA-B 5
```
Retorno = (1 + IPCA_período) × (1 + carrego_real + marcação) - 1

carrego_real = (1 + yield)^(du/252) - 1
marcação     = -Duration_anos × Δyield / (1 + yield)
```

### CDI
```
Retorno = (1 + Selic)^(du/252) - 1
```

---

## 🔗 Fontes de Dados

- **Focus/BCB**: [Serviço de Expectativas de Mercado do BCB](https://www.bcb.gov.br/publicacoes/focus)
- **ANBIMA**: [Curvas de Mercado Secundário](https://www.anbima.com.br/pt_br/informar/precos-e-indices/indicadores-de-renda-fixa/ima/ima-geral.htm)
- **Selic/CDI**: Calculado com base na taxa Selic meta (COPOM)
- **VNA**: Metodologia NTN-B da ANBIMA

---

## ⚠️ Aviso

> Este dashboard é uma ferramenta de apoio à análise. Não constitui recomendação de investimento. Os dados projetados dependem de premissas e podem diferir do realizado.
