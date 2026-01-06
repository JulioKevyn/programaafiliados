import streamlit as st
import pandas as pd
from supabase import create_client
import time

# --- CONFIGURAÇÃO INICIAL (Obrigatório ser a primeira linha) ---
st.set_page_config(page_title="Nexus IPTV Admin", page_icon="🚀", layout="wide")

# ==============================================================================
# 🎨 ESTILIZAÇÃO CSS (O SEGREDO DA BELEZA)
# ==============================================================================
st.markdown("""
<style>
    /* Fundo Geral */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* Remove barra superior vermelha padrão do Streamlit */
    header[data-testid="stHeader"] {
        background-color: transparent;
    }

    /* Estilo dos Cards de KPI (Caixinhas de Números) */
    .kpi-card {
        background: linear-gradient(145deg, #1e1e1e, #252525);
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        border-left: 5px solid #00FFA3;
        text-align: center;
        margin-bottom: 20px;
    }
    .kpi-title {
        color: #aaa;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .kpi-value {
        color: #fff;
        font-size: 32px;
        font-weight: bold;
        margin-top: 10px;
    }
    
    /* Botões Personalizados */
    div.stButton > button {
        background-color: #00FFA3;
        color: #000;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 10px 20px;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #00cc82;
        transform: scale(1.02);
        color: #000;
    }

    /* Inputs de Texto */
    .stTextInput input {
        background-color: #1e1e1e;
        color: #fff;
        border: 1px solid #333;
        border-radius: 8px;
    }
    
    /* Tabela */
    [data-testid="stDataFrame"] {
        border: 1px solid #333;
        border-radius: 10px;
        overflow: hidden;
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

# ==============================================================================
# 🧠 LÓGICA DO SISTEMA
# ==============================================================================

# Inicializa variaveis de sessão (Memória do navegador)
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None # 'admin' ou 'afiliado'
if 'user_data' not in st.session_state:
    st.session_state['user_data'] = {}

# --- FUNÇÃO DE LOGIN ---
def login():
    # Centraliza o Login usando colunas vazias
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #00FFA3;'>NEXUS IPTV</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #888;'>Painel de Gestão de Parceiros</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            senha_input = st.text_input("🔑 Código de Acesso / Cupom", type="password", placeholder="Digite sua senha ou cupom...")
            btn_entrar = st.button("ACESSAR SISTEMA", use_container_width=True)

        if btn_entrar:
            senha_limpa = senha_input.strip()
            
            # 1. Verifica se é ADMIN
            SENHA_ADMIN = st.secrets.get("ADMIN_PASSWORD", "admin123")
            if senha_limpa == SENHA_ADMIN:
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = 'admin'
                st.rerun()
            
            # 2. Verifica se é AFILIADO
            elif supabase:
                try:
                    # Busca cupom na tabela de afiliados
                    cupom_upper = senha_limpa.upper()
                    response = supabase.table("afiliados").select("*").eq("cupom", cupom_upper).execute()
                    
                    if response.data:
                        st.session_state['logged_in'] = True
                        st.session_state['user_role'] = 'afiliado'
                        st.session_state['user_data'] = response.data[0] # Guarda dados do usuario
                        st.rerun()
                    else:
                        st.error("🚫 Acesso negado. Código inválido.")
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")

# --- FUNÇÃO DASHBOARD ADMIN ---
def dashboard_admin():
    # Sidebar
    with st.sidebar:
        st.markdown("## 👑 Admin Master")
        st.write("Controle total da operação.")
        if st.button("Sair / Logout"):
            st.session_state['logged_in'] = False
            st.rerun()
    
    st.markdown("## 📊 Visão Geral")
    
    # Busca dados
    if supabase:
        vendas = supabase.table("vendas").select("*").execute().data
        afiliados = supabase.table("afiliados").select("*").execute().data
        
        df_vendas = pd.DataFrame(vendas)
        
        # --- CARDS KPI (HTML PURO) ---
        total_vendas = len(df_vendas) if not df_vendas.empty else 0
        ativos = len(df_vendas[df_vendas['status'] == 'Ativo']) if not df_vendas.empty else 0
        receita_comissao = df_vendas[df_vendas['status'] == 'Ativo']['valor_comissao'].sum() if not df_vendas.empty else 0
        
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Vendas Totais</div>
                <div class="kpi-value">{total_vendas}</div>
            </div>
        """, unsafe_allow_html=True)
        
        c2.markdown(f"""
            <div class="kpi-card" style="border-color: #00C2FF;">
                <div class="kpi-title">Clientes Ativos</div>
                <div class="kpi-value">{ativos}</div>
            </div>
        """, unsafe_allow_html=True)
        
        c3.markdown(f"""
            <div class="kpi-card" style="border-color: #BD00FF;">
                <div class="kpi-title">Comissões a Pagar</div>
                <div class="kpi-value">R$ {receita_comissao:.2f}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # --- ABAS DE AÇÃO ---
        tab_vendas, tab_afiliados, tab_nova_venda = st.tabs(["📋 Histórico de Vendas", "👥 Parceiros", "➕ Registrar Venda"])
        
        with tab_vendas:
            if not df_vendas.empty:
                st.dataframe(
                    df_vendas[['created_at', 'nome_cliente', 'cupom', 'status', 'valor_comissao']].sort_values(by='created_at', ascending=False),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "created_at": "Data",
                        "nome_cliente": "Cliente",
                        "valor_comissao": st.column_config.NumberColumn("Comissão", format="R$ %.2f")
                    }
                )
            else:
                st.info("Nenhuma venda registrada.")

        with tab_afiliados:
            df_af = pd.DataFrame(afiliados)
            if not df_af.empty:
                 st.dataframe(df_af[['nome', 'cupom', 'whatsapp', 'chave_pix']], use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum parceiro cadastrado.")
                
            with st.expander("Cadastrar Novo Parceiro"):
                with st.form("new_partner"):
                    n_nome = st.text_input("Nome")
                    n_cupom = st.text_input("CUPOM (Ex: JOAO10)").upper()
                    n_whats = st.text_input("WhatsApp")
                    n_pix = st.text_input("Pix")
                    if st.form_submit_button("Salvar Parceiro"):
                        try:
                            supabase.table("afiliados").insert({"nome": n_nome, "cupom": n_cupom, "whatsapp": n_whats, "chave_pix": n_pix}).execute()
                            st.success("Sucesso!")
                            time.sleep(1)
                            st.rerun()
                        except:
                            st.error("Erro. Cupom já existe?")

        with tab_nova_venda:
            col_form1, col_form2 = st.columns([1, 1])
            with col_form1:
                with st.container(border=True):
                    st.subheader("Lançamento Manual")
                    v_nome = st.text_input("Nome do Cliente")
                    v_plano = st.number_input("Valor Plano", value=35.00)
                    v_cupom = st.text_input("Cupom do Parceiro (Opcional)").upper()
                    
                    if st.button("💾 Confirmar Venda", use_container_width=True):
                        if supabase:
                            comissao = 15.00 if v_cupom else 0.00
                            supabase.table("vendas").insert({
                                "nome_cliente": v_nome,
                                "valor_plano": v_plano,
                                "cupom": v_cupom if v_cupom else None,
                                "status": "Ativo",
                                "valor_comissao": comissao
                            }).execute()
                            st.success("Venda registrada!")
                            time.sleep(1)
                            st.rerun()

# --- FUNÇÃO DASHBOARD AFILIADO ---
def dashboard_afiliado():
    user = st.session_state['user_data']
    cupom = user['cupom']
    nome = user['nome']
    
    with st.sidebar:
        st.markdown(f"## Olá, {nome}")
        st.write(f"Cupom: **{cupom}**")
        if st.button("Sair"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.markdown(f"## 🚀 Seus Resultados")
    
    if supabase:
        response = supabase.table("vendas").select("*").eq("cupom", cupom).execute()
        df = pd.DataFrame(response.data)
        
        ativos = 0
        comissao = 0.00
        
        if not df.empty:
            ativos = len(df[df['status'] == 'Ativo'])
            comissao = df[df['status'] == 'Ativo']['valor_comissao'].sum()
        
        c1, c2 = st.columns(2)
        c1.markdown(f"""
            <div class="kpi-card" style="border-color: #00C2FF;">
                <div class="kpi-title">Clientes Ativos</div>
                <div class="kpi-value">{ativos}</div>
            </div>
        """, unsafe_allow_html=True)
        
        c2.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">Saldo a Receber</div>
                <div class="kpi-value">R$ {comissao:.2f}</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📜 Detalhe das Vendas")
        if not df.empty:
            st.dataframe(
                df[['created_at', 'nome_cliente', 'status']], 
                use_container_width=True,
                hide_index=True,
                column_config={"created_at": "Data", "nome_cliente": "Cliente"}
            )
        else:
            st.info("Você ainda não tem vendas ativas. Divulgue seu cupom!")

# ==============================================================================
# 🚦 ROTEADOR DE PÁGINAS
# ==============================================================================

if not st.session_state['logged_in']:
    login()
else:
    if st.session_state['user_role'] == 'admin':
        dashboard_admin()
    elif st.session_state['user_role'] == 'afiliado':
        dashboard_afiliado()
