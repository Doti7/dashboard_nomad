"""
dashboard.py - DASHBOARD COMPLETO DOTI
Vendas + Mercado Ads + Consolidado
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import psycopg

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

st.set_page_config(
    page_title="Dashboard Doti - Completo",
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

# Conexão com banco
if "DATABASE_URL" in st.secrets:
    DATABASE_URL = st.secrets["DATABASE_URL"]
else:
    DATABASE_URL = "postgresql://postgres:senha@db.boewuhmmmtencgvpdctc.supabase.co:5432/postgres"

# ============================================================================
# CARREGAR DADOS
# ============================================================================

@st.cache_data(ttl=300)
def carregar_vendas():
    """Carrega vendas do Supabase"""
    try:
        conn = psycopg.connect(DATABASE_URL)
        query = """
        SELECT canal, id_pedido, data_venda, sku, produto, qtd,
               preco_unitario, gmv, cmc_unitario, cmc_total,
               taxa_ml, taxa_gateway, frete, imposto, opex,
               lucro_liquido, margem_pct, uf, cidade, status
        FROM vendas
        WHERE status = 'paid'
        ORDER BY data_venda DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        
        df['data_venda'] = pd.to_datetime(df['data_venda'])
        df['mes'] = df['data_venda'].dt.to_period('M').astype(str)
        df['dia'] = df['data_venda'].dt.date
        df['taxa_total'] = df['taxa_ml'] + df['taxa_gateway']
        
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar vendas: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def carregar_ads():
    """Carrega Mercado Ads do Supabase"""
    try:
        conn = psycopg.connect(DATABASE_URL)
        query = """
        SELECT nome_campanha, status, orcamento, impressoes, cliques,
               cpc, ctr, cvr, receita, investimento, acos, roas,
               vendas_total, vendas_diretas, vendas_indiretas, unidades
        FROM mercado_ads
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ Erro ao carregar ads: {e}")
        return pd.DataFrame()

# Carregar dados
with st.spinner('🔄 Carregando dados...'):
    df_vendas = carregar_vendas()
    df_ads = carregar_ads()
    
    if len(df_vendas) == 0:
        st.warning("⚠️ Nenhuma venda encontrada")
        st.stop()

# ============================================================================
# SIDEBAR
# ============================================================================

st.sidebar.title("🎯 Filtros")

# Abas principais
tem_ads = len(df_ads) > 0
if tem_ads:
    aba_selecionada = st.sidebar.radio(
        "📊 Visualização",
        ["💰 Vendas", "📣 Mercado Ads", "📊 Consolidado"]
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

periodo = st.sidebar.selectbox(
    "📅 Período",
    ["Últimos 30 dias", "Últimos 7 dias", "Mês atual", "Hoje", "Ontem", "Personalizado"]
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

st.markdown('<div class="main-header">📊 Dashboard Doti</div>', unsafe_allow_html=True)

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
    
    # KPIs
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
            cor_icon = "🟡" if "Mercado" in canal or "ML" in canal else "🟢"
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
        fig = px.line(vendas_dia, x='Dia', y='Receita', color='Canal', title='Receita Diária')
        fig.update_layout(height=400, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        fig = px.line(vendas_dia, x='Dia', y='Lucro', color='Canal', title='Lucro Diário')
        fig.update_layout(height=400, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        fig = px.bar(vendas_dia, x='Dia', y='Unidades', color='Canal', title='Unidades Vendidas')
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

elif aba_selecionada == "📣 Mercado Ads" and tem_ads:
    
    st.markdown('<div class="sub-header">📣 Performance Mercado Ads</div>', unsafe_allow_html=True)
    
    # KPIs Ads
    investimento_total = df_ads['investimento'].sum()
    receita_ads = df_ads['receita'].sum()
    roas_medio = (receita_ads / investimento_total) if investimento_total > 0 else 0
    acos_medio = (investimento_total / receita_ads * 100) if receita_ads > 0 else 0
    vendas_ads = df_ads['vendas_total'].sum()
    cliques_total = df_ads['cliques'].sum()
    impressoes_total = df_ads['impressoes'].sum()
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
        top_campanhas = df_ads.nlargest(10, 'receita')
        fig = px.bar(top_campanhas, y='nome_campanha', x='receita',
                    orientation='h', color='roas',
                    color_continuous_scale='Greens')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("**🎯 Top 10 por ROAS**")
        df_ads_roas = df_ads[df_ads['investimento'] > 0]
        top_roas = df_ads_roas.nlargest(10, 'roas')
        fig = px.bar(top_roas, y='nome_campanha', x='roas',
                    orientation='h', color='roas',
                    color_continuous_scale='Blues')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# ABA: CONSOLIDADO
# ============================================================================

elif aba_selecionada == "📊 Consolidado" and tem_ads:
    
    st.markdown('<div class="sub-header">📊 Visão Consolidada</div>', unsafe_allow_html=True)
    
    # KPIs consolidados
    receita_vendas = df_filtrado['gmv'].sum()
    lucro_vendas = df_filtrado['lucro_liquido'].sum()
    investimento_ads = df_ads['investimento'].sum()
    receita_ads = df_ads['receita'].sum()
    
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
📊 **Fonte:** Supabase (dados das planilhas oficiais)  
🔄 **Próxima etapa:** Migração para APIs  
⚠️ **Acesso:** Restrito aos usuários autorizados
""")