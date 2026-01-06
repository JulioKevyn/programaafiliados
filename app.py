import streamlit as st
import pandas as pd
from supabase import create_client
import time
import plotly.express as px
from datetime import datetime, timedelta

# ==============================================================================
# ⚙️ SETUP E ESTILO CORPORATIVO
# ==============================================================================
st.set_page_config(page_title="Gestor Pro", page_icon="💼", layout="wide")

st.markdown("""
<style>
    /* Estilo Global Limpo */
    .stApp { background-color: #0E1117; color: #FAFAFA; font-family: 'Segoe UI', sans-serif; }
    
    /* Cards KPI - Estilo Banco/Fintech */
    .metric-card {
        background-color: #1A1C24;
        border: 1px solid #2D3748;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #3182CE; /* Azul Profissional */
    }
    .metric-title { font-size: 14px; color: #A0AEC0; font-weight: 500; text-transform: uppercase; }
    .metric-value { font-size: 28px; font-weight: 700; color: #FFF; margin-top: 5px; }
    .metric-sub { font-size: 12px; color: #718096; margin-top: 4px; }
    
    /* Cores de Status Sóbrias */
    .status-active { color: #48BB78; font-weight: 600; } /* Verde suave */
    .status-warning { color: #ECC94B; font-weight: 600; } /* Amarelo */
    .status-danger { color: #F56565; font-weight: 600; } /* Vermelho suave */

    /* Tabelas e Inputs */
    .stDataFrame { border: 1px solid #2D3748; }
    .stTextInput input, .stNumberInput input, .stSelectbox {
        border-radius: 6px; border: 1px solid #4A5568; background-color: #1A202C; color: white;
    }
    
    /* Botões Padrão Azul */
    .stButton button {
        background-color: #3182CE; color: white; border: none; font-weight: 600;
        border-radius: 6px; padding: 0.5rem 1rem;
    }
    .stButton button:hover { background-color: #2B6CB0; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🔌 CONEXÃO E DADOS (COM CORREÇÃO DE DATA)
# ==============================================================================
@st.cache_resource
def init_connection():
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        if not url or not key: return None
        return create_client(url, key)
    except: return None

supabase = init_connection()

def get_data(table, order_col='created_at'):
    if not supabase: return pd.DataFrame()
    try:
        res = supabase.table(table).select("*").order(order_col, desc=True).execute()
        df = pd.DataFrame(res.data)
        
        # Correção Crítica de Fusos Horários e Datas
        cols_date = ['created_at', 'data_expiracao']
        for col in cols_date:
            if not df.empty and col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                # Remove fuso horário para evitar conflito com datetime.now()
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    if df[col].dt.tz is not None:
                        df[col] = df[col].dt.tz_localize(None)
                        
        # Ajuste manual de -3h (Brasilia) se necessário após remover TZ
        if not df.empty and 'created_at' in df.columns:
             df['created_at'] = df['created_at'] - timedelta(hours=3)
             
        return df
    except Exception: return pd.DataFrame()

def render_metric(title, value, sub="", color="#3182CE"):
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: {color};">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

def calcular_status_tempo(data_exp):
    if pd.isnull(data_exp): return "Sem Data", "#A0AEC0"
    hoje = datetime.now() # Agora ambas as datas não tem fuso horário
    delta = (data_exp - hoje).days
    
    if delta < 0: return "VENCIDO", "#F56565"
    if delta <= 3: return f"VENCE EM {delta} DIAS", "#ECC94B"
    return "ATIVO", "#48BB78"

# ==============================================================================
# 🔐 LOGIN
# ==============================================================================
if 'logged_in' not in st.session_state: 
    st.session_state.update({'logged_in': False, 'role': None, 'user': {}})

def login_ui():
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<br><h2 style='text-align: center;'>Acesso ao Sistema</h2><br>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Área do Parceiro", "Administração"])
        
        with tab1:
            with st.form("login_parceiro"):
                cupom = st.text_input("Insira seu Cupom").strip().upper()
                if st.form_submit_button("Entrar", use_container_width=True):
                    if not supabase: st.error("Erro BD"); return
                    res = supabase.table("afiliados").select("*").eq("cupom", cupom).execute()
                    if res.data:
                        st.session_state.update({'logged_in': True, 'role': 'afiliado', 'user': res.data[0]})
                        st.rerun()
                    else: st.error("Cupom não encontrado.")
        
        with tab2:
            with st.form("login_admin"):
                senha = st.text_input("Senha Admin", type="password")
                if st.form_submit_button("Acessar", use_container_width=True):
                    if senha == st.secrets.get("ADMIN_PASSWORD", "admin123"):
                        st.session_state.update({'logged_in': True, 'role': 'admin'})
                        st.rerun()
                    else: st.error("Senha incorreta.")

# ==============================================================================
# 🛡️ ADMIN DASHBOARD
# ==============================================================================
def admin_dash():
    with st.sidebar:
        st.header("Gestão")
        menu = st.radio("Menu", ["Dashboard", "Vendas", "Planos", "Parceiros", "Marketing", "Financeiro"])
        st.markdown("---")
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # Carregamento de dados
    df_vendas = get_data('vendas')
    df_afiliados = get_data('afiliados')
    df_planos = get_data('planos', 'valor')
    df_saques = get_data('saques')

    if menu == "Dashboard":
        st.title("Visão Geral")
        
        # Filtros e Lógica Segura de Data
        col_d1, col_d2 = st.columns([4, 1])
        with col_d2:
            periodo = st.selectbox("Filtro", ["7 Dias", "30 Dias", "Este Mês", "Total"], index=1)
        
        if not df_vendas.empty:
            hoje = datetime.now()
            # Garante que 'hoje' não tem fuso horário
            
            if periodo == "7 Dias": data_corte = hoje - timedelta(days=7)
            elif periodo == "30 Dias": data_corte = hoje - timedelta(days=30)
            elif periodo == "Este Mês": data_corte = hoje.replace(day=1)
            else: data_corte = hoje - timedelta(days=3650)
            
            # Filtro com erro corrigido (agora ambas as colunas são naive datetime)
            df_filt = df_vendas[df_vendas['created_at'] >= data_corte]
            
            fat = df_filt['valor_plano'].sum()
            lucro = fat - df_filt['valor_comissao'].sum()
            
            # Vencimentos Próximos
            vencendo = 0
            if 'data_expiracao' in df_vendas.columns:
                # Filtrar apenas datas validas
                validas = df_vendas[df_vendas['data_expiracao'].notna()]
                mask = (validas['data_expiracao'] <= (hoje + timedelta(days=3))) & (validas['data_expiracao'] >= hoje)
                vencendo = len(validas[mask])
            
            k1, k2, k3, k4 = st.columns(4)
            with k1: render_metric("Vendas", len(df_filt), "No período")
            with k2: render_metric("Receita", f"R$ {fat:,.2f}", "Bruta")
            with k3: render_metric("Líquido", f"R$ {lucro:,.2f}", "Real", "#48BB78")
            with k4: render_metric("A Vencer", vencendo, "Próx. 3 dias", "#ECC94B")
            
            st.markdown("---")
            
            g1, g2 = st.columns([2, 1])
            with g1:
                st.subheader("Receita Diária")
                if not df_filt.empty:
                    daily = df_filt.groupby(df_filt['created_at'].dt.date)['valor_plano'].sum().reset_index()
                    fig = px.bar(daily, x='created_at', y='valor_plano')
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    fig.update_traces(marker_color='#3182CE')
                    st.plotly_chart(fig, use_container_width=True)
            
            with g2:
                st.subheader("Planos")
                if not df_filt.empty and 'plano_nome' in df_filt.columns:
                    top = df_filt['plano_nome'].value_counts().reset_index()
                    fig2 = px.pie(top, values='count', names='plano_nome', hole=0.5)
                    st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Sem dados registrados.")

    elif menu == "Vendas":
        st.title("Controle de Assinaturas")
        tab_new, tab_list = st.tabs(["Nova Venda", "Lista Clientes"])
        
        with tab_new:
            with st.form("form_venda"):
                c1, c2 = st.columns(2)
                nome = c1.text_input("Cliente")
                whats = c2.text_input("WhatsApp")
                
                c3, c4 = st.columns(2)
                # Planos
                mapa_planos = {f"{r['nome']} (R$ {r['valor']})": r for i, r in df_planos.iterrows()} if not df_planos.empty else {}
                plano_key = c3.selectbox("Plano", list(mapa_planos.keys()) if mapa_planos else ["Manual"])
                cupom_in = c4.text_input("Cupom Parceiro").upper()
                
                if st.form_submit_button("Salvar Venda"):
                    if mapa_planos:
                        p_dados = mapa_planos[plano_key]
                        val, dias, p_nome, comissao = float(p_dados['valor']), int(p_dados['dias']), p_dados['nome'], float(p_dados['comissao_fixa'])
                    else:
                        val, dias, p_nome, comissao = 35.0, 30, "Manual", 0.0
                    
                    if cupom_in:
                        chk = supabase.table("afiliados").select("*").eq("cupom", cupom_in).execute()
                        if not chk.data: 
                            st.warning("Cupom inválido! Sem comissão."); cupom_in = None; comissao = 0
                        elif comissao == 0: comissao = 15.0 # Fallback
                    
                    exp = datetime.now() + timedelta(days=dias)
                    supabase.table("vendas").insert({
                        "nome_cliente": nome, "valor_plano": val, "cupom": cupom_in,
                        "valor_comissao": comissao, "plano_nome": p_nome,
                        "data_expiracao": exp.strftime('%Y-%m-%d'), "status": "Ativo"
                    }).execute()
                    st.success("Registrado!"); time.sleep(1); st.rerun()

        with tab_list:
            if not df_vendas.empty:
                search = st.text_input("Buscar Cliente")
                df_s = df_vendas[df_vendas['nome_cliente'].str.contains(search, case=False, na=False)] if search else df_vendas
                
                for i, row in df_s.iterrows():
                    st_txt, st_cor = calcular_status_tempo(row['data_expiracao']) if 'data_expiracao' in row else ("-", "grey")
                    with st.expander(f"{row['nome_cliente']} - {st_txt}"):
                        c1, c2 = st.columns([3, 1])
                        c1.write(f"Plano: {row.get('plano_nome')} | Vence: {row.get('data_expiracao', pd.NaT)}")
                        c1.write(f"Valor: R$ {row['valor_plano']} | Com: R$ {row['valor_comissao']}")
                        if c2.button("Renovar (+30)", key=f"r_{row['id']}"):
                            dt_base = row['data_expiracao'] if pd.notnull(row['data_expiracao']) else datetime.now()
                            # Ensure dt_base is naive before adding timedelta if needed, usually ok here
                            if isinstance(dt_base, pd.Timestamp) and dt_base.tz is not None:
                                dt_base = dt_base.tz_localize(None)
                            
                            n_exp = dt_base + timedelta(days=30)
                            supabase.table("vendas").update({"data_expiracao": n_exp.strftime('%Y-%m-%d'), "status": "Ativo"}).eq("id", row['id']).execute()
                            st.rerun()
            else: st.info("Sem vendas.")

    elif menu == "Planos":
        st.title("Configurar Planos")
        c1, c2 = st.columns([1, 2])
        with c1:
            with st.form("new_plan"):
                nome = st.text_input("Nome")
                val = st.number_input("Valor", value=30.0)
                dias = st.number_input("Dias", value=30)
                com = st.number_input("Comissão", value=10.0)
                if st.form_submit_button("Criar"):
                    supabase.table("planos").insert({"nome": nome, "valor": val, "dias": dias, "comissao_fixa": com}).execute()
                    st.rerun()
        with c2:
            if not df_planos.empty: st.dataframe(df_planos[['nome', 'valor', 'dias', 'comissao_fixa']], use_container_width=True)

    elif menu == "Parceiros":
        st.title("Parceiros")
        with st.expander("Novo Parceiro"):
            with st.form("add_parc"):
                nome = st.text_input("Nome")
                cupom = st.text_input("CUPOM").upper()
                whats = st.text_input("Zap")
                if st.form_submit_button("Cadastrar"):
                    try:
                        supabase.table("afiliados").insert({"nome": nome, "cupom": cupom, "whatsapp": whats}).execute()
                        st.success("Feito!"); st.rerun()
                    except: st.error("Erro/Duplicado")
        if not df_afiliados.empty: st.dataframe(df_afiliados, use_container_width=True)

    elif menu == "Marketing":
        st.title("Marketing")
        with st.form("mkt"):
            tit = st.text_input("Título")
            tipo = st.selectbox("Tipo", ["Texto", "Imagem"])
            cont = st.text_area("Conteúdo")
            if st.form_submit_button("Postar"):
                supabase.table("marketing").insert({"titulo": tit, "tipo": tipo, "conteudo": cont}).execute()
                st.success("Postado!")

    elif menu == "Financeiro":
        st.title("Financeiro")
        if not df_saques.empty:
            pends = df_saques[df_saques['status'] == 'Pendente']
            if not pends.empty:
                st.warning(f"{len(pends)} solicitações pendentes")
                for i, r in pends.iterrows():
                    with st.container():
                        c1, c2, c3 = st.columns([2, 1, 1])
                        c1.write(f"**{r['cupom']}**: R$ {r['valor']} ({r['created_at']})")
                        if c2.button("Pagar", key=f"p_{r['id']}"):
                            supabase.table("saques").update({"status": "Pago"}).eq("id", r['id']).execute(); st.rerun()
                        if c3.button("Recusar", key=f"d_{r['id']}"):
                            supabase.table("saques").update({"status": "Rejeitado"}).eq("id", r['id']).execute(); st.rerun()
            
            st.markdown("#### Histórico")
            st.dataframe(df_saques, use_container_width=True)

# ==============================================================================
# 🚀 PARCEIRO DASHBOARD
# ==============================================================================
def affiliate_dash():
    user = st.session_state['user']
    cupom = user['cupom']
    
    with st.sidebar:
        st.title(f"Olá, {user['nome'].split()[0]}")
        st.info(f"Cupom: {cupom}")
        menu = st.radio("Menu", ["Visão Geral", "Clientes", "Marketing", "Financeiro"])
        st.markdown("---")
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    df_vendas = get_data('vendas')
    minhas = df_vendas[df_vendas['cupom'] == cupom] if not df_vendas.empty else pd.DataFrame()
    
    if menu == "Visão Geral":
        st.title("Seu Desempenho")
        
        ativos = minhas[minhas['status'] == 'Ativo'] if not minhas.empty else pd.DataFrame()
        total_com = ativos['valor_comissao'].sum() if not ativos.empty else 0
        
        df_saq = get_data('saques')
        meus_saq = df_saq[(df_saq['cupom'] == cupom) & (df_saq['status'] != 'Rejeitado')] if not df_saq.empty else pd.DataFrame()
        sacado = meus_saq['valor'].sum() if not meus_saq.empty else 0
        disp = total_com - sacado
        
        c1, c2, c3 = st.columns(3)
        with c1: render_metric("Ativos", len(ativos))
        with c2: render_metric("Ganho Total", f"R$ {total_com:.2f}")
        with c3: render_metric("Disponível", f"R$ {disp:.2f}", color="#48BB78")
        
        st.markdown("### Gerador de Link")
        msg = f"Ola, quero renovar com cupom {cupom}"
        link = f"https://wa.me/5511999999999?text={msg.replace(' ', '%20')}"
        st.code(link)

    elif menu == "Clientes":
        st.title("Seus Clientes")
        if not minhas.empty:
            for i, r in minhas.iterrows():
                st_txt, st_cor = calcular_status_tempo(r['data_expiracao']) if 'data_expiracao' in r else ("-", "grey")
                with st.expander(f"{r['nome_cliente']} ({st_txt})"):
                    st.write(f"Plano: {r.get('plano_nome')} | Vence: {r.get('data_expiracao')}")
                    # Link de cobrança
                    l_cob = f"https://wa.me/?text=Ola%20{r['nome_cliente']}%20seu%20plano%20vence%20dia%20{r.get('data_expiracao')}"
                    st.link_button("Enviar Cobrança WhatsApp", l_cob)
        else: st.info("Nenhuma venda ainda.")

    elif menu == "Marketing":
        st.title("Materiais")
        df_mkt = get_data("marketing")
        if not df_mkt.empty:
            for i, r in df_mkt.iterrows():
                st.subheader(r['titulo'])
                if r['tipo'] == 'Imagem': st.image(r['conteudo'])
                else: st.code(r['conteudo'])
    
    elif menu == "Financeiro":
        st.title("Solicitar Saque")
        # Recalcular saldo
        ativos = minhas[minhas['status'] == 'Ativo'] if not minhas.empty else pd.DataFrame()
        total_com = ativos['valor_comissao'].sum() if not ativos.empty else 0
        df_saq = get_data('saques')
        meus_saq = df_saq[(df_saq['cupom'] == cupom) & (df_saq['status'] != 'Rejeitado')] if not df_saq.empty else pd.DataFrame()
        sacado = meus_saq['valor'].sum() if not meus_saq.empty else 0
        disp = total_com - sacado
        
        st.info(f"Disponível: R$ {disp:.2f}")
        
        with st.form("saque"):
            val = st.number_input("Valor", min_value=10.0, max_value=float(disp) if disp > 0 else 10.0)
            pix = st.text_input("Chave PIX")
            if st.form_submit_button("Pedir Saque") and disp >= val:
                supabase.table("saques").insert({"cupom": cupom, "valor": val, "status": "Pendente", "comprovante": pix}).execute()
                st.success("Enviado!"); st.rerun()
        
        st.dataframe(meus_saq[['created_at', 'valor', 'status']], use_container_width=True)

# ==============================================================================
# 🚦 APP
# ==============================================================================
if not st.session_state['logged_in']:
    login_ui()
else:
    if st.session_state['role'] == 'admin': admin_dash()
    elif st.session_state['role'] == 'afiliado': affiliate_dash()
