import streamlit as st
import pandas as pd
from supabase import create_client
import time
import plotly.express as px
from datetime import datetime, timedelta

# ==============================================================================
# 🎨 CONFIGURAÇÃO VISUAL "CYBER VIOLET" (PREMIUM STREAMING STYLE)
# ==============================================================================
st.set_page_config(page_title="Nexus TV", page_icon="🟣", layout="wide")

st.markdown("""
<style>
    /* --- VARIÁVEIS DE COR --- */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --bg-gradient: linear-gradient(to bottom, #0f0c29, #302b63, #24243e);
        --glass-bg: rgba(255, 255, 255, 0.05);
        --glass-border: 1px solid rgba(255, 255, 255, 0.1);
        --text-white: #ffffff;
        --text-gray: #b3b3b3;
    }

    /* Fundo Geral da Aplicação */
    .stApp {
        background: var(--bg-gradient);
        color: var(--text-white);
    }
    
    /* Esconder cabeçalhos padrão */
    header, footer { visibility: hidden; }

    /* --- CARDS DE KPI (VIDRO) --- */
    .metric-card {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: var(--glass-border);
        border-radius: 20px;
        padding: 25px;
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: rgba(118, 75, 162, 0.5);
    }
    .metric-label {
        color: var(--text-gray);
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        background: -webkit-linear-gradient(#fff, #a5a5a5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* --- BOTÕES MODERNOS --- */
    .stButton > button {
        background: var(--primary-gradient);
        color: white;
        border: none;
        border-radius: 50px; /* Redondinho */
        padding: 10px 25px;
        font-weight: 600;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 15px rgba(118, 75, 162, 0.4);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(118, 75, 162, 0.6);
        color: white;
    }

    /* --- INPUTS ESTILIZADOS --- */
    .stTextInput input, .stNumberInput input {
        background-color: rgba(0,0,0,0.3) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 12px !important;
        color: white !important;
        padding: 10px;
    }
    .stTextInput input:focus {
        border-color: #764ba2 !important;
        box-shadow: 0 0 10px rgba(118, 75, 162, 0.3);
    }

    /* --- ABAS (TABS) --- */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(0,0,0,0.3);
        padding: 5px;
        border-radius: 50px;
        gap: 10px;
        display: inline-flex;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border: none;
        color: #888;
        border-radius: 50px;
        padding: 0 20px;
    }
    .stTabs [aria-selected="true"] {
        background: var(--primary-gradient) !important;
        color: white !important;
        font-weight: bold;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }

    /* --- TITULOS --- */
    h1, h2, h3 {
        font-family: 'Montserrat', sans-serif;
    }
    .brand-text {
        font-size: 3rem;
        font-weight: 900;
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔌 CONEXÃO E LÓGICA (MANTIDA IGUAL, POIS ESTAVA PERFEITA)
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

def load_data(table):
    if not supabase: return pd.DataFrame()
    try:
        response = supabase.table(table).select("*").execute()
        df = pd.DataFrame(response.data)
        
        # Cria colunas vazias se tabela estiver zerada
        if df.empty:
            if table == 'vendas': return pd.DataFrame(columns=['id', 'created_at', 'nome_cliente', 'cupom', 'status', 'valor_plano', 'valor_comissao'])
            if table == 'afiliados': return pd.DataFrame(columns=['id', 'created_at', 'nome', 'cupom', 'whatsapp', 'chave_pix'])
            
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at']) - timedelta(hours=3)
        return df
    except:
        return pd.DataFrame()

# ==============================================================================
# 🚦 TELA DE LOGIN (NOVO DESIGN)
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'role' not in st.session_state:
    st.session_state['role'] = None
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = {}

def login_page():
    c1, c2, c3 = st.columns([1, 1.5, 1]) # Centraliza
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Logo Texto Gigante
        st.markdown("<div class='brand-text'>NEXUS TV</div>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#b3b3b3; margin-top:-10px; margin-bottom: 30px;'>SISTEMA DE GESTÃO INTELIGENTE</p>", unsafe_allow_html=True)
        
        # Caixa de Login Estilizada
        with st.container(border=True):
            st.markdown("### Bem-vindo")
            
            tabs = st.tabs(["Sou Parceiro", "Sou Admin"])
            
            with tabs[0]: # Login Parceiro
                st.write("")
                cupom = st.text_input("Insira seu Cupom de Acesso", placeholder="Ex: JULIO10").strip().upper()
                st.write("")
                if st.button("ACESSAR PAINEL PARCEIRO", use_container_width=True):
                    if supabase and cupom:
                        try:
                            res = supabase.table("afiliados").select("*").eq("cupom", cupom).execute()
                            if res.data:
                                st.session_state['logged_in'] = True
                                st.session_state['role'] = 'afiliado'
                                st.session_state['user_info'] = res.data[0]
                                st.rerun()
                            else:
                                st.error("Cupom inválido.")
                        except:
                            st.error("Erro de conexão.")

            with tabs[1]: # Login Admin
                st.write("")
                senha = st.text_input("Senha Mestra", type="password")
                st.write("")
                if st.button("ACESSAR ADMIN", use_container_width=True):
                    SENHA_ADMIN = st.secrets.get("ADMIN_PASSWORD", "admin123")
                    if senha == SENHA_ADMIN:
                        st.session_state['logged_in'] = True
                        st.session_state['role'] = 'admin'
                        st.rerun()
                    else:
                        st.error("Senha incorreta.")

# ==============================================================================
# 👑 DASHBOARD ADMIN (VISUAL NOVO)
# ==============================================================================
def admin_dash():
    # Header minimalista
    c1, c2 = st.columns([8, 1])
    with c1: st.title("Dashboard Admin")
    with c2: 
        if st.button("SAIR"): 
            st.session_state['logged_in'] = False
            st.rerun()

    df_vendas = load_data('vendas')
    df_afiliados = load_data('afiliados')

    # Métricas
    ativos = df_vendas[df_vendas['status'] == 'Ativo'] if not df_vendas.empty else pd.DataFrame()
    receita = ativos['valor_plano'].sum() if not ativos.empty else 0
    comissao_total = ativos['valor_comissao'].sum() if not ativos.empty else 0
    
    # Cards Estilizados
    kc1, kc2, kc3, kc4 = st.columns(4)
    kc1.markdown(f"""<div class="metric-card"><div class="metric-label">Vendas Totais</div><div class="metric-value">{len(df_vendas)}</div></div>""", unsafe_allow_html=True)
    kc2.markdown(f"""<div class="metric-card"><div class="metric-label">Ativos Agora</div><div class="metric-value" style="color:#4ade80">{len(ativos)}</div></div>""", unsafe_allow_html=True)
    kc3.markdown(f"""<div class="metric-card"><div class="metric-label">Faturamento</div><div class="metric-value">R${receita:.0f}</div></div>""", unsafe_allow_html=True)
    kc4.markdown(f"""<div class="metric-card"><div class="metric-label">Comissões</div><div class="metric-value">R${comissao_total:.0f}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    t1, t2, t3 = st.tabs(["📊 Gestão de Vendas", "👥 Parceiros & Pagamentos", "⚡ Ações Rápidas"])

    with t1:
        if not df_vendas.empty:
            # Gráfico Roxo
            vendas_dia = df_vendas.groupby(df_vendas['created_at'].dt.date).size().reset_index(name='Qtd')
            fig = px.area(vendas_dia, x='created_at', y='Qtd', title="Tendência de Vendas")
            fig.update_traces(line_color='#764ba2', fill_color='rgba(118, 75, 162, 0.3)')
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("### Detalhes")
            df_edit = df_vendas[['id', 'created_at', 'nome_cliente', 'cupom', 'status', 'valor_plano']].copy()
            df_edit['created_at'] = df_edit['created_at'].dt.strftime('%d/%m/%Y')
            
            edited = st.data_editor(
                df_edit,
                hide_index=True, use_container_width=True,
                column_config={
                    "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                    "status": st.column_config.SelectboxColumn("Status", options=["Ativo", "Cancelado", "Pendente"], required=True),
                    "valor_plano": st.column_config.NumberColumn("R$", format="R$ %.2f")
                }
            )
            if st.button("SALVAR ALTERAÇÕES DE STATUS"):
                for i, row in edited.iterrows():
                    supabase.table("vendas").update({"status": row['status']}).eq("id", row['id']).execute()
                st.success("Atualizado!")
                time.sleep(1)
                st.rerun()

    with t2:
        if not df_afiliados.empty and not ativos.empty:
            pagamentos = ativos.groupby('cupom')['valor_comissao'].sum().reset_index()
            final = pd.merge(df_afiliados, pagamentos, on='cupom', how='left').fillna(0)
            st.dataframe(
                final[['nome', 'cupom', 'whatsapp', 'valor_comissao']],
                column_config={"valor_comissao": st.column_config.NumberColumn("A Pagar", format="R$ %.2f")},
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Sem dados financeiros.")

    with t3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Nova Venda")
            with st.form("nv"):
                n = st.text_input("Cliente")
                v = st.number_input("Valor", value=35.00)
                c = st.text_input("Cupom (Opcional)").upper()
                if st.form_submit_button("LANÇAR VENDA"):
                    com = 15.00 if c else 0.00
                    supabase.table("vendas").insert({"nome_cliente": n, "valor_plano": v, "cupom": c if c else None, "status": "Ativo", "valor_comissao": com}).execute()
                    st.success("Feito!")
                    time.sleep(1)
                    st.rerun()
        with c2:
            st.markdown("#### Novo Parceiro")
            with st.form("np"):
                pn = st.text_input("Nome")
                pc = st.text_input("Cupom").upper()
                if st.form_submit_button("CRIAR PARCEIRO"):
                    try:
                        supabase.table("afiliados").insert({"nome": pn, "cupom": pc}).execute()
                        st.success("Criado!")
                    except:
                        st.error("Cupom existe.")

# ==============================================================================
# 🤝 DASHBOARD AFILIADO (VISUAL NOVO)
# ==============================================================================
def affiliate_dash():
    user = st.session_state['user_info']
    c1, c2 = st.columns([8, 1])
    with c1: st.title(f"Olá, {user['nome']}")
    with c2: 
        if st.button("SAIR"): 
            st.session_state['logged_in'] = False
            st.rerun()

    df_all = load_data('vendas')
    df = df_all[df_all['cupom'] == user['cupom']] if not df_all.empty else pd.DataFrame()
    ativos = df[df['status'] == 'Ativo'] if not df.empty else pd.DataFrame()
    saldo = ativos['valor_comissao'].sum() if not ativos.empty else 0.00

    k1, k2 = st.columns(2)
    k1.markdown(f"""<div class="metric-card"><div class="metric-label">Clientes Ativos</div><div class="metric-value">{len(ativos)}</div></div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class="metric-card"><div class="metric-label">Saldo Disponível</div><div class="metric-value" style="color:#a78bfa">R${saldo:.2f}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Extrato de Vendas")
    
    if not df.empty:
        df['created_at'] = df['created_at'].dt.strftime('%d/%m/%Y')
        st.dataframe(
            df[['created_at', 'nome_cliente', 'status', 'valor_comissao']],
            use_container_width=True, hide_index=True,
            column_config={
                "status": st.column_config.TextColumn("Status"),
                "valor_comissao": st.column_config.NumberColumn("Comissão", format="R$ %.2f")
            }
        )
    else:
        st.info("Nenhuma venda ainda.")

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
