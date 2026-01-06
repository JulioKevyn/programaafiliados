import streamlit as st
import pandas as pd
from supabase import create_client
import time
import plotly.express as px
from datetime import datetime, timedelta

# ==============================================================================
# ⚙️ CONFIGURAÇÃO E DESIGN "CLEAN CORPORATE"
# ==============================================================================
st.set_page_config(page_title="Olympikus Admin", page_icon="📊", layout="wide")

st.markdown("""
<style>
    /* Variáveis de Cor - Clean Dark */
    :root {
        --bg-dark: #0e1117;
        --card-bg: #1A1C24;
        --primary: #3B82F6;  /* Azul Corporativo */
        --success: #10B981;  /* Verde Sucesso */
        --text-gray: #9CA3AF;
        --border: #2d2d2d;
    }

    .stApp {
        background-color: var(--bg-dark);
        color: #F3F4F6;
    }
    
    /* Remove decorações padrão */
    header[data-testid="stHeader"] {background: transparent;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Cards de KPI (Simples e Direto) */
    .kpi-card {
        background-color: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    .kpi-label {
        color: var(--text-gray);
        font-size: 0.85rem;
        font-weight: 500;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .kpi-value {
        color: #fff;
        font-size: 1.8rem;
        font-weight: 700;
    }

    /* Títulos */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 600 !important;
    }

    /* Botões */
    .stButton > button {
        background-color: var(--primary);
        color: white;
        border-radius: 6px;
        border: none;
        font-weight: 500;
        padding: 0.5rem 1rem;
        transition: background 0.2s;
    }
    .stButton > button:hover {
        background-color: #2563EB; /* Azul mais escuro */
    }

    /* Tabela e Inputs */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        background-color: var(--card-bg);
    }
    .stTextInput input, .stNumberInput input {
        background-color: #111318;
        border: 1px solid var(--border);
        color: white;
    }
    
    /* Login Box */
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 40px;
        background: var(--card-bg);
        border-radius: 12px;
        border: 1px solid var(--border);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔌 CONEXÃO DATABASE
# ==============================================================================
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        return None

supabase = init_connection()

# Função segura para carregar dados
def load_data(table):
    if not supabase: return pd.DataFrame()
    response = supabase.table(table).select("*").execute()
    df = pd.DataFrame(response.data)
    if not df.empty and 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at']) - timedelta(hours=3)
    return df

# ==============================================================================
# 🔐 LÓGICA DE LOGIN (DEBUGADO)
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None
if 'user_data' not in st.session_state:
    st.session_state['user_data'] = {}

def login_screen():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Visual corporativo
        st.markdown("<h2 style='text-align: center; color: #3B82F6;'>OLYMPIKUS IPTV</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666; font-size: 0.9rem;'>SISTEMA DE GESTÃO</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        with st.container(border=True):
            senha_input = st.text_input("Acesso", type="password", placeholder="Senha Admin ou Cupom de Parceiro")
            if st.button("Entrar", use_container_width=True):
                if not senha_input:
                    st.warning("Digite uma credencial.")
                    return

                credencial = senha_input.strip() # Remove espaços extras
                
                # 1. Tenta Admin (Senha definida nos Secrets)
                SENHA_ADMIN = st.secrets.get("ADMIN_PASSWORD", "admin123")
                
                if credencial == SENHA_ADMIN:
                    st.session_state['logged_in'] = True
                    st.session_state['user_role'] = 'admin'
                    st.rerun()
                
                # 2. Tenta Afiliado (Busca no Banco)
                elif supabase:
                    try:
                        # Tenta buscar EXATAMENTE como digitado e também em UPPERCASE pra garantir
                        # Isso resolve o problema se vc cadastrou 'julio' minúsculo no banco
                        response = supabase.table("afiliados").select("*").or_(f"cupom.eq.{credencial},cupom.eq.{credencial.upper()}").execute()
                        
                        if response.data:
                            st.session_state['logged_in'] = True
                            st.session_state['user_role'] = 'afiliado'
                            st.session_state['user_data'] = response.data[0]
                            st.rerun()
                        else:
                            st.error("Credencial não encontrada.")
                    except Exception as e:
                         st.error(f"Erro de conexão: {e}")

# ==============================================================================
# 📊 DASHBOARD ADMINISTRATIVO
# ==============================================================================
def admin_dashboard():
    with st.sidebar:
        st.markdown("### Menu")
        filtro = st.radio("Período", ["Total", "Este Mês"], index=0)
        st.markdown("---")
        if st.button("Sair"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.markdown("## Visão Geral")

    # Dados
    df_vendas = load_data("vendas")
    df_afiliados = load_data("afiliados")

    # Filtro de tempo simples
    if not df_vendas.empty and filtro == "Este Mês":
        now = datetime.now() - timedelta(hours=3)
        df_vendas = df_vendas[(df_vendas['created_at'].dt.month == now.month) & (df_vendas['created_at'].dt.year == now.year)]

    # KPIS
    total_vendas = len(df_vendas)
    vendas_ativas = df_vendas[df_vendas['status'] == 'Ativo'] if not df_vendas.empty else pd.DataFrame()
    qtd_ativos = len(vendas_ativas)
    # Soma de comissões (Status Ativo apenas)
    total_comissao = vendas_ativas['valor_comissao'].sum() if not vendas_ativas.empty else 0.00
    
    # Cards Clean
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""<div class="kpi-card"><div class="kpi-label">Total Vendas</div><div class="kpi-value">{total_vendas}</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="kpi-card"><div class="kpi-label">Clientes Ativos</div><div class="kpi-value" style="color: #10B981;">{qtd_ativos}</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="kpi-card"><div class="kpi-label">Comissões (Passivo)</div><div class="kpi-value">R$ {total_comissao:.2f}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Vendas", "Parceiros", "Novo Registro"])

    with tab1:
        if not df_vendas.empty:
            # Gráfico de evolução
            vendas_dia = df_vendas.groupby(df_vendas['created_at'].dt.date).size().reset_index(name='Qtd')
            fig = px.bar(vendas_dia, x='created_at', y='Qtd', title="Evolução Diária")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)

            # Tabela Editável
            st.markdown("### Gestão de Clientes")
            df_view = df_vendas[['id', 'created_at', 'nome_cliente', 'cupom', 'status', 'valor_plano']].copy()
            df_view['created_at'] = df_view['created_at'].dt.strftime('%d/%m/%Y')
            
            edited = st.data_editor(
                df_view,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                    "status": st.column_config.SelectboxColumn("Status", options=["Ativo", "Cancelado", "Pendente"], required=True),
                    "valor_plano": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                }
            )
            
            if st.button("Salvar Alterações de Status"):
                for index, row in edited.iterrows():
                    # Update simples (pode ser otimizado)
                    supabase.table("vendas").update({"status": row['status']}).eq("id", row['id']).execute()
                st.success("Dados atualizados.")
                time.sleep(1)
                st.rerun()

    with tab2:
        if not df_afiliados.empty and not df_vendas.empty:
            st.markdown("### Relatório Financeiro")
            # Agrupa
            pagamentos = df_vendas[df_vendas['status'] == 'Ativo'].groupby('cupom')['valor_comissao'].sum().reset_index()
            # Merge
            final = pd.merge(df_afiliados, pagamentos, on='cupom', how='left').fillna(0)
            
            st.dataframe(
                final[['nome', 'cupom', 'whatsapp', 'valor_comissao']],
                column_config={"valor_comissao": st.column_config.NumberColumn("A Pagar (R$)", format="R$ %.2f")},
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Sem dados para relatório.")

    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Registrar Venda")
            with st.form("add_venda"):
                nome = st.text_input("Cliente")
                val = st.number_input("Valor", value=35.00)
                cupom = st.text_input("Cupom (Opcional)").upper()
                if st.form_submit_button("Salvar"):
                    com = 15.00 if cupom else 0.00
                    supabase.table("vendas").insert({
                        "nome_cliente": nome, "valor_plano": val, "cupom": cupom if cupom else None,
                        "status": "Ativo", "valor_comissao": com
                    }).execute()
                    st.success("Venda salva.")
                    time.sleep(0.5)
                    st.rerun()
        
        with c2:
            st.markdown("#### Cadastrar Parceiro")
            with st.form("add_parceiro"):
                p_nome = st.text_input("Nome")
                p_cupom = st.text_input("CUPOM (Único)").upper()
                p_whats = st.text_input("WhatsApp")
                if st.form_submit_button("Cadastrar"):
                    try:
                        supabase.table("afiliados").insert({
                            "nome": p_nome, "cupom": p_cupom, "whatsapp": p_whats
                        }).execute()
                        st.success("Parceiro cadastrado.")
                    except:
                        st.error("Erro: Cupom já existe.")

# ==============================================================================
# 🤝 DASHBOARD AFILIADO
# ==============================================================================
def afiliado_dashboard():
    user = st.session_state['user_data']
    
    with st.sidebar:
        st.markdown(f"### Olá, {user['nome']}")
        st.markdown(f"Cupom: `{user['cupom']}`")
        st.markdown("---")
        if st.button("Sair"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.markdown("## Minha Carteira")

    df_all = load_data("vendas")
    # Filtra apenas dados do usuário
    df = df_all[df_all['cupom'] == user['cupom']] if not df_all.empty else pd.DataFrame()

    ativos = df[df['status'] == 'Ativo'] if not df.empty else pd.DataFrame()
    saldo = ativos['valor_comissao'].sum() if not ativos.empty else 0.00
    
    c1, c2 = st.columns(2)
    c1.markdown(f"""<div class="kpi-card"><div class="kpi-label">Ativos na Base</div><div class="kpi-value">{len(ativos)}</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="kpi-card"><div class="kpi-label">Saldo Disponível</div><div class="kpi-value" style="color:#10B981">R$ {saldo:.2f}</div></div>""", unsafe_allow_html=True)

    st.markdown("### Extrato Detalhado")
    if not df.empty:
        df['created_at'] = df['created_at'].dt.strftime('%d/%m/%Y')
        st.dataframe(
            df[['created_at', 'nome_cliente', 'status', 'valor_comissao']],
            use_container_width=True, hide_index=True,
            column_config={
                "created_at": "Data",
                "nome_cliente": "Cliente",
                "valor_comissao": st.column_config.NumberColumn("Comissão", format="R$ %.2f")
            }
        )
    else:
        st.info("Nenhuma venda registrada com seu cupom ainda.")

# ==============================================================================
# 🚦 ROTEAMENTO
# ==============================================================================
if not st.session_state['logged_in']:
    login_screen()
else:
    if st.session_state['user_role'] == 'admin':
        admin_dashboard()
    elif st.session_state['user_role'] == 'afiliado':
        afiliado_dashboard()
