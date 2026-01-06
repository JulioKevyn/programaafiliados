import streamlit as st
import pandas as pd
from supabase import create_client
import time
import plotly.express as px
from datetime import datetime, timedelta

# ==============================================================================
# ⚙️ CONFIGURAÇÃO E CSS PREMIUM (O Visual do Olimpo)
# ==============================================================================
st.set_page_config(page_title="Olympikus IPTV", page_icon="🏛️", layout="wide")

st.markdown("""
<style>
    /* --- PALETA DE CORES OLYMPIKUS --- */
    :root {
        --gold: #D4AF37;
        --gold-light: #FEDC5F;
        --blue-deep: #0a0e1a;
        --blue-accent: #1e3a8a;
        --text-light: #e0e0e0;
        --danger: #ff4b4b;
        --success: #00c853;
    }

    /* Fundo Geral com Degradê Sutil */
    .stApp {
        background: linear-gradient(135deg, var(--blue-deep) 0%, #121212 100%);
        color: var(--text-light);
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* Remove elementos padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {background: transparent;}

    /* --- TÍTULOS E BRANDING --- */
    h1, h2, h3 {
        font-family: 'Montserrat', sans-serif;
        font-weight: 800 !important;
        letter-spacing: -1px;
    }
    .olympus-title {
        background: linear-gradient(to right, var(--gold), var(--gold-light));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-transform: uppercase;
        text-shadow: 0px 0px 20px rgba(212, 175, 55, 0.3);
    }

    /* --- CARDS KPI ESTILO VIDRO (GLASSMORPHISM) --- */
    .kpi-card {
        background: rgba(30, 58, 138, 0.2);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(212, 175, 55, 0.2);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        text-align: left;
        transition: transform 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .kpi-card:hover {
        transform: translateY(-5px);
        border-color: var(--gold);
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; width: 100%; height: 5px;
        background: linear-gradient(to right, var(--gold), var(--blue-accent));
    }
    .kpi-label {
        color: #aaa; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;
    }
    .kpi-value {
        color: #fff; font-size: 2.2rem; font-weight: 900;
    }
    .kpi-sub { font-size: 0.8rem; color: var(--gold); }

    /* --- BOTÕES PERSONALIZADOS --- */
    .stButton > button {
        background: linear-gradient(45deg, var(--blue-accent), var(--blue-deep));
        color: white; font-weight: bold; border: 1px solid var(--blue-accent);
        border-radius: 8px; padding: 12px 24px; transition: all 0.3s;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    .stButton > button:hover {
        background: linear-gradient(45deg, var(--gold), var(--gold-light));
        border-color: var(--gold); color: black; box-shadow: 0 0 15px rgba(212, 175, 55, 0.5);
    }
    /* Botão de Login/Destaque */
    .btn-gold > button {
        background: linear-gradient(45deg, var(--gold), var(--gold-light)) !important;
        color: black !important;
        font-size: 1.1rem;
    }

    /* --- INPUTS E TABELAS --- */
    .stTextInput input, .stNumberInput input, .stSelectbox > div > div {
        background-color: rgba(255,255,255,0.05) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(212, 175, 55, 0.2);
        border-radius: 12px; overflow: hidden;
        background: rgba(30, 58, 138, 0.1);
    }
    [data-testid="stSidebar"] {
        background-color: var(--blue-deep);
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px; background-color: rgba(255,255,255,0.05);
        border-radius: 8px; border: none; color: #aaa;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(45deg, var(--gold), rgba(212, 175, 55, 0.5)) !important;
        color: black !important; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔌 CONEXÃO DATABASE E FUNÇÕES ÚTEIS
# ==============================================================================
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        st.error("⚡ Erro crítico: Falha na conexão com o banco de dados.")
        st.stop()

supabase = init_connection()

# Função para carregar dados e já converter datas
def load_data(table):
    response = supabase.table(table).select("*").execute()
    df = pd.DataFrame(response.data)
    if not df.empty and 'created_at' in df.columns:
        # Converte string para datetime e ajusta fuso (Ex: UTC-3 Brasil)
        df['created_at'] = pd.to_datetime(df['created_at']) - timedelta(hours=3)
    return df

# ==============================================================================
# 🔐 GESTÃO DE SESSÃO (LOGIN)
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'user_data' not in st.session_state:
    st.session_state['user_data'] = {}

def login_screen():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("""
            <div style='text-align: center;'>
                <h1 class='olympus-title' style='font-size: 3.5rem; margin-bottom: 0;'>OLYMPIKUS IPTV</h1>
                <p style='letter-spacing: 2px; color: #aaa; margin-top: -10px;'>PORTAL DE GESTÃO & PARCEIROS</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("### 🏛️ Acesso ao Sistema")
            senha_input = st.text_input("Credencial", type="password", placeholder="Insira sua senha master ou cupom de parceiro...", label_visibility="collapsed")
            
            st.markdown('<div class="btn-gold">', unsafe_allow_html=True)
            btn_entrar = st.button("ENTRAR NO OLIMPO", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            if btn_entrar:
                senha_limpa = senha_input.strip()
                SENHA_ADMIN = st.secrets.get("ADMIN_PASSWORD", "admin123")
                
                if senha_limpa == SENHA_ADMIN:
                    st.session_state['logged_in'] = True
                    st.session_state['user_role'] = 'admin'
                    st.rerun()
                elif supabase:
                    try:
                        response = supabase.table("afiliados").select("*").eq("cupom", senha_limpa.upper()).execute()
                        if response.data:
                            st.session_state['logged_in'] = True
                            st.session_state['user_role'] = 'afiliado'
                            st.session_state['user_data'] = response.data[0]
                            st.rerun()
                        else:
                            st.toast("🚫 Credencial não reconhecida.", icon="🔥")
                    except Exception as e:
                         st.error(f"Erro: {e}")

# ==============================================================================
# 👑 PAINEL DO CHEFE (ADMIN MASTER)
# ==============================================================================
def admin_dashboard():
    # Sidebar com Logo e Menu
    with st.sidebar:
        st.markdown("<h2 class='olympus-title'>OLYMPIKUS</h2>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("### ⚡ Controle Mestre")
        
        # Filtro de Data Global
        filtro_periodo = st.radio("Período de Análise:", ["Todo o Período", "Este Mês", "Hoje"], index=1)
        
        st.markdown("---")
        if st.button("🔒 Sair do Sistema"):
            st.session_state['logged_in'] = False
            st.rerun()

    # Carrega dados
    df_vendas = load_data("vendas")
    df_afiliados = load_data("afiliados")

    # Aplica Filtros de Data
    if not df_vendas.empty:
        now = datetime.now() - timedelta(hours=3)
        if filtro_periodo == "Este Mês":
            df_vendas = df_vendas[(df_vendas['created_at'].dt.month == now.month) & (df_vendas['created_at'].dt.year == now.year)]
        elif filtro_periodo == "Hoje":
            df_vendas = df_vendas[df_vendas['created_at'].dt.date == now.date()]

    # Cabeçalho
    st.markdown(f"<h1 style='font-size: 2.5rem;'>Visão do Olimpo <span style='font-size:1rem; color:#aaa'>| Filtro: {filtro_periodo}</span></h1>", unsafe_allow_html=True)

    # --- KPIS PREMIUM ---
    total_vendas = len(df_vendas) if not df_vendas.empty else 0
    vendas_ativas = df_vendas[df_vendas['status'] == 'Ativo'] if not df_vendas.empty else pd.DataFrame()
    ativos_count = len(vendas_ativas)
    # Calcula faturamento total e comissões a pagar
    faturamento_bruto = vendas_ativas['valor_plano'].sum() if not vendas_ativas.empty else 0
    comissao_pagar = vendas_ativas['valor_comissao'].sum() if not vendas_ativas.empty else 0
    lucro_liquido = faturamento_bruto - comissao_pagar

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"""<div class="kpi-card"><div class="kpi-label">Vendas no Período</div><div class="kpi-value">{total_vendas}</div><div class="kpi-sub">Clientes registrados</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="kpi-card" style="border-color: var(--success);"><div class="kpi-label">Clientes Ativos</div><div class="kpi-value">{ativos_count}</div><div class="kpi-sub">Base pagante atual</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="kpi-card" style="border-color: var(--blue-accent);"><div class="kpi-label">Faturamento Bruto</div><div class="kpi-value">R$ {faturamento_bruto:,.2f}</div><div class="kpi-sub">Entrada total no caixa</div></div>""", unsafe_allow_html=True)
    c4.markdown(f"""<div class="kpi-card" style="border-color: var(--gold);"><div class="kpi-label">Lucro Líquido Est.</div><div class="kpi-value">R$ {lucro_liquido:,.2f}</div><div class="kpi-sub">Após comissões</div></div>""", unsafe_allow_html=True)

    st.markdown("---")

    # --- ABAS PRINCIPAIS ---
    tab_dash, tab_vendas, tab_parceiros, tab_novo = st.tabs(["📈 Métricas & Gráficos", "📋 Gestão de Vendas", "👥 Parceiros & Pagamentos", "✨ Novo Lançamento"])

    with tab_dash:
        if not df_vendas.empty:
            col_g1, col_g2 = st.columns([2, 1])
            with col_g1:
                st.markdown("### Crescimento de Vendas (Linha do Tempo)")
                # Agrupa vendas por dia
                vendas_dia = df_vendas.groupby(df_vendas['created_at'].dt.date).size().reset_index(name='Vendas')
                fig = px.bar(vendas_dia, x='created_at', y='Vendas', color_discrete_sequence=['#D4AF37'])
                fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#aaa', xaxis_title=None)
                st.plotly_chart(fig, use_container_width=True)
            with col_g2:
                st.markdown("### Status da Base")
                status_counts = df_vendas['status'].value_counts().reset_index()
                fig2 = px.pie(status_counts, values='count', names='status', color='status', color_discrete_map={'Ativo':'#00c853', 'Cancelado':'#ff4b4b', 'Pendente':'#D4AF37'}, hole=0.6)
                fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#aaa', showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Sem dados suficientes para gerar gráficos no período selecionado.")

    with tab_vendas:
        st.markdown("### 📋 Tabela de Vendas (Edição Rápida)")
        if not df_vendas.empty:
            # Mostra tabela editável para mudar status
            df_editor = df_vendas[['id', 'created_at', 'nome_cliente', 'cupom', 'status', 'valor_plano']].copy()
            df_editor['created_at'] = df_editor['created_at'].dt.strftime('%d/%m/%Y %H:%M')
            
            edited_df = st.data_editor(
                df_editor,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                    "created_at": st.column_config.TextColumn("Data/Hora", disabled=True),
                    "nome_cliente": "Cliente",
                    "status": st.column_config.SelectboxColumn("Status", options=["Ativo", "Cancelado", "Pendente"], required=True),
                    "valor_plano": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                }
            )
            
            # Botão para salvar alterações (Detectar mudanças seria mais complexo, vamos no simples)
            if st.button("💾 Salvar Alterações de Status"):
                # Compara o original com o editado para achar o que mudou
                # (Simplificação: atualiza todos os IDs visíveis. Em produção, otimize isso.)
                progress_bar = st.progress(0)
                for index, row in edited_df.iterrows():
                    # Atualiza no supabase
                    supabase.table("vendas").update({"status": row['status'], "nome_cliente": row['nome_cliente']}).eq("id", row['id']).execute()
                    progress_bar.progress((index + 1) / len(edited_df))
                st.toast("Status atualizados com sucesso no Olimpo!", icon="✅")
                time.sleep(1)
                st.rerun()

        else:
             st.info("Nenhuma venda encontrada.")

    with tab_parceiros:
        if not df_afiliados.empty and not df_vendas.empty:
            st.markdown("### 💰 Relatório de Comissões por Parceiro")
            # Agrupa vendas por cupom para saber quanto cada um tem a receber
            comissoes = df_vendas[df_vendas['status'] == 'Ativo'].groupby('cupom')['valor_comissao'].sum().reset_index()
            comissoes.rename(columns={'valor_comissao': 'A Pagar'}, inplace=True)
            
            # Junta com os dados do afiliado
            relatorio = pd.merge(df_afiliados, comissoes, left_on='cupom', right_on='cupom', how='left').fillna(0)
            
            st.dataframe(
                relatorio[['nome', 'cupom', 'whatsapp', 'chave_pix', 'A Pagar']],
                use_container_width=True, hide_index=True,
                column_config={"A Pagar": st.column_config.NumberColumn(format="R$ %.2f")}
            )
        else:
            st.warning("Faltam dados de afiliados ou vendas para gerar o relatório.")

    with tab_novo:
        c_venda, c_afiliado = st.columns(2)
        with c_venda:
            with st.container(border=True):
                st.subheader("➕ Registrar Venda Manual")
                with st.form("form_venda_adm"):
                    nome = st.text_input("Nome do Cliente")
                    valor = st.number_input("Valor (R$)", value=35.00, step=5.00)
                    cupom = st.text_input("Cupom Parceiro (Opcional)").upper()
                    if st.form_submit_button("Lançar Venda"):
                        comissao = 15.00 if cupom else 0.00
                        supabase.table("vendas").insert({"nome_cliente": nome, "valor_plano": valor, "cupom": cupom if cupom else None, "status": "Ativo", "valor_comissao": comissao}).execute()
                        st.toast(f"Venda para {nome} lançada!", icon="🚀")
        
        with c_afiliado:
             with st.container(border=True):
                st.subheader("🤝 Cadastrar Novo Parceiro")
                with st.form("form_afiliado_adm"):
                    nome_af = st.text_input("Nome Completo")
                    cupom_af = st.text_input("CUPOM EXCLUSIVO (Ex: ZEUS20)").upper()
                    whats_af = st.text_input("WhatsApp")
                    pix_af = st.text_input("Chave Pix")
                    if st.form_submit_button("Invocar Parceiro"):
                        try:
                            supabase.table("afiliados").insert({"nome": nome_af, "cupom": cupom_af, "whatsapp": whats_af, "chave_pix": pix_af}).execute()
                            st.toast(f"Parceiro {nome_af} adicionado ao Olimpo!", icon="🏛️")
                        except:
                            st.error("Erro: Este CUPOM já está em uso por outro deus.")

# ==============================================================================
# 💼 PAINEL DO AFILIADO (PARCEIRO)
# ==============================================================================
def afiliado_dashboard():
    user = st.session_state['user_data']
    cupom = user['cupom']
    
    with st.sidebar:
         st.markdown(f"<h2 class='olympus-title'>{user['nome']}</h2>", unsafe_allow_html=True)
         st.markdown(f"Cupom Ativo: **{cupom}**")
         st.markdown("---")
         st.markdown("### Central de Apoio")
         st.info("📢 Pagamentos são processados todo dia 10 via Pix.")
         if st.button("🔒 Sair"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.markdown(f"<h1 style='font-size: 2.5rem;'>Seu Império <span style='color:var(--gold)'>Olympikus</span></h1>", unsafe_allow_html=True)
    
    # Carrega vendas SÓ DESSA PESSOA
    df_all = load_data("vendas")
    df = df_all[df_all['cupom'] == cupom] if not df_all.empty else pd.DataFrame()
    
    ativos = df[df['status'] == 'Ativo'] if not df.empty else pd.DataFrame()
    qtd_ativos = len(ativos)
    saldo_receber = ativos['valor_comiss
