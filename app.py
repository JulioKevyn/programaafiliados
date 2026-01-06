import streamlit as st
import pandas as pd
from supabase import create_client
import time
import plotly.express as px
from datetime import datetime, timedelta

# ==============================================================================
# ⚙️ SETUP E VISUAL "DARK NEON"
# ==============================================================================
st.set_page_config(page_title="Gestão IPTV", page_icon="📺", layout="wide")

st.markdown("""
<style>
    /* Reset Geral */
    .stApp { background-color: #0E1117; color: #E0E0E0; }
    header, footer { visibility: hidden; }

    /* Estilo das Abas de Login */
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center;
        gap: 20px;
        background-color: #161B22;
        padding: 10px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        width: 150px;
        border-radius: 8px;
        background-color: transparent;
        color: #888;
        font-weight: 600;
        border: 1px solid #333;
    }
    .stTabs [aria-selected="true"] {
        background-color: #238636 !important; /* Verde GitHub/Hacker */
        color: white !important;
        border: none;
    }

    /* Cards KPI */
    .kpi-box {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .kpi-title { font-size: 12px; text-transform: uppercase; color: #8B949E; letter-spacing: 1px; }
    .kpi-val { font-size: 28px; font-weight: 700; color: #F0F6FC; margin-top: 5px; }
    .kpi-green { color: #3FB950 !important; } /* Verde */
    .kpi-gold { color: #D29922 !important; }  /* Dourado */

    /* Tabelas e Inputs */
    [data-testid="stDataFrame"] { border: 1px solid #30363D; }
    .stTextInput input, .stNumberInput input {
        background-color: #0D1117; border: 1px solid #30363D; color: white;
    }
    .stButton button {
        width: 100%; font-weight: bold; border-radius: 6px;
    }
    
    /* Login Container Centered */
    .login-wrapper {
        max-width: 500px; margin: 0 auto; padding-top: 50px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔌 CONEXÃO E FUNÇÕES SEGURAS
# ==============================================================================
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        return None

supabase = init_connection()

def load_data(table):
    if not supabase: return pd.DataFrame()
    try:
        response = supabase.table(table).select("*").execute()
        df = pd.DataFrame(response.data)
        
        # --- CORREÇÃO DO KEYERROR ---
        # Se a tabela estiver vazia, cria as colunas vazias pra não dar erro
        if df.empty:
            if table == 'vendas':
                return pd.DataFrame(columns=['id', 'created_at', 'nome_cliente', 'cupom', 'status', 'valor_plano', 'valor_comissao'])
            if table == 'afiliados':
                return pd.DataFrame(columns=['id', 'created_at', 'nome', 'cupom', 'whatsapp', 'chave_pix'])
        
        # Converte datas se existirem
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']) - timedelta(hours=3)
            
        return df
    except Exception as e:
        st.error(f"Erro ao carregar {table}: {e}")
        return pd.DataFrame()

# ==============================================================================
# 🚦 CONTROLADOR DE LOGIN (SEPARADO!)
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'role' not in st.session_state:
    st.session_state['role'] = None
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = {}

def login_page():
    # Cabeçalho Central
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #3FB950;'>NEXUS IPTV</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #8B949E;'>SISTEMA INTEGRADO DE GESTÃO</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- SISTEMA DE ABAS PARA LOGIN ---
        tab_parceiro, tab_admin = st.tabs(["Sou Parceiro", "Sou Admin"])
        
        with tab_parceiro:
            with st.container(border=True):
                st.markdown("### 🤝 Acesso do Afiliado")
                cupom_input = st.text_input("Digite seu Cupom", placeholder="Ex: JULIO10").strip().upper()
                if st.button("Acessar Painel"):
                    if not supabase:
                        st.error("Erro de conexão com Banco de Dados.")
                    elif not cupom_input:
                        st.warning("Digite o cupom.")
                    else:
                        try:
                            # Busca o cupom
                            res = supabase.table("afiliados").select("*").eq("cupom", cupom_input).execute()
                            if res.data:
                                st.session_state['logged_in'] = True
                                st.session_state['role'] = 'afiliado'
                                st.session_state['user_info'] = res.data[0]
                                st.rerun()
                            else:
                                st.error("Cupom não encontrado. Fale com o suporte.")
                        except Exception as e:
                            st.error(f"Erro técnico: {e}")

        with tab_admin:
            with st.container(border=True):
                st.markdown("### 🔐 Acesso Administrativo")
                senha_input = st.text_input("Senha Master", type="password")
                if st.button("Entrar como Admin"):
                    SENHA_ADMIN = st.secrets.get("ADMIN_PASSWORD", "admin123")
                    if senha_input == SENHA_ADMIN:
                        st.session_state['logged_in'] = True
                        st.session_state['role'] = 'admin'
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")

# ==============================================================================
# 👑 DASHBOARD ADMIN (COMPLETO)
# ==============================================================================
def admin_dash():
    # Sidebar
    with st.sidebar:
        st.markdown("### 🛡️ Admin")
        if st.button("Sair"):
            st.session_state['logged_in'] = False
            st.rerun()
            
    st.markdown("## Painel de Controle")
    
    # Carregamento seguro
    df_vendas = load_data('vendas')
    df_afiliados = load_data('afiliados')
    
    # Validação Extra para evitar KEYERROR
    required_cols = ['status', 'valor_plano', 'valor_comissao', 'id', 'nome_cliente', 'cupom']
    for col in required_cols:
        if col not in df_vendas.columns:
            st.error(f"⚠️ A coluna '{col}' está faltando no banco de dados. Rode o SQL de correção!")
            st.stop()

    # Métricas
    ativos = df_vendas[df_vendas['status'] == 'Ativo']
    faturamento = ativos['valor_plano'].sum()
    comissoes = ativos['valor_comissao'].sum()
    liquido = faturamento - comissoes

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-box'><div class='kpi-title'>Vendas Totais</div><div class='kpi-val'>{len(df_vendas)}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-box'><div class='kpi-title'>Ativos</div><div class='kpi-val kpi-green'>{len(ativos)}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-box'><div class='kpi-title'>Faturamento</div><div class='kpi-val'>R$ {faturamento:.0f}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-box'><div class='kpi-title'>Lucro Líquido</div><div class='kpi-val kpi-green'>R$ {liquido:.0f}</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📋 Gestão de Vendas", "👥 Parceiros", "➕ Novo Lançamento"])
    
    with tab1:
        if not df_vendas.empty:
            st.markdown("### Base de Clientes")
            # Editor de Dados
            df_edit = df_vendas[['id', 'created_at', 'nome_cliente', 'cupom', 'status', 'valor_plano']].copy()
            df_edit['created_at'] = df_edit['created_at'].dt.strftime('%d/%m/%Y')
            
            edited_df = st.data_editor(
                df_edit,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                    "status": st.column_config.SelectboxColumn("Status", options=["Ativo", "Cancelado", "Pendente"], required=True),
                    "valor_plano": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                }
            )
            
            if st.button("💾 Salvar Alterações"):
                with st.spinner("Salvando..."):
                    for i, row in edited_df.iterrows():
                        supabase.table("vendas").update({"status": row['status']}).eq("id", row['id']).execute()
                st.success("Atualizado!")
                time.sleep(1)
                st.rerun()
        else:
            st.info("Nenhuma venda registrada.")

    with tab2:
        if not df_afiliados.empty:
            st.markdown("### Financeiro Afiliados")
            # Agrupar comissões
            if not ativos.empty:
                pagamentos = ativos.groupby('cupom')['valor_comissao'].sum().reset_index()
                report = pd.merge(df_afiliados, pagamentos, on='cupom', how='left').fillna(0)
                st.dataframe(
                    report[['nome', 'cupom', 'whatsapp', 'valor_comissao']],
                    column_config={"valor_comissao": st.column_config.NumberColumn("A Pagar", format="R$ %.2f")},
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("Sem vendas ativas para gerar comissões.")
        else:
            st.info("Nenhum parceiro cadastrado.")

    with tab3:
        c_v, c_p = st.columns(2)
        with c_v:
            st.markdown("#### Registrar Venda Manual")
            with st.form("nova_venda"):
                nome = st.text_input("Cliente")
                valor = st.number_input("Valor", value=35.00)
                cupom = st.text_input("Cupom Parceiro (Opcional)").upper()
                if st.form_submit_button("Lançar Venda"):
                    comissao = 15.00 if cupom else 0.00
                    supabase.table("vendas").insert({
                        "nome_cliente": nome,
                        "valor_plano": valor,
                        "cupom": cupom if cupom else None,
                        "valor_comissao": comissao,
                        "status": "Ativo"
                    }).execute()
                    st.success("Venda Criada!")
                    time.sleep(0.5)
                    st.rerun()

        with c_p:
            st.markdown("#### Cadastrar Novo Parceiro")
            with st.form("novo_parceiro"):
                p_nome = st.text_input("Nome")
                p_cupom = st.text_input("CUPOM (Único)").upper()
                p_whats = st.text_input("WhatsApp")
                if st.form_submit_button("Criar Parceiro"):
                    try:
                        supabase.table("afiliados").insert({
                            "nome": p_nome, "cupom": p_cupom, "whatsapp": p_whats
                        }).execute()
                        st.success("Parceiro Criado!")
                    except:
                        st.error("Cupom já existe.")

# ==============================================================================
# 🤝 DASHBOARD AFILIADO
# ==============================================================================
def affiliate_dash():
    user = st.session_state['user_info']
    
    with st.sidebar:
        st.markdown(f"### Olá, {user['nome']}")
        st.write(f"Cupom: **{user['cupom']}**")
        if st.button("Sair"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.markdown("## Minha Área")
    
    df_all = load_data('vendas')
    # Filtra dados do usuário
    df = df_all[df_all['cupom'] == user['cupom']] if not df_all.empty else pd.DataFrame()
    
    ativos = df[df['status'] == 'Ativo'] if not df.empty else pd.DataFrame()
    saldo = ativos['valor_comissao'].sum() if not ativos.empty else 0.00

    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='kpi-box'><div class='kpi-title'>Clientes Ativos</div><div class='kpi-val kpi-green'>{len(ativos)}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-box'><div class='kpi-title'>Saldo Disponível</div><div class='kpi-val kpi-gold'>R$ {saldo:.2f}</div></div>", unsafe_allow_html=True)
    
    st.markdown("### Extrato")
    if not df.empty:
        df['created_at'] = df['created_at'].dt.strftime('%d/%m/%Y')
        st.dataframe(
            df[['created_at', 'nome_cliente', 'status', 'valor_comissao']],
            column_config={
                "status": st.column_config.TextColumn("Status"),
                "valor_comissao": st.column_config.NumberColumn("Comissão", format="R$ %.2f")
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Nenhuma venda encontrada.")
        st.markdown("💡 **Dica:** Divulgue seu cupom para começar a vender!")

# ==============================================================================
# 🚦 ROTEADOR
# ==============================================================================
if not st.session_state['logged_in']:
    login_page()
else:
    if st.session_state['role'] == 'admin':
        admin_dash()
    elif st.session_state['role'] == 'afiliado':
        affiliate_dash()
