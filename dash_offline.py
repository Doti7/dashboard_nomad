"""
dashboard.py - DASHBOARD COMPLETO DOTI
Execute: streamlit run dashboard.py

DADOS:
- Mercado Livre (planilhas)
- Braavo (planilhas)  
- Mercado Ads (planilhas)
- CMC do Omie

PREPARADO PARA:
- Streamlit Cloud (deploy online)
- Uso local (planilhas)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re
import os

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

st.set_page_config(
    page_title="Dashboard Doti - Vendas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; font-weight: bold; margin-bottom: 1rem;}
    .sub-header {font-size: 1.5rem; font-weight: bold; margin-top: 2rem; margin-bottom: 1rem;}
    .metric-card {background: #f0f2f6; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0;}
    .positive {color: #00D26A;}
    .negative {color: #FF4B4B;}
    .canal-ml {color: #FFE600; font-weight: bold;}
    .canal-braavo {color: #00A650; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def parse_data_ml(data_str):
    """Parseia data do Mercado Livre"""
    try:
        if pd.isna(data_str):
            return None
        data_str = str(data_str).replace(' de ', ' ').replace(' hs.', '').strip()
        meses = {
            'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
            'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
            'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
        }
        for mes_pt, mes_num in meses.items():
            if mes_pt in data_str.lower():
                data_str = data_str.lower().replace(mes_pt, mes_num)
                break
        parts = data_str.split()
        if len(parts) >= 4:
            dia = parts[0].zfill(2)
            mes = parts[1]
            ano = parts[2]
            hora = parts[3] if len(parts) > 3 else '00:00'
            return pd.to_datetime(f'{ano}-{mes}-{dia} {hora}', errors='coerce')
    except:
        return None
    return None

@st.cache_data(ttl=3600)
def carregar_vendas():
    """Carrega dados de vendas ML + Braavo"""
    
    # ========================================================================
    # MERCADO LIVRE
    # ========================================================================
    
    # Buscar arquivo ML mais recente
    arquivos_ml = [f for f in os.listdir('.') if 'Vendas_BR_Mercado_Libre' in f and f.endswith('.xlsx')]
    
    if not arquivos_ml:
        st.error("❌ Planilha ML não encontrada! Coloque 'Vendas_BR_Mercado_Libre_*.xlsx' na pasta")
        st.stop()
    
    arquivo_ml = max(arquivos_ml)
    
    df_ml_raw = pd.read_excel(arquivo_ml, sheet_name='Vendas BR')
    df_ml_raw['data_venda'] = df_ml_raw['Data da venda'].apply(parse_data_ml)
    df_ml_raw = df_ml_raw[df_ml_raw['data_venda'].notna()].copy()
    
    # Filtrar vendas válidas
    estados_validos = ['Entregue', 'Venda entregue', 'Pacote de 2 produtos', 
                      'Pacote de 3 produtos', 'Pacote de 4 produtos']
    df_ml = df_ml_raw[df_ml_raw['Estado'].str.contains('|'.join(estados_validos), na=False, case=False)].copy()
    
    df_ml['canal'] = 'Mercado Livre'
    df_ml['id_pedido'] = df_ml['N.º de venda'].astype(str)
    df_ml['sku'] = df_ml['SKU'].fillna('N/A').astype(str)
    df_ml['produto'] = df_ml['Título do anúncio']
    df_ml['qtd'] = df_ml['Unidades'].fillna(1)
    df_ml['preco_unitario'] = df_ml['Preço unitário de venda do anúncio (BRL)'].fillna(0)
    df_ml['gmv'] = df_ml['Receita por produtos (BRL)'].fillna(0)
    df_ml['taxa_ml'] = -df_ml['Tarifa de venda e impostos (BRL)'].fillna(0)
    df_ml['taxa_gateway'] = 0
    df_ml['frete'] = 0
    df_ml['imposto'] = 0
    df_ml['opex'] = 0
    df_ml['uf'] = df_ml['Estado.1'].fillna('N/A')
    df_ml['cidade'] = df_ml['Cidade'].fillna('N/A')
    df_ml['status'] = 'paid'
    
    # ========================================================================
    # BRAAVO
    # ========================================================================
    
    # Buscar arquivo Braavo mais recente
    arquivos_braavo = [f for f in os.listdir('.') if f.startswith('Planilha-') and f.endswith('.xlsx')]
    
    if not arquivos_braavo:
        st.error("❌ Planilha Braavo não encontrada! Coloque 'Planilha-*.xlsx' na pasta")
        st.stop()
    
    arquivo_braavo = max(arquivos_braavo)
    
    df_braavo = pd.read_excel(arquivo_braavo)
    df_braavo['data_venda'] = pd.to_datetime(df_braavo['Data Compra'])
    df_braavo['canal'] = 'Braavo'
    df_braavo['id_pedido'] = df_braavo['Pedido'].astype(str)
    df_braavo['sku'] = df_braavo['SKU'].astype(str)
    df_braavo['produto'] = df_braavo['Produto']
    df_braavo['qtd'] = df_braavo['Quantidade']
    df_braavo['preco_unitario'] = df_braavo['Preço Venda Un']
    df_braavo['gmv'] = df_braavo['Total Venda 1']
    df_braavo['uf'] = 'N/A'
    df_braavo['cidade'] = 'N/A'
    df_braavo['status'] = 'paid'
    df_braavo['taxa_ml'] = 0
    df_braavo['frete'] = 0
    df_braavo['imposto'] = 0
    df_braavo['opex'] = 0
    df_braavo['taxa_gateway'] = df_braavo['gmv'] * 0.04
    
    # ========================================================================
    # CMC (OMIE)
    # ========================================================================
    
    if os.path.exists('estoque_omie.xlsx'):
        df_omie = pd.read_excel('estoque_omie.xlsx')
        df_omie['SKU_Omie'] = df_omie['Código do Produto'].str.strip().str.upper()
        df_omie_cmc = df_omie[['SKU_Omie', 'Soma de CMC Unitário']].copy()
        df_omie_cmc.columns = ['SKU', 'CMC_Omie']
    else:
        df_omie_cmc = pd.DataFrame(columns=['SKU', 'CMC_Omie'])
    
    cmc_cat = {
        'BRETELLE': 74.64, 'MEIA': 14.41, 'JERSEY': 32.51,
        'CAMISA': 30.13, 'BONE': 30.07, 'LUVA': 31.98,
        'SHORT': 42.23, 'BERMUDA': 55.83, 'TRUCKPAD': 176.50
    }
    
    def obter_cmc(row, df_omie_cmc, cmc_cat):
        # 1. Via Referência (Braavo)
        if 'Referência' in row and pd.notna(row.get('Referência')):
            ref = str(row['Referência']).strip().upper()
            match = df_omie_cmc[df_omie_cmc['SKU'] == ref]
            if not match.empty:
                return match.iloc[0]['CMC_Omie']
        
        # 2. Via SKU direto
        if pd.notna(row['sku']):
            sku = str(row['sku']).strip().upper()
            for prefix in ['', 'NMD']:
                sku_test = f'{prefix}{sku}'
                match = df_omie_cmc[df_omie_cmc['SKU'] == sku_test]
                if not match.empty:
                    return match.iloc[0]['CMC_Omie']
        
        # 3. CMC da planilha Braavo
        if 'Preço Custo Un' in row and pd.notna(row.get('Preço Custo Un')) and row.get('Preço Custo Un') > 0:
            return row['Preço Custo Un']
        
        # 4. Inferir por categoria
        produto_upper = str(row['produto']).upper()
        for cat, cmc in cmc_cat.items():
            if cat in produto_upper:
                return cmc
        
        # 5. CMC geral
        return 44.16
    
    # Aplicar CMC
    if 'Referência' in df_braavo.columns:
        df_braavo['Ref_Clean'] = df_braavo['Referência'].astype(str).str.strip().str.upper()
    
    df_braavo['cmc_unitario'] = df_braavo.apply(lambda row: obter_cmc(row, df_omie_cmc, cmc_cat), axis=1)
    df_ml['cmc_unitario'] = df_ml.apply(lambda row: obter_cmc(row, df_omie_cmc, cmc_cat), axis=1)
    
    # Calcular lucro
    for df in [df_ml, df_braavo]:
        df['cmc_total'] = df['cmc_unitario'] * df['qtd']
        df['lucro_liquido'] = (
            df['gmv'] - df['cmc_total'] - df['taxa_ml'] - 
            df['taxa_gateway'] - df['frete'] - df['imposto'] - df['opex']
        )
        df['margem_pct'] = (df['lucro_liquido'] / df['gmv'] * 100).fillna(0)
    
    # ========================================================================
    # UNIFICAR
    # ========================================================================
    
    colunas_finais = [
        'canal', 'id_pedido', 'data_venda', 'sku', 'produto', 'qtd',
        'preco_unitario', 'gmv', 'cmc_unitario', 'cmc_total',
        'taxa_ml', 'taxa_gateway', 'frete', 'imposto', 'opex',
        'lucro_liquido', 'margem_pct', 'uf', 'cidade', 'status'
    ]
    
    df_final = pd.concat([
        df_ml[colunas_finais],
        df_braavo[colunas_finais]
    ], ignore_index=True)
    
    df_final['mes'] = df_final['data_venda'].dt.to_period('M').astype(str)
    df_final['dia'] = df_final['data_venda'].dt.date
    df_final['dia_nome'] = df_final['data_venda'].dt.day_name()
    df_final['taxa_total'] = df_final['taxa_ml'] + df_final['taxa_gateway']
    
    return df_final

@st.cache_data(ttl=3600)
def carregar_ads():
    """Carrega dados de Mercado Ads"""
    
    # Buscar arquivo Ads mais recente
    arquivos_ads = [f for f in os.listdir('.') if f.startswith('Relatorio_campanhas_') and f.endswith('.xlsx')]
    
    if not arquivos_ads:
        return None  # Ads opcional
    
    arquivo_ads = max(arquivos_ads)
    
    try:
        df_ads = pd.read_excel(arquivo_ads, sheet_name='Relatório de campanha', skiprows=1)
        
        # Limpar colunas
        df_ads.columns = df_ads.columns.str.replace('\n', ' ').str.strip()
        
        # Garantir colunas numéricas
        colunas_numericas = [
            'Orçamento', 'Impressões', 'Cliques', 'CPC  (Custo por clique)',
            'CTR (Click through rate)', 'CVR (Conversion rate)',
            'Receita (Moeda local)', 'Investimento (Moeda local)',
            'ACOS (Investimento / Receitas)', 'ROAS (Receitas / Investimento)',
            'Vendas por publicidade (Diretas + Indiretas)', 'Vendas diretas',
            'Vendas indiretas', 'Receita por ventas diretas (Moeda local)',
            'Receita por vendas indiretas (Moeda local)', 'Unidades vendidas por publicidade'
        ]
        
        for col in colunas_numericas:
            if col in df_ads.columns:
                df_ads[col] = pd.to_numeric(df_ads[col], errors='coerce').fillna(0)
        
        return df_ads
    except:
        return None

# ============================================================================
# CARREGAMENTO DE DADOS
# ============================================================================

with st.spinner('🔄 Carregando dados...'):
    try:
        df_vendas = carregar_vendas()
        df_ads = carregar_ads()
        
        if len(df_vendas) == 0:
            st.error("❌ Nenhuma venda encontrada!")
            st.stop()
            
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        st.exception(e)
        st.stop()

# ============================================================================
# SIDEBAR - FILTROS
# ============================================================================

st.sidebar.title("🎯 Filtros")

# Abas principais
if df_ads is not None and len(df_ads) > 0:
    aba_selecionada = st.sidebar.radio(
        "📊 Visualização",
        ["💰 Vendas", "📣 Mercado Ads", "📊 Consolidado"],
        label_visibility="collapsed"
    )
else:
    aba_selecionada = "💰 Vendas"

# Filtro de canal (apenas para vendas)
if aba_selecionada in ["💰 Vendas", "📊 Consolidado"]:
    canais_disponiveis = ['Todos'] + sorted(df_vendas['canal'].unique().tolist())
    canal_selecionado = st.sidebar.selectbox("📊 Canal", canais_disponiveis)
else:
    canal_selecionado = 'Todos'

# Filtro de data
data_min = df_vendas['data_venda'].min().date()
data_max = df_vendas['data_venda'].max().date()

# Atalhos de período
periodo = st.sidebar.selectbox(
    "📅 Período",
    ["Personalizado", "Hoje", "Ontem", "Últimos 7 dias", "Últimos 30 dias", "Mês atual"]
)

if periodo == "Hoje":
    data_inicio = data_fim = datetime.now().date()
elif periodo == "Ontem":
    data_inicio = data_fim = (datetime.now() - timedelta(days=1)).date()
elif periodo == "Últimos 7 dias":
    data_fim = datetime.now().date()
    data_inicio = data_fim - timedelta(days=7)
elif periodo == "Últimos 30 dias":
    data_fim = datetime.now().date()
    data_inicio = data_fim - timedelta(days=30)
elif periodo == "Mês atual":
    data_fim = datetime.now().date()
    data_inicio = datetime.now().replace(day=1).date()
else:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        data_inicio = st.date_input("De", data_min, min_value=data_min, max_value=data_max)
    with col2:
        data_fim = st.date_input("Até", data_max, min_value=data_min, max_value=data_max)

# Aplicar filtros
df_filtrado = df_vendas[
    (df_vendas['data_venda'].dt.date >= data_inicio) &
    (df_vendas['data_venda'].dt.date <= data_fim)
]

if canal_selecionado != 'Todos':
    df_filtrado = df_filtrado[df_filtrado['canal'] == canal_selecionado]

# ============================================================================
# HEADER
# ============================================================================

st.markdown('<div class="main-header">📊 Dashboard Doti - Vendas</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.markdown(f"**Período:** {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
with col2:
    if canal_selecionado != 'Todos':
        st.info(f"📊 Canal: **{canal_selecionado}**")
with col3:
    st.caption(f"🔄 Atualizado: {datetime.now().strftime('%H:%M')}")

st.markdown("---")

# ============================================================================
# ABA: VENDAS
# ============================================================================

if aba_selecionada == "💰 Vendas":
    
    st.markdown('<div class="sub-header">📈 Visão Geral de Vendas</div>', unsafe_allow_html=True)
    
    # KPIs principais
    receita_total = df_filtrado['gmv'].sum()
    lucro_total = df_filtrado['lucro_liquido'].sum()
    margem_media = df_filtrado['margem_pct'].mean()
    taxa_total = df_filtrado['taxa_total'].sum()
    ticket_medio = df_filtrado['gmv'].mean()
    qtd_vendas = len(df_filtrado)
    unidades_vendidas = df_filtrado['qtd'].sum()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Receita (GMV)", f"R$ {receita_total:,.2f}", 
                 delta=f"{qtd_vendas} vendas")
    
    with col2:
        st.metric("📈 Lucro Líquido", f"R$ {lucro_total:,.2f}",
                 delta=f"{margem_media:.1f}% margem")
    
    with col3:
        st.metric("💳 Taxas Pagas", f"R$ {taxa_total:,.2f}",
                 delta=f"{taxa_total/receita_total*100:.1f}% da receita")
    
    with col4:
        st.metric("🎫 Ticket Médio", f"R$ {ticket_medio:,.2f}",
                 delta=f"{unidades_vendidas:.0f} unidades")
    
    st.markdown("---")
    
    # Comparativo por canal
    st.markdown('<div class="sub-header">🏪 Comparativo por Canal</div>', unsafe_allow_html=True)
    
    metricas_canal = df_filtrado.groupby('canal').agg({
        'gmv': 'sum',
        'lucro_liquido': 'sum',
        'taxa_total': 'sum',
        'qtd': 'sum',
        'id_pedido': 'count'
    }).reset_index()
    
    metricas_canal.columns = ['Canal', 'Receita', 'Lucro', 'Taxas', 'Unidades', 'Vendas']
    metricas_canal['Margem %'] = (metricas_canal['Lucro'] / metricas_canal['Receita'] * 100).round(1)
    metricas_canal['Ticket Médio'] = (metricas_canal['Receita'] / metricas_canal['Vendas']).round(2)
    
    canais_unicos = df_filtrado['canal'].unique()
    cols = st.columns(len(canais_unicos))
    
    for i, canal in enumerate(sorted(canais_unicos)):
        dados_canal = metricas_canal[metricas_canal['Canal'] == canal].iloc[0]
        
        with cols[i]:
            cor_icon = "🟡" if canal == "Mercado Livre" else "🟢"
            st.markdown(f"### {cor_icon} {canal}")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Receita", f"R$ {dados_canal['Receita']:,.0f}")
                st.metric("Lucro", f"R$ {dados_canal['Lucro']:,.0f}")
                st.metric("Vendas", f"{dados_canal['Vendas']:.0f}")
            
            with col_b:
                st.metric("Margem", f"{dados_canal['Margem %']:.1f}%")
                st.metric("Taxas", f"R$ {dados_canal['Taxas']:,.0f}")
                st.metric("Ticket", f"R$ {dados_canal['Ticket Médio']:,.2f}")
    
    st.markdown("---")
    
    # Evolução temporal
    st.markdown('<div class="sub-header">📊 Evolução Temporal</div>', unsafe_allow_html=True)
    
    vendas_dia = df_filtrado.groupby(['dia', 'canal']).agg({
        'gmv': 'sum',
        'lucro_liquido': 'sum',
        'qtd': 'sum'
    }).reset_index()
    
    vendas_dia.columns = ['Dia', 'Canal', 'Receita', 'Lucro', 'Unidades']
    
    tab1, tab2, tab3 = st.tabs(["💰 Receita", "📈 Lucro", "📦 Unidades"])
    
    with tab1:
        fig = px.line(vendas_dia, x='Dia', y='Receita', color='Canal',
                     title='Receita Diária',
                     color_discrete_map={'Mercado Livre': '#FFE600', 'Braavo': '#00A650'})
        fig.update_layout(height=400, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        fig = px.line(vendas_dia, x='Dia', y='Lucro', color='Canal',
                     title='Lucro Diário',
                     color_discrete_map={'Mercado Livre': '#FFE600', 'Braavo': '#00A650'})
        fig.update_layout(height=400, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        fig = px.bar(vendas_dia, x='Dia', y='Unidades', color='Canal',
                    title='Unidades Vendidas',
                    color_discrete_map={'Mercado Livre': '#FFE600', 'Braavo': '#00A650'})
        fig.update_layout(height=400, barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Top produtos
    st.markdown('<div class="sub-header">🏆 Top Produtos</div>', unsafe_allow_html=True)
    
    top_produtos = df_filtrado.groupby('produto').agg({
        'gmv': 'sum',
        'lucro_liquido': 'sum',
        'qtd': 'sum'
    }).reset_index().sort_values('gmv', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**💰 Top 10 por Receita**")
        fig = px.bar(top_produtos.head(10), y='produto', x='gmv', orientation='h',
                    color='gmv', color_continuous_scale='Blues')
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("**📈 Top 10 por Lucro**")
        top_lucro = top_produtos.sort_values('lucro_liquido', ascending=False).head(10)
        fig = px.bar(top_lucro, y='produto', x='lucro_liquido', orientation='h',
                    color='lucro_liquido', color_continuous_scale='Greens')
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# ABA: MERCADO ADS
# ============================================================================

elif aba_selecionada == "📣 Mercado Ads" and df_ads is not None:
    
    st.markdown('<div class="sub-header">📣 Performance Mercado Ads</div>', unsafe_allow_html=True)
    
    # KPIs Ads
    investimento_total = df_ads['Investimento (Moeda local)'].sum()
    receita_ads = df_ads['Receita (Moeda local)'].sum()
    roas_medio = (receita_ads / investimento_total) if investimento_total > 0 else 0
    acos_medio = (investimento_total / receita_ads * 100) if receita_ads > 0 else 0
    vendas_ads = df_ads['Vendas por publicidade (Diretas + Indiretas)'].sum()
    cliques_total = df_ads['Cliques'].sum()
    impressoes_total = df_ads['Impressões'].sum()
    ctr_medio = (cliques_total / impressoes_total * 100) if impressoes_total > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Investimento", f"R$ {investimento_total:,.2f}")
    
    with col2:
        st.metric("📈 Receita Ads", f"R$ {receita_ads:,.2f}",
                 delta=f"ROAS: {roas_medio:.2f}x")
    
    with col3:
        st.metric("🎯 ACOS", f"{acos_medio:.1f}%",
                 delta="Meta: 25%", delta_color="inverse")
    
    with col4:
        st.metric("🛒 Vendas por Ads", f"{vendas_ads:.0f}",
                 delta=f"CTR: {ctr_medio:.2f}%")
    
    st.markdown("---")
    
    # Top campanhas
    st.markdown('<div class="sub-header">🏆 Top Campanhas</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**💰 Top 10 por Receita**")
        top_campanhas = df_ads.nlargest(10, 'Receita (Moeda local)')
        fig = px.bar(top_campanhas, y='Nome', x='Receita (Moeda local)',
                    orientation='h', color='ROAS (Receitas / Investimento)',
                    color_continuous_scale='Greens')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("**🎯 Top 10 por ROAS**")
        df_ads_roas = df_ads[df_ads['Investimento (Moeda local)'] > 0]
        top_roas = df_ads_roas.nlargest(10, 'ROAS (Receitas / Investimento)')
        fig = px.bar(top_roas, y='Nome', x='ROAS (Receitas / Investimento)',
                    orientation='h', color='ROAS (Receitas / Investimento)',
                    color_continuous_scale='Blues')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# ABA: CONSOLIDADO
# ============================================================================

elif aba_selecionada == "📊 Consolidado" and df_ads is not None:
    
    st.markdown('<div class="sub-header">📊 Visão Consolidada - Vendas + Ads</div>', unsafe_allow_html=True)
    
    # KPIs consolidados
    receita_vendas = df_filtrado['gmv'].sum()
    lucro_vendas = df_filtrado['lucro_liquido'].sum()
    investimento_ads = df_ads['Investimento (Moeda local)'].sum()
    receita_ads = df_ads['Receita (Moeda local)'].sum()
    
    lucro_real = lucro_vendas - investimento_ads
    roi_ads = ((receita_ads - investimento_ads) / investimento_ads * 100) if investimento_ads > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Receita Total", f"R$ {receita_vendas:,.2f}")
    
    with col2:
        st.metric("💳 Investimento Ads", f"R$ {investimento_ads:,.2f}",
                 delta=f"{investimento_ads/receita_vendas*100:.1f}% da receita")
    
    with col3:
        st.metric("📈 Lucro Real", f"R$ {lucro_real:,.2f}",
                 delta=f"{lucro_real/receita_vendas*100:.1f}% margem")
    
    with col4:
        st.metric("🎯 ROI Ads", f"{roi_ads:.1f}%",
                 delta=f"R$ {receita_ads:,.0f} gerados")

# ============================================================================
# RODAPÉ
# ============================================================================

st.markdown("---")
st.caption(f"""
📊 **Fonte:** Planilhas oficiais  
🔄 **Próxima feature:** Integração com API para atualização automática  
⚠️ **Nota:** Dados sensíveis - não compartilhar externamente
""")